import asyncio
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, List, Optional

import aioboto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .filter_helper import FilterHelper


class AsyncGenericRepository:
    """
    Async generic repository for DynamoDB table operations.

    This class provides a standardized interface for common DynamoDB operations including:
    - Basic CRUD operations (Create, Read, Update, Delete)
    - Batch operations for efficiency
    - Query operations with pagination support
    - Index-based queries
    - Automatic data serialization and expiration handling

    The repository supports both simple primary key tables and composite key tables
    (partition key + sort key).

    Authentication uses AWS default credentials from environment variables by default.
    Optionally accepts a pre-configured aioboto3 session for custom authentication.

    Note: Requires aioboto3 package for async functionality.

        Example:
        >>> async with AsyncGenericRepository(
        ...     table_name='my-table',
        ...     primary_key_name='id',
        ...     region_name='us-west-2',
        ...     data_expiration_days=30
        ... ) as repo:
        ...     item = await repo.save('key1', {'name': 'value'})
        ...     loaded = await repo.load('key1')
    """

    def __init__(
        self,
        table_name: str,
        primary_key_name: str,
        region_name: Optional[str] = None,
        session: Optional[aioboto3.Session] = None,
        logger: Optional[logging.Logger] = None,
        data_expiration_days: Optional[int] = None,
        debug_mode: bool = False,
    ):
        """
        Initialize the AsyncGenericRepository.

        Args:
            table_name: Name of the DynamoDB table
            primary_key_name: Name of the primary key attribute (partition key)
            region_name: AWS region name (optional, uses default if not provided)
            session: Pre-configured aioboto3 session (optional, creates new if not provided)
            logger: Optional logger instance. If None, creates a default logger
            data_expiration_days: Optional number of days after which items expire.
                                 If set, adds '_expireAt' field to saved items
            debug_mode: If True, skips actual database operations for testing
        """
        self.table_name = table_name
        self.primary_key_name = primary_key_name
        self.logger = logger or logging.getLogger(__name__)
        self.data_expiration_days = data_expiration_days
        self.debug_mode = debug_mode
        self.region_name = region_name

        # Store session and region for later use
        if session:
            self._session = session
        else:
            self._session = aioboto3.Session()

        self._dynamodb_resource = None
        self.table = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._dynamodb_resource = self._session.resource('dynamodb', region_name=self.region_name)
        self._dynamodb = await self._dynamodb_resource.__aenter__()

        # `aioboto3.resource("dynamodb").Table(name)` returns an awaitable in
        # real usage but unit‑test mocks often return a plain object.  Handle
        # either case safely.
        table_candidate = self._dynamodb.Table(self.table_name)
        if asyncio.iscoroutine(table_candidate):
            table_candidate = await table_candidate
        self.table = table_candidate
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._dynamodb_resource:
            await self._dynamodb_resource.__aexit__(exc_type, exc_val, exc_tb)

    # ===========================
    # PRIVATE UTILITY METHODS
    # ===========================

    def _get_expire_at_epoch(self, days: int) -> int:
        """
        Calculate expiration timestamp in epoch seconds.

        Args:
            days: Number of days from now when the item should expire

        Returns:
            Unix timestamp (epoch seconds) when item should expire
        """
        expiration_date = datetime.now() + timedelta(days=days)
        return int(expiration_date.timestamp())

    def _serialize_for_dynamodb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Python types to DynamoDB-compatible types.

        This method handles conversion of Python data types that aren't natively
        supported by DynamoDB (like datetime objects) into compatible formats.

        Args:
            data: Dictionary containing data to be serialized

        Returns:
            Dictionary with DynamoDB-compatible data types
        """
        return json.loads(json.dumps(data, default=str), parse_float=Decimal)

    # ===========================
    # BASIC READ OPERATIONS
    # ===========================

    async def load(self, primary_key_value: Any) -> Optional[Dict[str, Any]]:
        """
        Load an item by primary key.

        Args:
            primary_key_value: The value of the primary key to load

        Returns:
            Dictionary containing the item data, or None if not found

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        try:
            response = await self.table.get_item(Key={self.primary_key_name: primary_key_value})
            return response.get('Item')
        except ClientError as e:
            self.logger.error(f'Error loading item: {e}')
            raise

    async def load_by_composite_key(self, key_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Load an item by composite key (for tables with partition + sort key).

        Args:
            key_dict: Dictionary containing both partition and sort key values
                     Example: {'partition_key': 'value1', 'sort_key': 'value2'}

        Returns:
            Dictionary containing the item data, or None if not found

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        try:
            response = await self.table.get_item(Key=key_dict)
            return response.get('Item')
        except ClientError as e:
            self.logger.error(f'Error loading item by composite key: {e}')
            raise

    async def load_or_throw(self, primary_key_value: Any) -> Dict[str, Any]:
        """
        Load an item by primary key, throw if not found.

        Args:
            primary_key_value: The value of the primary key to load

        Returns:
            Dictionary containing the item data

        Raises:
            ValueError: If the item is not found
            ClientError: If there's an error communicating with DynamoDB
        """
        item = await self.load(primary_key_value)
        if not item:
            raise ValueError(f'Key not found in table {self.table_name}: {self.primary_key_name}={primary_key_value}')
        return item

    # ===========================
    # BASIC WRITE/DELETE OPERATIONS
    # ===========================

    async def save(
        self, primary_key_value: Any, model: Dict[str, Any], return_model: bool = True, set_expiration: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Save an item to the table.

        Args:
            primary_key_value: Value for the primary key
            model: Dictionary containing the data to save
            return_model: If True, returns the saved item after successful save
            set_expiration: If True and data_expiration_days is set, adds expiration

        Returns:
            Dictionary containing the saved item if return_model=True, otherwise None
            In debug mode, always returns None

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        if self.debug_mode:
            self.logger.info(f'Debug mode: skipping save to {self.table_name} for {primary_key_value}')
            return None

        # Combine model data with primary key
        item = {**model, self.primary_key_name: primary_key_value}

        # Add expiration if configured
        if set_expiration and self.data_expiration_days:
            item['_expireAt'] = self._get_expire_at_epoch(self.data_expiration_days)

        # Serialize for DynamoDB compatibility
        item = self._serialize_for_dynamodb(item)

        try:
            await self.table.put_item(Item=item)
            if return_model:
                return await self.load(primary_key_value)
        except ClientError as e:
            self.logger.error(f'Error saving item: {e}')
            raise

    async def save_with_composite_key(
        self, item_data: Dict[str, Any], return_model: bool = True, set_expiration: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Save an item to a table with composite key (partition + sort key).

        Args:
            item_data: Dictionary containing all the data including partition and sort keys
            return_model: If True, returns the saved item after successful save
            set_expiration: If True and data_expiration_days is set, adds expiration

        Returns:
            Dictionary containing the saved item if return_model=True, otherwise None
            In debug mode, always returns None

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        if self.debug_mode:
            self.logger.info(f'Debug mode: skipping composite key save to {self.table_name}')
            return None

        # Make a copy to avoid modifying the original
        item = item_data.copy()

        # Add expiration if configured
        if set_expiration and self.data_expiration_days:
            item['_expireAt'] = self._get_expire_at_epoch(self.data_expiration_days)

        # Serialize for DynamoDB compatibility
        item = self._serialize_for_dynamodb(item)

        try:
            await self.table.put_item(Item=item)
            if return_model:
                # For composite key tables, we need to extract the key components from the item
                # Assume we can determine the keys from the table schema or item data
                # For now, return the item data since we can't easily do a load operation
                return item_data
        except ClientError as e:
            self.logger.error(f'Error saving item with composite key: {e}')
            raise

    async def delete_by_composite_key(self, key_dict: Dict[str, Any]) -> None:
        """
        Delete an item by composite key.

        Args:
            key_dict: Dictionary containing both partition and sort key values
                     Example: {'partition_key': 'value1', 'sort_key': 'value2'}

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        if self.debug_mode:
            self.logger.info(f'Debug mode: skipping delete from {self.table_name}')
            return

        try:
            await self.table.delete_item(Key=key_dict)
        except ClientError as e:
            self.logger.error(f'Error deleting item: {e}')
            raise

    # ===========================
    # BATCH OPERATIONS
    # ===========================

    async def save_batch(self, models: List[Dict[str, Any]], set_expiration: bool = True) -> None:
        """
        Save multiple items in batch for improved performance.

        Automatically handles DynamoDB's 25-item batch limit by splitting large
        batches into smaller chunks.

        Args:
            models: List of dictionaries containing item data to save.
                   Each dict should contain all necessary data including primary key
            set_expiration: If True and data_expiration_days is set, adds expiration

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        if self.debug_mode:
            self.logger.info(f'Debug mode: skipping batch save to {self.table_name} ({len(models)} items)')
            return

        if not models:
            return

        # DynamoDB batch write limit is 25 items
        batch_size = 25

        for i in range(0, len(models), batch_size):
            batch = models[i : i + batch_size]
            items = []

            for model in batch:
                item = model.copy()
                # Add expiration if configured
                if set_expiration and self.data_expiration_days:
                    item['_expireAt'] = self._get_expire_at_epoch(self.data_expiration_days)
                items.append(self._serialize_for_dynamodb(item))

            try:
                async with self.table.batch_writer() as batch_writer:
                    for item in items:
                        await batch_writer.put_item(Item=item)
            except ClientError as e:
                self.logger.error(f'Error in batch save: {e}')
                raise

    async def delete_batch_by_keys(self, key_dicts: List[Dict[str, Any]]) -> None:
        """
        Delete multiple items by their keys in batch for improved performance.

        Automatically handles DynamoDB's 25-item batch limit by splitting large
        batches into smaller chunks.

        Args:
            key_dicts: List of dictionaries containing key values for items to delete.
                      Each dict should contain primary key (and sort key if applicable)
                      Example: [{'id': 'key1'}, {'id': 'key2'}] for simple primary key
                      Example: [{'pk': 'p1', 'sk': 's1'}] for composite key

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        if self.debug_mode:
            self.logger.info(f'Debug mode: skipping batch delete from {self.table_name} ({len(key_dicts)} items)')
            return

        if not key_dicts:
            return

        # DynamoDB batch write limit is 25 items
        batch_size = 25

        for i in range(0, len(key_dicts), batch_size):
            batch = key_dicts[i : i + batch_size]

            try:
                async with self.table.batch_writer() as batch_writer:
                    for key_dict in batch:
                        await batch_writer.delete_item(Key=key_dict)
            except ClientError as e:
                self.logger.error(f'Error in batch delete: {e}')
                raise

    # ===========================
    # QUERY OPERATIONS
    # ===========================

    async def find_all(self, primary_key_value: Any, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Find all items with the given primary key value, with optional filtering.

        Uses DynamoDB Query operation with automatic pagination to retrieve all
        items that match the primary key. For composite key tables, this returns
        all items with the given partition key across all sort keys. Additional
        filters can be applied to further narrow down the results.

        Args:
            primary_key_value: Value of the primary key (partition key) to search for
            filters: Optional dictionary containing filter conditions in JSON format.
                    Supports multiple formats:
                    - Simple equality: {"status": "active"}
                    - Operator format: {"age": {"gt": 18}}
                    - With type hints: {"price": {"value": 19.99, "type": "N", "operator": "ge"}}

                    Supported operators: eq, ne, lt, le, gt, ge, between, in, contains,
                    begins_with, exists, not_exists

                    Examples:
                    - {"status": "active", "age": {"gt": 18}}
                    - {"name": {"begins_with": "John"}}
                    - {"tags": {"contains": "python"}}
                    - {"score": {"between": [10, 20]}}
                    - {"category": {"in": ["tech", "science"]}}

        Returns:
            List of dictionaries containing all matching items. Empty list if none found

        Raises:
            ClientError: If there's an error communicating with DynamoDB
            ValueError: If filter format is invalid
        """
        if not primary_key_value:
            return []

        try:
            query_params = {
                'TableName': self.table_name,
                'KeyConditionExpression': Key(self.primary_key_name).eq(primary_key_value),
            }

            # Build filter expression if filters are provided
            if filters:
                filter_expression = FilterHelper.build_filter_expression(filters)
                if filter_expression:
                    query_params['FilterExpression'] = filter_expression

            paginator = self.table.meta.client.get_paginator('query')
            page_iterator = paginator.paginate(**query_params)

            items = []
            async for page in page_iterator:
                items.extend(page.get('Items', []))

            return items
        except ClientError as e:
            self.logger.error(f'Error in find_all: {e}')
            raise

    async def load_all(self, filters: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Scan and yield all items in the table with optional filtering.

        Uses DynamoDB Scan operation with automatic pagination. This is an expensive
        operation that reads the entire table, so use sparingly and prefer query
        operations when possible.

        Args:
            filters: Optional dictionary containing filter conditions in JSON format.
                    Supports multiple formats:
                    - Simple equality: {"status": "active"}
                    - Operator format: {"age": {"gt": 18}}
                    - With type hints: {"price": {"value": 19.99, "type": "N", "operator": "ge"}}

                    Supported operators: eq, ne, lt, le, gt, ge, between, in, contains,
                    begins_with, exists, not_exists

                    Examples:
                    - {"status": "active", "age": {"gt": 18}}
                    - {"name": {"begins_with": "John"}}
                    - {"tags": {"contains": "python"}}
                    - {"score": {"between": [10, 20]}}
                    - {"category": {"in": ["tech", "science"]}}

        Yields:
            Dictionary containing each item in the table that matches the filters

        Raises:
            ClientError: If there's an error communicating with DynamoDB
            ValueError: If filter format is invalid
        """
        try:
            scan_params = {'TableName': self.table_name}

            # Build filter expression if filters are provided
            if filters:
                filter_expression = FilterHelper.build_filter_expression(filters)
                if filter_expression:
                    scan_params['FilterExpression'] = filter_expression

            paginator = self.table.meta.client.get_paginator('scan')
            page_iterator = paginator.paginate(**scan_params)

            async for page in page_iterator:
                for item in page.get('Items', []):
                    yield item
        except ClientError as e:
            self.logger.error(f'Error in load_all: {e}')
            raise

    # ===========================
    # INDEX-BASED QUERY OPERATIONS
    # ===========================

    async def find_one_with_index(
        self, index_name: str, key_name: str, key_value: Any, filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the first item matching the index query, with optional filtering.

        Args:
            index_name: Name of the GSI (Global Secondary Index) or LSI (Local Secondary Index)
            key_name: Name of the index key attribute to query on
            key_value: Value to search for in the index
            filters: Optional dictionary containing filter conditions in JSON format.
                    Supports the same filter formats as find_all_with_index.

        Returns:
            Dictionary containing the first matching item, or None if not found

        Raises:
            ClientError: If there's an error communicating with DynamoDB
            ValueError: If filter format is invalid
        """
        items = await self.find_all_with_index(index_name, key_name, key_value, filters)
        return items[0] if items else None

    async def find_all_with_index(
        self, index_name: str, key_name: str, key_value: Any, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all items matching the index query, with optional filtering.

        Uses DynamoDB Query operation on a specified index with automatic pagination
        to retrieve all matching items. Additional filters can be applied to further
        narrow down the results.

        Args:
            index_name: Name of the GSI (Global Secondary Index) or LSI (Local Secondary Index)
            key_name: Name of the index key attribute to query on
            key_value: Value to search for in the index
            filters: Optional dictionary containing filter conditions in JSON format.
                    Supports multiple formats:
                    - Simple equality: {"status": "active"}
                    - Operator format: {"age": {"gt": 18}}
                    - With type hints: {"price": {"value": 19.99, "type": "N", "operator": "ge"}}

                    Supported operators: eq, ne, lt, le, gt, ge, between, in, contains,
                    begins_with, exists, not_exists

                    Examples:
                    - {"status": "active", "age": {"gt": 18}}
                    - {"name": {"begins_with": "John"}}
                    - {"tags": {"contains": "python"}}
                    - {"score": {"between": [10, 20]}}
                    - {"category": {"in": ["tech", "science"]}}

        Returns:
            List of dictionaries containing all matching items. Empty list if none found

        Raises:
            ClientError: If there's an error communicating with DynamoDB
            ValueError: If filter format is invalid
        """
        try:
            query_params = {
                'TableName': self.table_name,
                'IndexName': index_name,
                'KeyConditionExpression': Key(key_name).eq(key_value),
            }

            # Build filter expression if filters are provided
            if filters:
                filter_expression = FilterHelper.build_filter_expression(filters)
                if filter_expression:
                    query_params['FilterExpression'] = filter_expression

            paginator = self.table.meta.client.get_paginator('query')
            page_iterator = paginator.paginate(**query_params)

            items = []
            async for page in page_iterator:
                items.extend(page.get('Items', []))

            return items
        except ClientError as e:
            self.logger.error(f'Error in find_all_with_index: {e}')
            raise

    # ===========================
    # UTILITY OPERATIONS
    # ===========================

    async def count(self) -> int:
        """
        Count total items in the table.

        Returns the approximate number of items in the table from table metadata.
        Note: This count is approximate and may not reflect recent changes due to
        DynamoDB's eventual consistency model.

        Returns:
            Approximate number of items in the table

        Raises:
            ClientError: If there's an error communicating with DynamoDB
        """
        try:
            response = await self.table.meta.client.describe_table(TableName=self.table_name)
            return response['Table']['ItemCount']
        except ClientError as e:
            self.logger.error(f'Error counting items: {e}')
            raise
