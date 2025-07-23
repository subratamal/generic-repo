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

        # Update an existing item (partial update)
        update_data = {'status': 'active', 'last_login': '2024-01-01T10:30:00Z'}
        updated_item = repo.update('user-123', update_data)
        print(f'Updated item: {updated_item}')

        # Update with expiration
        repo.update('user-124', {'status': 'premium'}, set_expiration=True)
        print('Updated user-124 with expiration')

        # Find all items with a specific partition key
        items = repo.find_all('user-123')
        print(f'Found {len(items)} items')

        # Find all items with filtering
        filtered_items = repo.find_all('user-123', filters={'age': {'gt': 25}})
        print(f'Found {len(filtered_items)} items for user-123 with age > 25')

        # Count total items
        count = repo.count()
        print(f'Total items in table: {count}')

    except Exception as e:
        print(f'Error in sync operations: {e}')


def sync_filtering_example():
    """Example demonstrating filtering functionality in sync GenericRepository."""
    print('\n=== Sync Filtering Example ===')

    repo = GenericRepository(
        table_name='my-table',
        primary_key_name='id',
        region_name='us-east-1',
        logger=logger,
        debug_mode=False,
    )

    try:
        # First, add some sample data with different attributes for filtering
        sample_data = [
            {
                'id': 'sync-filter-001',
                'name': 'John Doe',
                'age': 25,
                'status': 'active',
                'city': 'New York',
                'score': 85.5,
            },
            {
                'id': 'sync-filter-002',
                'name': 'Jane Smith',
                'age': 30,
                'status': 'inactive',
                'city': 'Los Angeles',
                'score': 92.0,
            },
            {
                'id': 'sync-filter-003',
                'name': 'Bob Johnson',
                'age': 35,
                'status': 'active',
                'city': 'Chicago',
                'score': 78.3,
            },
            {
                'id': 'sync-filter-004',
                'name': 'Alice Brown',
                'age': 28,
                'status': 'active',
                'city': 'Houston',
                'score': 88.7,
            },
        ]

        print('Adding sample data for sync filtering...')
        repo.save_batch(sample_data)

        # Example 1: Simple equality filter
        print('\n1. Simple equality filter (status = "active"):')
        count = 0
        for item in repo.load_all(filters={'status': 'active'}):
            if 'sync-filter-' in item.get('id', ''):  # Only show our test data
                count += 1
                print(f'   {item["name"]} (age: {item["age"]}, score: {item["score"]})')
        print(f'   Found {count} active users')

        # Example 2: Multiple conditions
        print('\n2. Active users older than 25:')
        count = 0
        for item in repo.load_all(filters={'status': 'active', 'age': {'gt': 25}}):
            if 'sync-filter-' in item.get('id', ''):
                count += 1
                print(f'   {item["name"]} (age: {item["age"]})')
        print(f'   Found {count} active users older than 25')

        # Example 3: String operations
        print('\n3. Names containing "Jo":')
        count = 0
        for item in repo.load_all(filters={'name': {'contains': 'Jo'}}):
            if 'sync-filter-' in item.get('id', ''):
                count += 1
                print(f'   {item["name"]}')
        print(f'   Found {count} users with "Jo" in name')

    except Exception as e:
        print(f'Error in sync filtering operations: {e}')


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

            # Update an existing item (partial update)
            update_data = {'status': 'active', 'last_login': '2024-01-01T10:30:00Z'}
            updated_item = await repo.update('user-async-123', update_data)
            print(f'Async updated item: {updated_item}')

            # Update with expiration
            await repo.update('user-async-124', {'status': 'premium'}, set_expiration=True)
            print('Async updated user-async-124 with expiration')

            # Find all items with a specific partition key
            items = await repo.find_all('user-async-123')
            print(f'Async found {len(items)} items')

            # Find all items with filtering
            filtered_items = await repo.find_all('user-async-123', filters={'age': {'gt': 25}})
            print(f'Async found {len(filtered_items)} items for user-async-123 with age > 25')

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


async def filtering_example():
    """Example demonstrating the new filtering functionality in load_all."""
    print('\n=== Filtering Example ===')

    async with AsyncGenericRepository(
        table_name='my-table',
        primary_key_name='id',
        region_name='us-east-1',
        logger=logger,
        debug_mode=False,
    ) as repo:
        try:
            # First, add some sample data with different attributes for filtering
            sample_data = [
                {
                    'id': 'user-filter-001',
                    'name': 'John Doe',
                    'age': 25,
                    'status': 'active',
                    'city': 'New York',
                    'score': 85.5,
                },
                {
                    'id': 'user-filter-002',
                    'name': 'Jane Smith',
                    'age': 30,
                    'status': 'inactive',
                    'city': 'Los Angeles',
                    'score': 92.0,
                },
                {
                    'id': 'user-filter-003',
                    'name': 'Bob Johnson',
                    'age': 35,
                    'status': 'active',
                    'city': 'Chicago',
                    'score': 78.3,
                },
                {
                    'id': 'user-filter-004',
                    'name': 'Alice Brown',
                    'age': 28,
                    'status': 'active',
                    'city': 'Houston',
                    'score': 88.7,
                },
                {
                    'id': 'user-filter-005',
                    'name': 'Charlie Wilson',
                    'age': 45,
                    'status': 'inactive',
                    'city': 'Phoenix',
                    'score': 95.2,
                },
            ]

            print('Adding sample data for filtering...')
            await repo.save_batch(sample_data)

            # Example 1: Simple equality filter
            print('\n1. Simple equality filter (status = "active"):')
            count = 0
            async for item in repo.load_all(filters={'status': 'active'}):
                if 'user-filter-' in item.get('id', ''):  # Only show our test data
                    count += 1
                    print(f'   {item["name"]} (age: {item["age"]}, score: {item["score"]})')
            print(f'   Found {count} active users')

            # Example 2: Comparison operators
            print('\n2. Age greater than 30:')
            count = 0
            async for item in repo.load_all(filters={'age': {'gt': 30}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]} (age: {item["age"]})')
            print(f'   Found {count} users older than 30')

            # Example 3: Multiple conditions (AND logic)
            print('\n3. Active users older than 25:')
            count = 0
            async for item in repo.load_all(filters={'status': 'active', 'age': {'gt': 25}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]} (age: {item["age"]})')
            print(f'   Found {count} active users older than 25')

            # Example 4: Between operator
            print('\n4. Users with age between 28 and 35:')
            count = 0
            async for item in repo.load_all(filters={'age': {'between': [28, 35]}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]} (age: {item["age"]})')
            print(f'   Found {count} users between age 28-35')

            # Example 5: String contains
            print('\n5. Names containing "Jo":')
            count = 0
            async for item in repo.load_all(filters={'name': {'contains': 'Jo'}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]}')
            print(f'   Found {count} users with "Jo" in name')

            # Example 6: String begins with
            print('\n6. Names beginning with "A":')
            count = 0
            async for item in repo.load_all(filters={'name': {'begins_with': 'A'}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]}')
            print(f'   Found {count} users whose name starts with "A"')

            # Example 7: In operator
            print('\n7. Users from New York or Chicago:')
            count = 0
            async for item in repo.load_all(filters={'city': {'in': ['New York', 'Chicago']}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]} from {item["city"]}')
            print(f'   Found {count} users from specified cities')

            # Example 8: Explicit type specification for decimal numbers
            print('\n8. Users with score >= 90.0 (explicit number type):')
            count = 0
            async for item in repo.load_all(filters={'score': {'value': 90.0, 'type': 'N', 'operator': 'ge'}}):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]} (score: {item["score"]})')
            print(f'   Found {count} users with score >= 90.0')

            # Example 9: Complex filter combining multiple operators
            print('\n9. Complex filter - Active users with score > 80 and age <= 35:')
            count = 0
            filters = {'status': 'active', 'score': {'gt': 80}, 'age': {'le': 35}}
            async for item in repo.load_all(filters=filters):
                if 'user-filter-' in item.get('id', ''):
                    count += 1
                    print(f'   {item["name"]} (age: {item["age"]}, score: {item["score"]})')
            print(f'   Found {count} users matching complex criteria')

        except Exception as e:
            print(f'Error in filtering operations: {e}')


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

        # Update item by composite key (partial update)
        update_data = {'status': 'verified', 'last_updated': '2024-01-01T15:45:00Z'}
        updated_item = repo.update_by_composite_key(key_dict, update_data)
        print(f'Updated composite key item: {updated_item}')

        # Update with expiration
        repo.update_by_composite_key(key_dict, {'plan': 'enterprise'}, set_expiration=True)
        print('Updated composite key item with expiration')

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

        # Find active users with additional filtering
        filtered_active_items = repo.find_all_with_index(
            index_name='status-index', key_name='status', key_value='active', filters={'name': {'contains': 'Jo'}}
        )
        print(f'Found {len(filtered_active_items)} active users with "Jo" in name')

        # Find one with filtering
        filtered_item = repo.find_one_with_index(
            index_name='status-index', key_name='status', key_value='active', filters={'name': {'begins_with': 'B'}}
        )
        print(f'First active user with name starting with "B": {filtered_item.get("name", "None") if filtered_item else "None"}')

    except Exception as e:
        print(f'Error in index query operations: {e}')


async def async_composite_key_example():
    """Example using async composite key operations including updates."""
    print('\n=== Async Composite Key Example ===')

    # Initialize async repository with partition key name
    async with AsyncGenericRepository(
        table_name='my-composite-table',
        primary_key_name='tenant_id',  # This is the partition key
        region_name='us-east-1',
        logger=logger,
        debug_mode=False,
    ) as repo:
        try:
            # Save item with composite key (partition + sort key)
            item_data = {
                'tenant_id': 'async-tenant-123',
                'user_id': 'async-user-456',  # This is the sort key
                'name': 'Async Composite User',
                'email': 'async-composite@example.com',
                'status': 'pending',
            }
            saved_item = await repo.save_with_composite_key(item_data)
            print(f'Async saved composite key item: {saved_item}')

            # Load item by composite key
            key_dict = {'tenant_id': 'async-tenant-123', 'user_id': 'async-user-456'}
            loaded_item = await repo.load_by_composite_key(key_dict)
            print(f'Async loaded composite key item: {loaded_item}')

            # Update item by composite key (partial update)
            update_data = {'status': 'active', 'last_login': '2024-01-01T16:30:00Z', 'login_count': 1}
            updated_item = await repo.update_by_composite_key(key_dict, update_data)
            print(f'Async updated composite key item: {updated_item}')

            # Another update with different fields
            await repo.update_by_composite_key(key_dict, {'login_count': 5, 'plan': 'premium'}, set_expiration=True)
            print('Async updated composite key item with expiration')

            # Load the updated item to see all changes
            final_item = await repo.load_by_composite_key(key_dict)
            print(f'Final composite key item state: {final_item}')

            # Find all items with the same partition key
            items = await repo.find_all('async-tenant-123')
            print(f'Async found {len(items)} items for async-tenant-123')

            # Clean up - delete by composite key
            await repo.delete_by_composite_key(key_dict)
            print('Async deleted composite key item')

        except Exception as e:
            print(f'Error in async composite key operations: {e}')


def reserved_keywords_update_example():
    """Example demonstrating updates with DynamoDB reserved keywords."""
    print('\n=== Reserved Keywords Update Example ===')

    repo = GenericRepository(
        table_name='my-table',
        primary_key_name='id',
        region_name='us-east-1',
        logger=logger,
        debug_mode=False,
    )

    try:
        # Create a test item with various reserved keywords as field names
        test_data = {
            'name': 'Test User',
            'status': 'inactive',  # reserved keyword
            'size': 'large',  # reserved keyword
            'type': 'premium',  # reserved keyword
            'order': 1,  # reserved keyword
            'count': 0,  # reserved keyword
            'data': {'nested': 'value'},  # reserved keyword
        }

        # Save the item
        saved_item = repo.save('reserved-test-001', test_data)
        print(f'Saved item with reserved keywords: {saved_item}')

        # Update multiple reserved keyword fields at once
        update_data = {
            'status': 'active',  # reserved keyword
            'size': 'medium',  # reserved keyword
            'type': 'enterprise',  # reserved keyword
            'count': 5,  # reserved keyword
            'order': 10,  # reserved keyword
            'data': {'updated': 'successfully'},  # reserved keyword
        }

        updated_item = repo.update('reserved-test-001', update_data)
        print(f'Updated item with reserved keywords: {updated_item}')

        # Verify the update worked by loading the item
        loaded_item = repo.load('reserved-test-001')
        if loaded_item:
            print('Verification - loaded item shows updates:')
            for key in ['status', 'size', 'type', 'count', 'order']:
                print(f'  {key}: {loaded_item.get(key)}')
        else:
            print('Warning: Could not load item for verification')

    except Exception as e:
        print(f'Error in reserved keywords update operations: {e}')


if __name__ == '__main__':
    # Setup tables first
    setup_tables()

    # Run synchronous examples
    sync_example()
    sync_filtering_example()
    composite_key_example()
    index_query_example()

    # Run asynchronous example
    asyncio.run(async_example())
    asyncio.run(filtering_example())
    asyncio.run(async_composite_key_example())
    reserved_keywords_update_example()

    print('\n=== All Examples Completed ===')
