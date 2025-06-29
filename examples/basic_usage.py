#!/usr/bin/env python3
"""
Basic usage examples for GenericRepository and AsyncGenericRepository.

This example demonstrates how to use both sync and async versions of the
GenericRepository for common DynamoDB operations.

Requirements:
- AWS credentials configured (via AWS CLI, IAM role, or environment variables)
- A DynamoDB table created (or use the create_sample_table function)
"""

import asyncio
import logging

# Import both sync and async repositories
import boto3
from generic_repo import AsyncGenericRepository, GenericRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_table(table_name: str = 'sample-generic-repo-table'):
    """
    Create a sample DynamoDB table for testing.

    Args:
        table_name: Name of the table to create

    Returns:
        The created table resource
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    try:
        # Create table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH',  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S',  # String
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S',  # String
                },
                {
                    'AttributeName': 'status',
                    'AttributeType': 'S',  # String
                },
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH',  # Partition key for the GSI
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL',  # Include all attributes
                    },
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'status',
                            'KeyType': 'HASH',  # Partition key for the GSI
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL',  # Include all attributes
                    },
                },
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Wait for table to be created
        logger.info(f'Creating table {table_name}...')
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        logger.info(f'Table {table_name} created successfully!')

        return table

    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f'Table {table_name} already exists')
        return dynamodb.Table(table_name)


def create_composite_key_table(table_name: str = 'my-composite-table'):
    """
    Create a sample DynamoDB table with composite key (partition + sort key) for testing.

    Args:
        table_name: Name of the table to create

    Returns:
        The created table resource
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    try:
        # Create table with composite key
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'tenant_id',
                    'KeyType': 'HASH',  # Partition key
                },
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'RANGE',  # Sort key
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'tenant_id',
                    'AttributeType': 'S',  # String
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S',  # String
                },
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        # Wait for table to be created
        logger.info(f'Creating composite key table {table_name}...')
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        logger.info(f'Composite key table {table_name} created successfully!')

        return table

    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f'Composite key table {table_name} already exists')
        return dynamodb.Table(table_name)


def setup_tables():
    """Create all necessary tables for the examples."""
    print('=== Setting up tables ===')

    # Create main table for sync/async examples
    create_sample_table('my-table')

    # Create composite key table
    create_composite_key_table('my-composite-table')

    print('All tables are ready!')
    print()


def sync_example():
    """Example using the synchronous GenericRepository."""
    print('=== Synchronous Repository Example ===')

    # Initialize the repository - no need to create boto3 resources!
    repo = GenericRepository(
        table_name='my-table',
        primary_key_name='id',
        region_name='us-east-1',  # Optional: specify region
        logger=logger,
        data_expiration_days=30,
        debug_mode=False,  # Set to False for actual DynamoDB operations
    )

    # Basic operations
    try:
        # Save an item
        item_data = {'name': 'John Doe', 'email': 'john@example.com', 'age': 30, 'metadata': {'created_by': 'system'}}
        saved_item = repo.save('user-123', item_data)
        print(f'Saved item: {saved_item}')

        # Load an item
        loaded_item = repo.load('user-123')
        print(f'Loaded item: {loaded_item}')

        # Save multiple items in batch
        batch_items = [
            {'id': 'user-124', 'name': 'Jane Doe', 'email': 'jane@example.com'},
            {'id': 'user-125', 'name': 'Bob Smith', 'email': 'bob@example.com'},
        ]
        repo.save_batch(batch_items)
        print('Batch save completed')

        # Find all items with a specific partition key
        items = repo.find_all('user-123')
        print(f'Found {len(items)} items')

        # Count total items
        count = repo.count()
        print(f'Total items in table: {count}')

    except Exception as e:
        print(f'Error in sync operations: {e}')


async def async_example():
    """Example using the asynchronous AsyncGenericRepository."""
    print('\n=== Asynchronous Repository Example ===')

    # Initialize the async repository with context manager - no need to create aioboto3 resources!
    async with AsyncGenericRepository(
        table_name='my-table',
        primary_key_name='id',
        region_name='us-east-1',  # Optional: specify region
        logger=logger,
        data_expiration_days=30,
        debug_mode=False,  # Set to True for debugging
    ) as repo:
        try:
            # Save an item
            item_data = {
                'name': 'Alice Johnson',
                'email': 'alice@example.com',
                'age': 28,
                'metadata': {'created_by': 'async_system'},
            }
            saved_item = await repo.save('user-async-123', item_data)
            print(f'Async saved item: {saved_item}')

            # Load an item
            loaded_item = await repo.load('user-async-123')
            print(f'Async loaded item: {loaded_item}')

            # Save multiple items in batch
            batch_items = [
                {'id': 'user-async-124', 'name': 'Charlie Brown', 'email': 'charlie@example.com'},
                {'id': 'user-async-125', 'name': 'Diana Prince', 'email': 'diana@example.com'},
            ]
            await repo.save_batch(batch_items)
            print('Async batch save completed')

            # Find all items with a specific partition key
            items = await repo.find_all('user-async-123')
            print(f'Async found {len(items)} items')

            # Load all items using async generator
            print('Loading all items asynchronously:')
            count = 0
            async for item in repo.load_all():
                count += 1
                if count <= 3:  # Show first 3 items
                    print(f'  Item {count}: {item.get("name", "N/A")}')
                if count >= 10:  # Limit output
                    break
            print(f'Total items processed: {count}')

            # Count total items
            total_count = await repo.count()
            print(f'Total items in table: {total_count}')

        except Exception as e:
            print(f'Error in async operations: {e}')


def composite_key_example():
    """Example using composite key operations."""
    print('\n=== Composite Key Example ===')

    # Initialize repository with partition key name
    repo = GenericRepository(
        table_name='my-composite-table',
        primary_key_name='tenant_id',  # This is the partition key
        region_name='us-east-1',
        logger=logger,
        debug_mode=False,
    )

    try:
        # Save item with composite key (partition + sort key)
        item_data = {
            'tenant_id': 'tenant-123',
            'user_id': 'user-456',  # This is the sort key
            'name': 'Composite User',
            'email': 'composite@example.com',
        }
        saved_item = repo.save_with_composite_key(item_data)
        print(f'Saved composite key item: {saved_item}')

        # Load item by composite key
        key_dict = {'tenant_id': 'tenant-123', 'user_id': 'user-456'}
        loaded_item = repo.load_by_composite_key(key_dict)
        print(f'Loaded composite key item: {loaded_item}')

        # Find all items with the same partition key
        items = repo.find_all('tenant-123')
        print(f'Found {len(items)} items for tenant-123')

        # Delete by composite key
        repo.delete_by_composite_key(key_dict)
        print('Deleted composite key item')

    except Exception as e:
        print(f'Error in composite key operations: {e}')


def index_query_example():
    """Example using index-based queries."""
    print('\n=== Index Query Example ===')

    # Use the table with indexes for this example
    repo = GenericRepository(
        table_name='my-table',
        primary_key_name='id',
        region_name='us-east-1',
        logger=logger,
        debug_mode=False,
    )

    try:
        # First, add some sample data to query
        sample_users = [
            {'id': 'user-001', 'name': 'John Doe', 'email': 'john@example.com', 'status': 'active'},
            {'id': 'user-002', 'name': 'Jane Smith', 'email': 'jane@example.com', 'status': 'inactive'},
            {'id': 'user-003', 'name': 'Bob Johnson', 'email': 'bob@example.com', 'status': 'active'},
        ]

        print('Adding sample data for index queries...')
        repo.save_batch(sample_users)

        # Query using Global Secondary Index (GSI) - email-index
        items = repo.find_all_with_index(index_name='email-index', key_name='email', key_value='john@example.com')
        print(f'Found {len(items)} items with email john@example.com')
        if items:
            print(f'  User: {items[0].get("name", "N/A")}')

        # Find first item matching index query - status-index
        item = repo.find_one_with_index(index_name='status-index', key_name='status', key_value='active')
        print(f'First active item: {item.get("name", "N/A") if item else "None"}')

        # Find all active users
        active_items = repo.find_all_with_index(index_name='status-index', key_name='status', key_value='active')
        print(f'Found {len(active_items)} active users')

    except Exception as e:
        print(f'Error in index query operations: {e}')


if __name__ == '__main__':
    # Setup tables first
    setup_tables()

    # Run synchronous examples
    # sync_example()
    # composite_key_example()
    # index_query_example()

    # Run asynchronous example
    asyncio.run(async_example())

    print('\n=== All Examples Completed ===')
