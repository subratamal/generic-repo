#!/usr/bin/env python3
"""
Basic usage examples for Generic DynamoDB Repository.

This script demonstrates common usage patterns and operations
with the GenericRepository class.

Requirements:
- AWS credentials configured (via AWS CLI, IAM role, or environment variables)
- A DynamoDB table created (or use the create_sample_table function)
"""

import logging
from decimal import Decimal

import boto3

from generic_repo import GenericRepository

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
                }
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


def basic_crud_operations():
    """Demonstrate basic CRUD operations."""
    logger.info('=== Basic CRUD Operations ===')

    # Initialize DynamoDB table
    table = create_sample_table()

    # Create repository
    repo = GenericRepository(
        table=table,
        primary_key_name='id',
        data_expiration_days=30,  # Items expire after 30 days
        debug_mode=False,
    )

    # 1. CREATE - Save a new item
    user_data = {
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'age': 30,
        'preferences': {'notifications': True, 'theme': 'dark'},
        'tags': ['developer', 'python', 'aws'],
    }

    logger.info('Saving user...')
    saved_user = repo.save('user-123', user_data)
    logger.info(f'Saved user: {saved_user}')

    # 2. READ - Load the item
    logger.info('Loading user...')
    loaded_user = repo.load('user-123')
    logger.info(f'Loaded user: {loaded_user}')

    # 3. UPDATE - Save with modified data
    user_data['age'] = 31
    user_data['last_updated'] = '2024-12-19'

    logger.info('Updating user...')
    updated_user = repo.save('user-123', user_data)
    logger.info(f'Updated user: {updated_user}')

    # 4. DELETE - Remove the item
    logger.info('Deleting user...')
    repo.delete('user-123')

    # Verify deletion
    deleted_user = repo.load('user-123')
    logger.info(f'User after deletion: {deleted_user}')


def batch_operations():
    """Demonstrate batch operations for better performance."""
    logger.info('\n=== Batch Operations ===')

    table = create_sample_table()
    repo = GenericRepository(table=table, primary_key_name='id')

    # Batch save multiple items
    users = [
        {'id': 'user-001', 'name': 'Alice Johnson', 'email': 'alice@example.com', 'department': 'Engineering'},
        {'id': 'user-002', 'name': 'Bob Smith', 'email': 'bob@example.com', 'department': 'Marketing'},
        {'id': 'user-003', 'name': 'Carol Williams', 'email': 'carol@example.com', 'department': 'Sales'},
    ]

    logger.info('Batch saving users...')
    repo.save_batch(users)
    logger.info(f'Saved {len(users)} users in batch')

    # Load individual items to verify
    for user in users:
        loaded = repo.load(user['id'])
        logger.info(f'Verified user {user["id"]}: {loaded["name"]}')

    # Batch delete
    keys_to_delete = [{'id': user['id']} for user in users]
    logger.info('Batch deleting users...')
    repo.delete_batch_by_keys(keys_to_delete)
    logger.info(f'Deleted {len(keys_to_delete)} users in batch')


def composite_key_operations():
    """Demonstrate operations with composite keys (partition + sort key)."""
    logger.info('\n=== Composite Key Operations ===')

    # Create table with composite key
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table_name = 'sample-composite-table'

    try:
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
                {'AttributeName': 'tenant_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        logger.info(f'Composite key table created: {table_name}')

    except dynamodb.meta.client.exceptions.ResourceInUseException:
        table = dynamodb.Table(table_name)
        logger.info(f'Using existing composite key table: {table_name}')

    # Create repository for composite key table
    repo = GenericRepository(
        table=table,
        primary_key_name='tenant_id',  # Still need to specify partition key
    )

    # Save with composite key
    user_data = {
        'tenant_id': 'company-a',
        'user_id': 'emp-123',
        'name': 'David Brown',
        'role': 'Manager',
        'salary': Decimal('75000.00'),
    }

    logger.info('Saving with composite key...')
    repo.save_with_composite_key(user_data)

    # Load with composite key
    composite_key = {'tenant_id': 'company-a', 'user_id': 'emp-123'}

    logger.info('Loading with composite key...')
    loaded_user = repo.load_by_composite_key(composite_key)
    logger.info(f'Loaded composite key user: {loaded_user}')

    # Clean up
    repo.delete_by_composite_key(composite_key)


def query_operations():
    """Demonstrate query operations and pagination."""
    logger.info('\n=== Query Operations ===')

    table = create_sample_table()
    repo = GenericRepository(table=table, primary_key_name='id')

    # Add some test data
    test_data = [
        {'id': 'order-001', 'customer_id': 'customer-a', 'amount': Decimal('100.50')},
        {'id': 'order-002', 'customer_id': 'customer-a', 'amount': Decimal('250.00')},
        {'id': 'order-003', 'customer_id': 'customer-b', 'amount': Decimal('75.25')},
    ]

    logger.info('Adding test data...')
    repo.save_batch(test_data)

    # Count total items
    total_count = repo.count()
    logger.info(f'Total items in table: {total_count}')

    # Scan all items (use carefully on large tables!)
    logger.info('Scanning all items...')
    all_items = list(repo.load_all())
    logger.info(f'Found {len(all_items)} items via scan')

    # Clean up
    cleanup_keys = [{'id': item['id']} for item in test_data]
    repo.delete_batch_by_keys(cleanup_keys)


def error_handling():
    """Demonstrate error handling patterns."""
    logger.info('\n=== Error Handling ===')

    table = create_sample_table()
    repo = GenericRepository(table=table, primary_key_name='id')

    # Try to load non-existent item
    logger.info('Loading non-existent item...')
    result = repo.load('non-existent-key')
    logger.info(f'Non-existent item result: {result}')

    # Use load_or_throw for required items
    try:
        logger.info('Using load_or_throw on non-existent item...')
        repo.load_or_throw('non-existent-key')
    except ValueError as e:
        logger.info(f'Caught expected error: {e}')


def debug_mode_example():
    """Demonstrate debug mode for testing."""
    logger.info('\n=== Debug Mode Example ===')

    table = create_sample_table()

    # Create repository in debug mode
    debug_repo = GenericRepository(
        table=table,
        primary_key_name='id',
        debug_mode=True,  # This will skip actual database operations
    )

    # Operations in debug mode won't actually execute
    logger.info('Saving in debug mode (no actual database operation)...')
    result = debug_repo.save('debug-key', {'name': 'Debug User'})
    logger.info(f'Debug save result: {result}')

    logger.info('Loading in debug mode...')
    result = debug_repo.load('debug-key')
    logger.info(f'Debug load result: {result}')


def cleanup_tables():
    """Clean up sample tables."""
    logger.info('\n=== Cleanup ===')

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    tables_to_delete = ['sample-generic-repo-table', 'sample-composite-table']

    for table_name in tables_to_delete:
        try:
            table = dynamodb.Table(table_name)
            table.delete()
            logger.info(f'Deleted table: {table_name}')
        except Exception as e:
            logger.info(f'Could not delete table {table_name}: {e}')


if __name__ == '__main__':
    logger.info('Starting Generic DynamoDB Repository Examples')

    try:
        # Run all examples
        basic_crud_operations()
        batch_operations()
        composite_key_operations()
        query_operations()
        error_handling()
        debug_mode_example()

    except Exception as e:
        logger.error(f'Example failed: {e}')
        raise

    finally:
        # Uncomment to clean up tables after running examples
        # cleanup_tables()
        pass

    logger.info('Examples completed successfully!')
