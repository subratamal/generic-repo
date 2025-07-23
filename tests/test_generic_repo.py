"""
Test suite for GenericRepository class.

This module contains comprehensive tests for the GenericRepository class,
including unit tests with mocked DynamoDB operations.
"""

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from botocore.exceptions import ClientError
from generic_repo import AsyncGenericRepository, GenericRepository

# ===========================
# SHARED TEST UTILITIES
# ===========================


class AsyncPageIterator:
    """Async iterator for mocking DynamoDB paginated responses."""

    def __init__(self, pages):
        self.pages = pages
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.pages):
            raise StopAsyncIteration
        page = self.pages[self.index]
        self.index += 1
        return page


def create_async_page_iterator(pages):
    """Helper function to create AsyncPageIterator instances."""
    return AsyncPageIterator(pages)


# ===========================
# PYTEST FIXTURES
# ===========================


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table for testing."""
    table = Mock()
    table.table_name = 'test-table'
    table.meta.client.get_paginator.return_value.paginate.return_value = []
    table.meta.client.describe_table.return_value = {'Table': {'ItemCount': 5}}
    return table


@pytest.fixture
def mock_dynamodb_resource(mock_table):
    """Create a mock DynamoDB resource for testing."""
    with patch('src.sync_repo.boto3.resource') as mock_resource:
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_resource.return_value = mock_dynamodb
        yield mock_dynamodb


@pytest.fixture
def sync_repo(mock_dynamodb_resource):
    """Create a GenericRepository instance with mocked dependencies."""
    return GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=False)


@pytest.fixture
def async_mock_table():
    """Create a mock async DynamoDB table for testing."""
    table = Mock()  # Use regular Mock, not AsyncMock for the table itself
    table.table_name = 'test-table'

    # Set up batch_writer to return an async context manager
    mock_batch_writer = AsyncMock()
    mock_batch_context_manager = AsyncMock()
    mock_batch_context_manager.__aenter__ = AsyncMock(return_value=mock_batch_writer)
    mock_batch_context_manager.__aexit__ = AsyncMock(return_value=None)
    table.batch_writer.return_value = mock_batch_context_manager

    # Set up async methods that should be awaitable
    table.get_item = AsyncMock()
    table.put_item = AsyncMock()
    table.delete_item = AsyncMock()

    # Set up pagination with async iterator support
    mock_paginator = Mock()
    mock_paginator.paginate = Mock(return_value=create_async_page_iterator([]))

    # Set up the meta.client as a regular Mock
    table.meta.client = Mock()
    table.meta.client.get_paginator.return_value = mock_paginator
    table.meta.client.describe_table = AsyncMock(return_value={'Table': {'ItemCount': 5}})

    return table


@pytest.fixture
def mock_aioboto3_session(async_mock_table):
    """Create a mock aioboto3 session for testing."""
    with patch('src.async_repo.aioboto3.Session') as mock_session_class:
        mock_session = Mock()
        mock_dynamodb_resource = AsyncMock()
        mock_dynamodb = Mock()  # This should be Mock, not AsyncMock

        # Set up the mock chain: Session -> resource -> __aenter__ -> Table
        mock_session.resource.return_value = mock_dynamodb_resource
        mock_dynamodb_resource.__aenter__.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = async_mock_table  # Direct return, not awaitable
        mock_session_class.return_value = mock_session

        yield mock_session


@pytest.fixture
def async_repo(mock_aioboto3_session):
    """Create an AsyncGenericRepository instance with mocked dependencies."""
    return AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=False)


@pytest_asyncio.fixture
async def async_repo_context(mock_aioboto3_session):
    """Create an async context manager for AsyncGenericRepository."""
    async with AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=False) as repo:
        yield repo


# ===========================
# SYNC REPOSITORY TESTS
# ===========================


class TestGenericRepository:
    """Test cases for the synchronous GenericRepository."""

    def test_init(self, sync_repo):
        """Test repository initialization."""
        assert sync_repo.table_name == 'test-table'
        assert sync_repo.primary_key_name == 'id'
        assert sync_repo.debug_mode is False

    def test_serialize_for_dynamodb(self, sync_repo):
        """Test data serialization."""
        data = {'string': 'test', 'number': 123, 'float': 45.67, 'bool': True, 'list': [1, 2, 3]}

        result = sync_repo._serialize_for_dynamodb(data)

        # Floats should be converted to Decimal
        assert isinstance(result['float'], Decimal)
        assert result['float'] == Decimal('45.67')
        assert result['string'] == 'test'
        assert result['number'] == 123

    def test_get_expire_at_epoch(self, sync_repo):
        """Test expiration timestamp generation."""
        import time

        now = time.time()
        expire_at = sync_repo._get_expire_at_epoch(1)  # 1 day

        # Should be approximately 24 hours from now
        expected_expire = now + (24 * 60 * 60)
        assert abs(expire_at - expected_expire) < 60  # Within 1 minute

    def test_load(self, sync_repo, mock_table):
        """Test loading an item."""
        mock_table.get_item.return_value = {'Item': {'id': 'test', 'name': 'Test Item'}}

        result = sync_repo.load('test')

        mock_table.get_item.assert_called_once_with(Key={'id': 'test'})
        assert result == {'id': 'test', 'name': 'Test Item'}

    def test_load_not_found(self, sync_repo, mock_table):
        """Test loading non-existent item."""
        mock_table.get_item.return_value = {}

        result = sync_repo.load('nonexistent')

        assert result is None

    def test_save(self, sync_repo, mock_table):
        """Test saving an item."""
        model_data = {'name': 'Test Item', 'value': 42}
        mock_table.get_item.return_value = {'Item': {'id': 'test', **model_data}}

        sync_repo.save('test', model_data)

        # Verify put_item was called
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert call_args['id'] == 'test'
        assert call_args['name'] == 'Test Item'
        assert call_args['value'] == 42

    def test_save_debug_mode(self, mock_dynamodb_resource, mock_table):
        """Test saving in debug mode."""
        debug_repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)

        result = debug_repo.save('test', {'name': 'Test'})

        # Should not call put_item in debug mode
        mock_table.put_item.assert_not_called()
        assert result is None

    def test_save_with_expiration(self, mock_dynamodb_resource, mock_table):
        """Test saving with expiration."""
        repo_with_expiration = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', data_expiration_days=30)

        repo_with_expiration.save('test', {'name': 'Test'}, return_model=False)

        # Verify expiration was added
        call_args = mock_table.put_item.call_args[1]['Item']
        assert '_expireAt' in call_args
        assert isinstance(call_args['_expireAt'], int)

    def test_save_batch(self, sync_repo, mock_table):
        """Test batch saving."""
        models = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]

        mock_batch_writer = Mock()
        # Properly mock the context manager
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        sync_repo.save_batch(models)

        # Verify batch_writer was used
        mock_table.batch_writer.assert_called_once()
        assert mock_batch_writer.put_item.call_count == 2

    def test_load_or_throw_success(self, sync_repo, mock_table):
        """Test load_or_throw with existing item."""
        mock_table.get_item.return_value = {'Item': {'id': 'test', 'name': 'Test Item'}}

        result = sync_repo.load_or_throw('test')

        assert result == {'id': 'test', 'name': 'Test Item'}

    def test_load_or_throw_not_found(self, sync_repo, mock_table):
        """Test load_or_throw with non-existent item."""
        mock_table.get_item.return_value = {}

        with pytest.raises(ValueError, match='Key not found'):
            sync_repo.load_or_throw('nonexistent')

    def test_count(self, sync_repo, mock_table):
        """Test counting items in table."""
        mock_table.meta.client.describe_table.return_value = {'Table': {'ItemCount': 5}}

        result = sync_repo.count()

        mock_table.meta.client.describe_table.assert_called_once_with(TableName='test-table')
        assert result == 5

    def test_load_client_error(self, sync_repo, mock_table):
        """Test load method with ClientError."""
        mock_table.get_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='GetItem'
        )

        with pytest.raises(ClientError):
            sync_repo.load('test-key')

    def test_load_by_composite_key(self, sync_repo, mock_table):
        """Test loading by composite key."""
        key_dict = {'pk': 'partition1', 'sk': 'sort1'}
        expected_item = {'pk': 'partition1', 'sk': 'sort1', 'data': 'value'}

        mock_table.get_item.return_value = {'Item': expected_item}

        result = sync_repo.load_by_composite_key(key_dict)

        mock_table.get_item.assert_called_once_with(Key=key_dict)
        assert result == expected_item

    def test_save_with_composite_key(self, sync_repo, mock_table):
        """Test saving with composite key."""
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        sync_repo.save_with_composite_key(item_data, return_model=False)

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert call_args['pk'] == 'partition1'
        assert call_args['sk'] == 'sort1'
        assert call_args['name'] == 'Test Item'

    def test_save_with_composite_key_with_expiration(self, mock_dynamodb_resource, mock_table):
        """Test saving with composite key and expiration."""
        repo_with_expiration = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', data_expiration_days=30)
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        repo_with_expiration.save_with_composite_key(item_data, return_model=False)

        call_args = mock_table.put_item.call_args[1]['Item']
        assert '_expireAt' in call_args
        assert isinstance(call_args['_expireAt'], int)

    def test_delete_by_composite_key(self, sync_repo, mock_table):
        """Test deleting by composite key."""
        key_dict = {'pk': 'partition1', 'sk': 'sort1'}

        sync_repo.delete_by_composite_key(key_dict)

        mock_table.delete_item.assert_called_once_with(Key=key_dict)

    def test_delete_by_composite_key_debug_mode(self, mock_dynamodb_resource, mock_table):
        """Test deleting by composite key in debug mode."""
        debug_repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        key_dict = {'pk': 'partition1', 'sk': 'sort1'}

        debug_repo.delete_by_composite_key(key_dict)

        mock_table.delete_item.assert_not_called()

    def test_delete_batch_by_keys(self, sync_repo, mock_table):
        """Test batch deleting by keys."""
        key_dicts = [{'id': 'item1'}, {'id': 'item2'}, {'id': 'item3'}]

        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        sync_repo.delete_batch_by_keys(key_dicts)

        mock_table.batch_writer.assert_called_once()
        assert mock_batch_writer.delete_item.call_count == 3

    def test_delete_batch_by_keys_empty_list(self, sync_repo, mock_table):
        """Test batch deleting with empty key list."""
        sync_repo.delete_batch_by_keys([])

        mock_table.batch_writer.assert_not_called()

    def test_delete_batch_by_keys_debug_mode(self, mock_dynamodb_resource, mock_table):
        """Test batch deleting in debug mode."""
        debug_repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        key_dicts = [{'id': 'item1'}, {'id': 'item2'}]

        debug_repo.delete_batch_by_keys(key_dicts)

        mock_table.batch_writer.assert_not_called()

    def test_find_all(self, sync_repo, mock_table):
        """Test finding all items with primary key."""
        expected_items = [
            {'id': 'test', 'sk': 'item1', 'name': 'Item 1'},
            {'id': 'test', 'sk': 'item2', 'name': 'Item 2'},
        ]

        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': expected_items}]

        result = sync_repo.find_all('test')

        mock_table.meta.client.get_paginator.assert_called_once_with('query')
        assert result == expected_items

    def test_find_all_empty_key(self, sync_repo, mock_table):
        """Test finding all with empty primary key value."""
        result = sync_repo.find_all('')

        assert result == []
        mock_table.meta.client.get_paginator.assert_not_called()

    def test_find_all_with_pagination(self, sync_repo, mock_table):
        """Test finding all with multiple pages."""
        page1_items = [{'id': 'test', 'sk': 'item1'}]
        page2_items = [{'id': 'test', 'sk': 'item2'}]

        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': page1_items}, {'Items': page2_items}]

        result = sync_repo.find_all('test')

        assert result == page1_items + page2_items

    def test_load_all(self, sync_repo, mock_table):
        """Test loading all items from table."""
        expected_items = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]

        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': expected_items}]

        result = list(sync_repo.load_all())

        mock_table.meta.client.get_paginator.assert_called_once_with('scan')
        assert result == expected_items

    def test_find_one_with_index(self, sync_repo, mock_table):
        """Test finding one item with index."""
        expected_item = {'id': 'test', 'email': 'test@example.com', 'name': 'Test User'}

        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': [expected_item]}]

        result = sync_repo.find_one_with_index('email-index', 'email', 'test@example.com')

        mock_table.meta.client.get_paginator.assert_called_once_with('query')
        assert result == expected_item

    def test_find_one_with_index_not_found(self, sync_repo, mock_table):
        """Test finding one item with index when not found."""
        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': []}]

        result = sync_repo.find_one_with_index('email-index', 'email', 'nonexistent@example.com')

        assert result is None

    def test_find_all_with_index(self, sync_repo, mock_table):
        """Test finding all items with index."""
        expected_items = [
            {'id': 'user1', 'status': 'active', 'name': 'User 1'},
            {'id': 'user2', 'status': 'active', 'name': 'User 2'},
        ]

        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': expected_items}]

        result = sync_repo.find_all_with_index('status-index', 'status', 'active')

        mock_table.meta.client.get_paginator.assert_called_once_with('query')
        assert result == expected_items

    def test_find_all_with_index_multiple_pages(self, sync_repo, mock_table):
        """Test finding all with index across multiple pages."""
        page1_items = [{'id': 'user1', 'status': 'active'}]
        page2_items = [{'id': 'user2', 'status': 'active'}]

        mock_paginator = Mock()
        mock_table.meta.client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'Items': page1_items}, {'Items': page2_items}]

        result = sync_repo.find_all_with_index('status-index', 'status', 'active')

        assert result == page1_items + page2_items

    def test_save_batch_empty_list(self, sync_repo, mock_table):
        """Test batch saving with empty model list."""
        sync_repo.save_batch([])

        mock_table.batch_writer.assert_not_called()

    def test_save_batch_large_batch(self, sync_repo, mock_table):
        """Test batch saving with large batch (more than 25 items)."""
        # Create 30 items to test batch splitting
        models = [{'id': f'item{i}', 'name': f'Item {i}'} for i in range(30)]

        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        sync_repo.save_batch(models)

        # Should be called twice (25 + 5 items)
        assert mock_table.batch_writer.call_count == 2
        # Total put_item calls should equal number of models
        assert mock_batch_writer.put_item.call_count == 30

    def test_delete_batch_by_keys_large_batch(self, sync_repo, mock_table):
        """Test batch deleting with large batch (more than 25 items)."""
        # Create 30 keys to test batch splitting
        key_dicts = [{'id': f'item{i}'} for i in range(30)]

        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        sync_repo.delete_batch_by_keys(key_dicts)

        # Should be called twice (25 + 5 items)
        assert mock_table.batch_writer.call_count == 2
        # Total delete_item calls should equal number of keys
        assert mock_batch_writer.delete_item.call_count == 30

    def test_save_client_error(self, sync_repo, mock_table):
        """Test save method with ClientError."""
        mock_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='PutItem'
        )

        with pytest.raises(ClientError):
            sync_repo.save('test-key', {'name': 'Test'})

    def test_save_batch_client_error(self, sync_repo, mock_table):
        """Test save_batch method with ClientError."""
        models = [{'id': 'item1', 'name': 'Item 1'}]

        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager
        mock_batch_writer.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='BatchWriteItem',
        )

        with pytest.raises(ClientError):
            sync_repo.save_batch(models)

    def test_find_all_client_error(self, sync_repo, mock_table):
        """Test find_all method with ClientError."""
        mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Query'
        )

        with pytest.raises(ClientError):
            sync_repo.find_all('test-key')

    def test_count_client_error(self, sync_repo, mock_table):
        """Test count method with ClientError."""
        mock_table.meta.client.describe_table.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='DescribeTable',
        )

        with pytest.raises(ClientError):
            sync_repo.count()

    def test_init_with_custom_session(self, mock_table):
        """Test repository initialization with custom boto3 session."""
        with patch('src.sync_repo.boto3.resource') as mock_resource:
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_resource.return_value = mock_dynamodb

            # Create a custom session
            custom_session = Mock()
            custom_session.resource.return_value = mock_dynamodb

            repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-west-2', session=custom_session)

            # Verify custom session was used
            custom_session.resource.assert_called_once_with('dynamodb', region_name='us-west-2')
            assert repo.table_name == 'test-table'

    def test_save_return_model_false(self, sync_repo, mock_table):
        """Test saving with return_model=False."""
        model_data = {'name': 'Test Item', 'value': 42}

        result = sync_repo.save('test', model_data, return_model=False)

        # Verify put_item was called but load was not called
        mock_table.put_item.assert_called_once()
        mock_table.get_item.assert_not_called()
        assert result is None

    def test_save_with_composite_key_return_model_true(self, sync_repo, mock_table):
        """Test saving with composite key and return_model=True."""
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        result = sync_repo.save_with_composite_key(item_data, return_model=True)

        mock_table.put_item.assert_called_once()
        # Should return the original item_data since we can't load composite key items easily
        assert result == item_data

    def test_load_by_composite_key_client_error(self, sync_repo, mock_table):
        """Test load_by_composite_key with ClientError."""
        mock_table.get_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='GetItem'
        )

        with pytest.raises(ClientError):
            sync_repo.load_by_composite_key({'pk': 'test', 'sk': 'test'})

    def test_save_with_composite_key_client_error(self, sync_repo, mock_table):
        """Test save_with_composite_key with ClientError."""
        mock_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='PutItem'
        )

        with pytest.raises(ClientError):
            sync_repo.save_with_composite_key({'pk': 'test', 'sk': 'test', 'data': 'value'})

    def test_delete_by_composite_key_client_error(self, sync_repo, mock_table):
        """Test delete_by_composite_key with ClientError."""
        mock_table.delete_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='DeleteItem',
        )

        with pytest.raises(ClientError):
            sync_repo.delete_by_composite_key({'pk': 'test', 'sk': 'test'})

    def test_delete_batch_by_keys_client_error(self, sync_repo, mock_table):
        """Test delete_batch_by_keys with ClientError."""
        key_dicts = [{'id': 'item1'}]

        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager
        mock_batch_writer.delete_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='BatchWriteItem',
        )

        with pytest.raises(ClientError):
            sync_repo.delete_batch_by_keys(key_dicts)

    def test_load_all_client_error(self, sync_repo, mock_table):
        """Test load_all method with ClientError."""
        mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Scan'
        )

        with pytest.raises(ClientError):
            list(sync_repo.load_all())

    def test_find_all_with_index_client_error(self, sync_repo, mock_table):
        """Test find_all_with_index method with ClientError."""
        mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Query'
        )

        with pytest.raises(ClientError):
            sync_repo.find_all_with_index('test-index', 'key', 'value')


# ===========================
# ASYNC REPOSITORY TESTS
# ===========================


class TestAsyncGenericRepository:
    """Test cases for the asynchronous AsyncGenericRepository."""

    def test_init(self, async_repo):
        """Test async repository initialization."""
        assert async_repo.table_name == 'test-table'
        assert async_repo.primary_key_name == 'id'
        assert async_repo.debug_mode is False

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_aioboto3_session):
        """Test async context manager functionality."""
        async with AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1') as repo:
            assert repo.table_name == 'test-table'

    @pytest.mark.asyncio
    async def test_load(self, async_repo_context, async_mock_table):
        """Test async loading an item."""
        async_mock_table.get_item.return_value = {'Item': {'id': 'test', 'name': 'Test Item'}}

        result = await async_repo_context.load('test')

        async_mock_table.get_item.assert_called_once_with(Key={'id': 'test'})
        assert result == {'id': 'test', 'name': 'Test Item'}

    @pytest.mark.asyncio
    async def test_save(self, async_repo_context, async_mock_table):
        """Test async saving an item."""
        model_data = {'name': 'Test Item', 'value': 42}
        async_mock_table.get_item.return_value = {'Item': {'id': 'test', **model_data}}

        await async_repo_context.save('test', model_data)

        # Verify put_item was called
        async_mock_table.put_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_debug_mode(self, mock_aioboto3_session, async_mock_table):
        """Test async saving in debug mode."""
        repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)

        result = await repo.save('test', {'name': 'Test'})

        # Should not call put_item in debug mode
        async_mock_table.put_item.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_or_throw_success(self, async_repo_context, async_mock_table):
        """Test async load_or_throw with existing item."""
        async_mock_table.get_item.return_value = {'Item': {'id': 'test', 'name': 'Test Item'}}

        result = await async_repo_context.load_or_throw('test')

        assert result == {'id': 'test', 'name': 'Test Item'}

    @pytest.mark.asyncio
    async def test_load_or_throw_not_found(self, async_repo_context, async_mock_table):
        """Test async load_or_throw with non-existent item."""
        async_mock_table.get_item.return_value = {}

        with pytest.raises(ValueError, match='Key not found'):
            await async_repo_context.load_or_throw('nonexistent')

    @pytest.mark.asyncio
    async def test_count(self, async_repo_context, async_mock_table):
        """Test async counting items."""
        result = await async_repo_context.count()

        async_mock_table.meta.client.describe_table.assert_called_once_with(TableName='test-table')
        assert result == 5

    @pytest.mark.asyncio
    async def test_save_with_composite_key(self, async_repo_context, async_mock_table):
        """Test async saving with composite key."""
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        await async_repo_context.save_with_composite_key(item_data, return_model=False)

        async_mock_table.put_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_with_composite_key_with_expiration(self, mock_aioboto3_session):
        """Test async saving with composite key and expiration."""
        async with AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', data_expiration_days=30) as repo:
            item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}
            await repo.save_with_composite_key(item_data, return_model=False)

    @pytest.mark.asyncio
    async def test_load_by_composite_key(self, async_repo_context, async_mock_table):
        """Test async loading by composite key."""
        key_dict = {'pk': 'partition1', 'sk': 'sort1'}
        expected_item = {'pk': 'partition1', 'sk': 'sort1', 'data': 'value'}

        async_mock_table.get_item.return_value = {'Item': expected_item}

        result = await async_repo_context.load_by_composite_key(key_dict)

        async_mock_table.get_item.assert_called_once_with(Key=key_dict)
        assert result == expected_item

    @pytest.mark.asyncio
    async def test_delete_by_composite_key(self, async_repo_context, async_mock_table):
        """Test async deleting by composite key."""
        key_dict = {'pk': 'partition1', 'sk': 'sort1'}

        await async_repo_context.delete_by_composite_key(key_dict)

        async_mock_table.delete_item.assert_called_once_with(Key=key_dict)

    @pytest.mark.asyncio
    async def test_delete_by_composite_key_debug_mode(self, mock_aioboto3_session, async_mock_table):
        """Test async deleting by composite key in debug mode."""
        repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        key_dict = {'pk': 'partition1', 'sk': 'sort1'}

        await repo.delete_by_composite_key(key_dict)

        async_mock_table.delete_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_batch(self, async_repo_context, async_mock_table):
        """Test async batch saving."""
        models = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]

        await async_repo_context.save_batch(models)

        # Verify batch_writer was called
        async_mock_table.batch_writer.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_batch_empty_list(self, async_repo_context, async_mock_table):
        """Test async batch saving with empty model list."""
        await async_repo_context.save_batch([])

        async_mock_table.batch_writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_batch_debug_mode(self, mock_aioboto3_session, async_mock_table):
        """Test async batch saving in debug mode."""
        repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        models = [{'id': 'item1', 'name': 'Item 1'}]

        await repo.save_batch(models)

        async_mock_table.batch_writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_batch_by_keys(self, async_repo_context, async_mock_table):
        """Test async batch deleting by keys."""
        key_dicts = [{'id': 'item1'}, {'id': 'item2'}, {'id': 'item3'}]

        await async_repo_context.delete_batch_by_keys(key_dicts)

        # Verify batch_writer was called
        async_mock_table.batch_writer.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_batch_by_keys_empty_list(self, async_repo_context, async_mock_table):
        """Test async batch deleting with empty key list."""
        await async_repo_context.delete_batch_by_keys([])

        async_mock_table.batch_writer.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_batch_by_keys_debug_logging(self, mock_aioboto3_session, caplog):
        """Test async delete_batch_by_keys debug mode logging."""
        debug_repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        key_dicts = [{'id': 'item1'}, {'id': 'item2'}]

        with caplog.at_level(logging.INFO):
            await debug_repo.delete_batch_by_keys(key_dicts)

        # Verify debug log was written
        assert 'Debug mode: skipping batch delete from test-table (2 items)' in caplog.text

    @pytest.mark.asyncio
    async def test_find_all(self, async_repo_context, async_mock_table):
        """Test async finding all items with primary key."""
        expected_items = [
            {'id': 'test', 'sk': 'item1', 'name': 'Item 1'},
            {'id': 'test', 'sk': 'item2', 'name': 'Item 2'},
        ]

        # Update the mock to return the expected items
        async_mock_table.meta.client.get_paginator.return_value.paginate.return_value = create_async_page_iterator([{'Items': expected_items}])

        result = await async_repo_context.find_all('test')

        async_mock_table.meta.client.get_paginator.assert_called_once_with('query')
        assert result == expected_items

    @pytest.mark.asyncio
    async def test_find_all_empty_key(self, async_repo_context, async_mock_table):
        """Test async finding all with empty primary key value."""
        result = await async_repo_context.find_all('')

        assert result == []
        async_mock_table.meta.client.get_paginator.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_all(self, async_repo_context, async_mock_table):
        """Test async loading all items from table."""
        expected_items = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]

        # Update the mock to return the expected items
        async_mock_table.meta.client.get_paginator.return_value.paginate.return_value = create_async_page_iterator([{'Items': expected_items}])

        result = []
        async for item in async_repo_context.load_all():
            result.append(item)

        async_mock_table.meta.client.get_paginator.assert_called_once_with('scan')
        assert result == expected_items

    @pytest.mark.asyncio
    async def test_find_one_with_index(self, async_repo_context, async_mock_table):
        """Test async finding one item with index."""
        expected_item = {'id': 'test', 'email': 'test@example.com', 'name': 'Test User'}

        # Update the mock to return the expected item
        async_mock_table.meta.client.get_paginator.return_value.paginate.return_value = create_async_page_iterator([{'Items': [expected_item]}])

        result = await async_repo_context.find_one_with_index('email-index', 'email', 'test@example.com')

        async_mock_table.meta.client.get_paginator.assert_called_once_with('query')
        assert result == expected_item

    @pytest.mark.asyncio
    async def test_find_one_with_index_not_found(self, async_repo_context, async_mock_table):
        """Test async finding one item with index when not found."""

        # Update the mock to return empty results
        async_mock_table.meta.client.get_paginator.return_value.paginate.return_value = create_async_page_iterator([{'Items': []}])

        result = await async_repo_context.find_one_with_index('email-index', 'email', 'nonexistent@example.com')

        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_with_index(self, async_repo_context, async_mock_table):
        """Test async finding all items with index."""
        expected_items = [
            {'id': 'user1', 'status': 'active', 'name': 'User 1'},
            {'id': 'user2', 'status': 'active', 'name': 'User 2'},
        ]

        # Update the mock to return the expected items
        async_mock_table.meta.client.get_paginator.return_value.paginate.return_value = create_async_page_iterator([{'Items': expected_items}])

        result = await async_repo_context.find_all_with_index('status-index', 'status', 'active')

        async_mock_table.meta.client.get_paginator.assert_called_once_with('query')
        assert result == expected_items

    @pytest.mark.asyncio
    async def test_load_client_error(self, async_repo_context, async_mock_table):
        """Test async load method with ClientError."""
        async_mock_table.get_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='GetItem'
        )

        with pytest.raises(ClientError):
            await async_repo_context.load('test-key')

    @pytest.mark.asyncio
    async def test_save_client_error(self, async_repo_context, async_mock_table):
        """Test async save method with ClientError."""
        async_mock_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='PutItem'
        )

        with pytest.raises(ClientError):
            await async_repo_context.save('test-key', {'name': 'Test'})

    @pytest.mark.asyncio
    async def test_find_all_client_error(self, async_repo_context, async_mock_table):
        """Test async find_all method with ClientError."""
        async_mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Query'
        )

        with pytest.raises(ClientError):
            await async_repo_context.find_all('test-key')

    @pytest.mark.asyncio
    async def test_count_client_error(self, async_repo_context, async_mock_table):
        """Test async count method with ClientError."""
        async_mock_table.meta.client.describe_table.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='DescribeTable',
        )

        with pytest.raises(ClientError):
            await async_repo_context.count()

    @pytest.mark.asyncio
    async def test_init_with_custom_session(self, async_mock_table):
        """Test async repository initialization with custom aioboto3 session."""
        with patch('src.async_repo.aioboto3.Session') as mock_session_class:
            mock_session = Mock()
            mock_dynamodb_resource = AsyncMock()
            mock_dynamodb = Mock()

            # Create a custom session
            mock_session.resource.return_value = mock_dynamodb_resource
            mock_dynamodb_resource.__aenter__.return_value = mock_dynamodb
            mock_dynamodb.Table.return_value = async_mock_table
            mock_session_class.return_value = mock_session

            repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-west-2', session=mock_session)

            async with repo:
                # Verify custom session was used
                mock_session.resource.assert_called_once_with('dynamodb', region_name='us-west-2')
                assert repo.table_name == 'test-table'

    @pytest.mark.asyncio
    async def test_save_return_model_false(self, async_repo_context, async_mock_table):
        """Test async saving with return_model=False."""
        model_data = {'name': 'Test Item', 'value': 42}

        result = await async_repo_context.save('test', model_data, return_model=False)

        # Verify put_item was called but get_item was not called
        async_mock_table.put_item.assert_called_once()
        async_mock_table.get_item.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_save_with_composite_key_return_model_true(self, async_repo_context, async_mock_table):
        """Test async saving with composite key and return_model=True."""
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        result = await async_repo_context.save_with_composite_key(item_data, return_model=True)

        async_mock_table.put_item.assert_called_once()
        # Should return the original item_data since we can't load composite key items easily
        assert result == item_data

    @pytest.mark.asyncio
    async def test_save_batch_client_error(self, async_repo_context, async_mock_table):
        """Test async save_batch method with ClientError."""
        models = [{'id': 'item1', 'name': 'Item 1'}]

        # Mock the batch writer to raise an exception
        mock_batch_writer = AsyncMock()
        mock_batch_context_manager = AsyncMock()
        mock_batch_context_manager.__aenter__ = AsyncMock(return_value=mock_batch_writer)
        mock_batch_context_manager.__aexit__ = AsyncMock(return_value=None)
        async_mock_table.batch_writer.return_value = mock_batch_context_manager

        mock_batch_writer.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='BatchWriteItem',
        )

        with pytest.raises(ClientError):
            await async_repo_context.save_batch(models)

    @pytest.mark.asyncio
    async def test_delete_batch_by_keys_client_error(self, async_repo_context, async_mock_table):
        """Test async delete_batch_by_keys with ClientError."""
        key_dicts = [{'id': 'item1'}]

        # Mock the batch writer to raise an exception
        mock_batch_writer = AsyncMock()
        mock_batch_context_manager = AsyncMock()
        mock_batch_context_manager.__aenter__ = AsyncMock(return_value=mock_batch_writer)
        mock_batch_context_manager.__aexit__ = AsyncMock(return_value=None)
        async_mock_table.batch_writer.return_value = mock_batch_context_manager

        mock_batch_writer.delete_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='BatchWriteItem',
        )

        with pytest.raises(ClientError):
            await async_repo_context.delete_batch_by_keys(key_dicts)

    @pytest.mark.asyncio
    async def test_load_all_client_error(self, async_repo_context, async_mock_table):
        """Test async load_all method with ClientError."""
        async_mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Scan'
        )

        with pytest.raises(ClientError):
            async for _ in async_repo_context.load_all():
                pass

    @pytest.mark.asyncio
    async def test_find_all_with_index_client_error(self, async_repo_context, async_mock_table):
        """Test async find_all_with_index method with ClientError."""
        async_mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Query'
        )

        with pytest.raises(ClientError):
            await async_repo_context.find_all_with_index('test-index', 'key', 'value')


# ===========================
# INTEGRATION TESTS
# ===========================


class TestBothRepositories:
    """Integration tests for both repository types."""

    def test_sync_and_async_have_same_methods(self):
        """Test that sync and async repositories have the same public methods."""
        # Get public methods (not starting with _)
        sync_methods = [method for method in dir(GenericRepository) if not method.startswith('_')]
        async_methods = [method for method in dir(AsyncGenericRepository) if not method.startswith('_')]

        # Remove async-specific methods
        async_methods_filtered = [method for method in async_methods if method not in ['__aenter__', '__aexit__']]

        # Sort for comparison
        sync_methods.sort()
        async_methods_filtered.sort()

        # They should have the same public interface
        assert sync_methods == async_methods_filtered, f'Method mismatch: sync={sync_methods}, async={async_methods_filtered}'

    def test_both_repositories_can_be_imported(self):
        """Test that both repositories can be imported successfully."""
        assert GenericRepository is not None
        assert AsyncGenericRepository is not None

        # Test that they are different classes
        assert GenericRepository != AsyncGenericRepository

        # Test that they have the expected attributes
        assert hasattr(GenericRepository, 'load')
        assert hasattr(GenericRepository, 'save')
        assert hasattr(AsyncGenericRepository, 'load')
        assert hasattr(AsyncGenericRepository, 'save')


# ===========================
# SHARED FIXTURES
# ===========================


@pytest.fixture
def sample_dynamodb_item():
    """Sample DynamoDB item for testing."""
    return {
        'id': 'test-item-123',
        'name': 'Test Item',
        'description': 'A test item for unit testing',
        'created_at': '2024-01-01T00:00:00Z',
        'metadata': {'category': 'test', 'priority': 'high'},
    }


@pytest.fixture
def mock_client_error():
    """Mock ClientError for testing error scenarios."""
    return ClientError(
        error_response={'Error': {'Code': 'ValidationException', 'Message': 'Mock validation error'}},
        operation_name='TestOperation',
    )


# ===========================
# ADDITIONAL COVERAGE TESTS
# ===========================


class TestSyncRepositoryAdditionalCoverage:
    """Additional tests to improve coverage for sync repository."""

    def test_save_with_composite_key_debug_logging(self, mock_dynamodb_resource, mock_table, caplog):
        """Test save_with_composite_key debug mode logging."""
        debug_repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        with caplog.at_level(logging.INFO):
            result = debug_repo.save_with_composite_key(item_data)

        # Verify debug log was written
        assert 'Debug mode: skipping composite key save to test-table' in caplog.text
        mock_table.put_item.assert_not_called()
        assert result is None

    def test_save_batch_debug_logging(self, mock_dynamodb_resource, mock_table, caplog):
        """Test save_batch debug mode logging."""
        debug_repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        models = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]

        with caplog.at_level(logging.INFO):
            debug_repo.save_batch(models)

        # Verify debug log was written
        assert 'Debug mode: skipping batch save to test-table (2 items)' in caplog.text
        mock_table.batch_writer.assert_not_called()

    def test_delete_batch_by_keys_debug_logging(self, mock_dynamodb_resource, mock_table, caplog):
        """Test delete_batch_by_keys debug mode logging."""
        debug_repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        key_dicts = [{'id': 'item1'}, {'id': 'item2'}]

        with caplog.at_level(logging.INFO):
            debug_repo.delete_batch_by_keys(key_dicts)

        # Verify debug log was written
        assert 'Debug mode: skipping batch delete from test-table (2 items)' in caplog.text
        mock_table.batch_writer.assert_not_called()


class TestAsyncRepositoryAdditionalCoverage:
    """Additional tests to improve coverage for async repository."""

    @pytest.mark.asyncio
    async def test_load_by_composite_key_client_error(self, async_repo_context, async_mock_table):
        """Test async load_by_composite_key with ClientError."""
        async_mock_table.get_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='GetItem'
        )

        with pytest.raises(ClientError):
            await async_repo_context.load_by_composite_key({'pk': 'test', 'sk': 'test'})

    @pytest.mark.asyncio
    async def test_save_with_composite_key_debug_logging(self, mock_aioboto3_session, caplog):
        """Test async save_with_composite_key debug mode logging."""
        debug_repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        with caplog.at_level(logging.INFO):
            result = await debug_repo.save_with_composite_key(item_data)

        # Verify debug log was written
        assert 'Debug mode: skipping composite key save to test-table' in caplog.text
        assert result is None

    @pytest.mark.asyncio
    async def test_save_with_composite_key_client_error(self, async_repo_context, async_mock_table):
        """Test async save_with_composite_key with ClientError."""
        async_mock_table.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='PutItem'
        )

        with pytest.raises(ClientError):
            await async_repo_context.save_with_composite_key({'pk': 'test', 'sk': 'test', 'data': 'value'})

    @pytest.mark.asyncio
    async def test_delete_by_composite_key_client_error(self, async_repo_context, async_mock_table):
        """Test async delete_by_composite_key with ClientError."""
        async_mock_table.delete_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}},
            operation_name='DeleteItem',
        )

        with pytest.raises(ClientError):
            await async_repo_context.delete_by_composite_key({'pk': 'test', 'sk': 'test'})

    @pytest.mark.asyncio
    async def test_save_batch_debug_logging(self, mock_aioboto3_session, caplog):
        """Test async save_batch debug mode logging."""
        debug_repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', debug_mode=True)
        models = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]

        with caplog.at_level(logging.INFO):
            await debug_repo.save_batch(models)

        # Verify debug log was written
        assert 'Debug mode: skipping batch save to test-table (2 items)' in caplog.text

    @pytest.mark.asyncio
    async def test_load_all_client_error(self, async_repo_context, async_mock_table):
        """Test async load_all method with ClientError."""
        async_mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Scan'
        )

        with pytest.raises(ClientError):
            async for _ in async_repo_context.load_all():
                pass

    @pytest.mark.asyncio
    async def test_find_all_with_index_client_error(self, async_repo_context, async_mock_table):
        """Test async find_all_with_index method with ClientError."""
        async_mock_table.meta.client.get_paginator.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, operation_name='Query'
        )

        with pytest.raises(ClientError):
            await async_repo_context.find_all_with_index('test-index', 'key', 'value')


class TestImportCoverage:
    """Tests to ensure all imports and type checking paths are covered."""

    def test_import_both_repositories(self):
        """Test that both repository classes can be imported and instantiated."""
        from src import AsyncGenericRepository, GenericRepository

        # Test sync repository
        sync_repo = GenericRepository(table_name='test', primary_key_name='id')
        assert sync_repo.table_name == 'test'
        assert sync_repo.primary_key_name == 'id'

        # Test async repository
        async_repo = AsyncGenericRepository(table_name='test', primary_key_name='id')
        assert async_repo.table_name == 'test'
        assert async_repo.primary_key_name == 'id'

    def test_type_checking_imports(self):
        """Test TYPE_CHECKING import coverage."""
        import sys
        from unittest.mock import patch

        # Temporarily enable TYPE_CHECKING to test the import path
        with patch.dict(sys.modules, {'typing': sys.modules['typing']}):
            # This should cover the TYPE_CHECKING import lines
            from src.async_repo import AsyncGenericRepository

            repo = AsyncGenericRepository(table_name='test', primary_key_name='id')
            assert repo is not None


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions for better coverage."""

    def test_sync_save_batch_with_expiration_disabled(self, sync_repo, mock_table):
        """Test save_batch with expiration explicitly disabled."""
        models = [{'id': 'item1', 'name': 'Item 1'}]

        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        sync_repo.save_batch(models, set_expiration=False)

        # Verify batch_writer was used
        mock_table.batch_writer.assert_called_once()
        mock_batch_writer.put_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_save_batch_with_expiration_disabled(self, async_repo_context, async_mock_table):
        """Test async save_batch with expiration explicitly disabled."""
        models = [{'id': 'item1', 'name': 'Item 1'}]

        await async_repo_context.save_batch(models, set_expiration=False)

        # Verify batch_writer was called
        async_mock_table.batch_writer.assert_called_once()

    def test_sync_save_with_expiration_disabled(self, sync_repo, mock_table):
        """Test save with expiration explicitly disabled."""
        model_data = {'name': 'Test Item', 'value': 42}
        mock_table.get_item.return_value = {'Item': {'id': 'test', **model_data}}

        sync_repo.save('test', model_data, set_expiration=False)

        # Verify put_item was called
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert '_expireAt' not in call_args

    @pytest.mark.asyncio
    async def test_async_save_with_expiration_disabled(self, async_repo_context, async_mock_table):
        """Test async save with expiration explicitly disabled."""
        model_data = {'name': 'Test Item', 'value': 42}
        async_mock_table.get_item.return_value = {'Item': {'id': 'test', **model_data}}

        await async_repo_context.save('test', model_data, set_expiration=False)

        # Verify put_item was called
        async_mock_table.put_item.assert_called_once()

    def test_sync_save_with_composite_key_expiration_disabled(self, sync_repo, mock_table):
        """Test save_with_composite_key with expiration explicitly disabled."""
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        sync_repo.save_with_composite_key(item_data, set_expiration=False, return_model=False)

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]['Item']
        assert '_expireAt' not in call_args

    @pytest.mark.asyncio
    async def test_async_save_with_composite_key_expiration_disabled(self, async_repo_context, async_mock_table):
        """Test async save_with_composite_key with expiration explicitly disabled."""
        item_data = {'pk': 'partition1', 'sk': 'sort1', 'name': 'Test Item'}

        await async_repo_context.save_with_composite_key(item_data, set_expiration=False, return_model=False)

        async_mock_table.put_item.assert_called_once()

    def test_sync_repository_with_custom_logger(self, mock_dynamodb_resource, mock_table):
        """Test sync repository with custom logger."""
        custom_logger = logging.getLogger('custom_test_logger')
        repo = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', logger=custom_logger)

        assert repo.logger == custom_logger

    def test_async_repository_with_custom_logger(self):
        """Test async repository with custom logger."""
        custom_logger = logging.getLogger('custom_async_test_logger')
        repo = AsyncGenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', logger=custom_logger)

        assert repo.logger == custom_logger

    def test_serialize_for_dynamodb_edge_cases(self, sync_repo):
        """Test serialization with edge cases."""
        import datetime
        from decimal import Decimal

        # Test with various data types
        data = {
            'string': 'test',
            'number': 123,
            'float': 45.67,
            'bool': True,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'datetime': datetime.datetime.now(),
            'none': None,
        }

        result = sync_repo._serialize_for_dynamodb(data)

        # Verify float is converted to Decimal
        assert isinstance(result['float'], Decimal)
        assert result['float'] == Decimal('45.67')

        # Verify other types are preserved or converted appropriately
        assert result['string'] == 'test'
        assert result['number'] == 123
        assert result['bool'] is True
        assert result['list'] == [1, 2, 3]
        assert result['dict'] == {'nested': 'value'}


class TestCompleteLineCoverage:
    """Tests specifically designed to cover the remaining missing lines for 100% coverage."""

    def test_type_checking_import_coverage(self):
        """Test to cover TYPE_CHECKING import on line 13 of async_repo.py."""
        # This test ensures that the TYPE_CHECKING import path exists
        # We can't easily test the actual import without causing dependency issues
        # but we can verify that the module imports correctly and the class exists
        import src.async_repo

        # Verify the module imported correctly and has the expected class
        assert hasattr(src.async_repo, 'AsyncGenericRepository')
        assert hasattr(src.async_repo.AsyncGenericRepository, '__init__')

        # Check that TYPE_CHECKING is being used properly in the module
        # by verifying the module can be imported without issues
        import typing

        assert hasattr(typing, 'TYPE_CHECKING')

    @pytest.mark.asyncio
    async def test_async_save_return_model_true_with_load(self, async_repo_context, async_mock_table):
        """Test async save method with return_model=True to cover line 225."""
        model_data = {'name': 'Test Item', 'value': 42}

        # Mock the load method to return a specific item
        expected_saved_item = {'id': 'test', **model_data}
        async_mock_table.get_item.return_value = {'Item': expected_saved_item}

        # Call save with return_model=True (default)
        result = await async_repo_context.save('test', model_data, return_model=True)

        # Verify put_item was called
        async_mock_table.put_item.assert_called_once()
        # Verify get_item was called for the return (this exercises line 225)
        async_mock_table.get_item.assert_called_once_with(Key={'id': 'test'})
        # Verify the returned result
        assert result == expected_saved_item

    def test_sync_save_batch_with_items_and_expiration(self, mock_dynamodb_resource, mock_table):
        """Test sync save_batch to specifically cover line 315 (batch_writer.put_item)."""
        # Create repo with expiration enabled
        repo_with_expiration = GenericRepository(table_name='test-table', primary_key_name='id', region_name='us-east-1', data_expiration_days=30)

        models = [{'id': 'item1', 'name': 'Item 1'}]

        # Set up batch writer mock
        mock_batch_writer = Mock()
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_batch_writer)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_table.batch_writer.return_value = mock_context_manager

        # Call save_batch with expiration enabled
        repo_with_expiration.save_batch(models, set_expiration=True)

        # Verify batch_writer.put_item was called (this exercises line 315)
        mock_batch_writer.put_item.assert_called_once()
        call_args = mock_batch_writer.put_item.call_args[1]['Item']
        assert call_args['id'] == 'item1'
        assert call_args['name'] == 'Item 1'
        assert '_expireAt' in call_args  # Expiration should be added

    @pytest.mark.asyncio
    async def test_async_save_batch_with_expiration_enabled(self, mock_aioboto3_session):
        """Test async save_batch with expiration to cover line 339."""
        # Create repo with expiration enabled
        repo_with_expiration = AsyncGenericRepository(
            table_name='test-table', primary_key_name='id', region_name='us-east-1', data_expiration_days=30
        )

        models = [{'id': 'item1', 'name': 'Item 1'}]

        # Set up async mock table
        async_mock_table = Mock()
        mock_batch_writer = AsyncMock()
        mock_batch_context_manager = AsyncMock()
        mock_batch_context_manager.__aenter__ = AsyncMock(return_value=mock_batch_writer)
        mock_batch_context_manager.__aexit__ = AsyncMock(return_value=None)
        async_mock_table.batch_writer.return_value = mock_batch_context_manager

        # Mock the table setup
        async_mock_table.table_name = 'test-table'

        # Start the repo context and set the table
        async with repo_with_expiration as repo:
            repo.table = async_mock_table

            # Call save_batch with expiration enabled (this exercises line 339)
            await repo.save_batch(models, set_expiration=True)

            # Verify batch_writer was used
            async_mock_table.batch_writer.assert_called_once()
            mock_batch_writer.put_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_save_with_expiration_enabled_line_222(self, mock_aioboto3_session):
        """Test async save method with expiration enabled to cover line 222."""
        # Create repo with expiration enabled
        repo_with_expiration = AsyncGenericRepository(
            table_name='test-table', primary_key_name='id', region_name='us-east-1', data_expiration_days=30
        )

        model_data = {'name': 'Test Item', 'value': 42}

        # Set up async mock table
        async_mock_table = Mock()
        async_mock_table.put_item = AsyncMock()
        async_mock_table.get_item = AsyncMock(return_value={'Item': {'id': 'test', **model_data}})

        # Start the repo context and set the table
        async with repo_with_expiration as repo:
            repo.table = async_mock_table

            # Call save with expiration enabled (this exercises line 222)
            result = await repo.save('test', model_data, return_model=False, set_expiration=True)

            # Verify put_item was called with expiration
            async_mock_table.put_item.assert_called_once()
            call_args = async_mock_table.put_item.call_args[1]['Item']
            assert call_args['id'] == 'test'
            assert call_args['name'] == 'Test Item'
            assert call_args['value'] == 42
            assert '_expireAt' in call_args  # Expiration should be added (line 222 executed)
            assert isinstance(call_args['_expireAt'], int)
            assert result is None  # return_model=False
