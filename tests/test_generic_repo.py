"""
Test suite for GenericRepository class.

This module contains comprehensive tests for the GenericRepository class,
including unit tests with mocked DynamoDB operations.
"""

import json
import logging
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from generic_repo import GenericRepository


class TestGenericRepository:
    """Test cases for GenericRepository class."""

    @pytest.fixture
    def mock_table(self):
        """Create a mock DynamoDB table for testing."""
        table = Mock()
        table.table_name = 'test-table'
        table.meta.client = Mock()
        return table

    @pytest.fixture
    def repository(self, mock_table):
        """Create a GenericRepository instance for testing."""
        return GenericRepository(table=mock_table, primary_key_name='id', data_expiration_days=30, debug_mode=False)

    @pytest.fixture
    def debug_repository(self, mock_table):
        """Create a GenericRepository instance in debug mode for testing."""
        return GenericRepository(table=mock_table, primary_key_name='id', debug_mode=True)

    def test_initialization(self, mock_table):
        """Test repository initialization with various parameters."""
        # Test basic initialization
        repo = GenericRepository(table=mock_table, primary_key_name='id')
        assert repo.table == mock_table
        assert repo.primary_key_name == 'id'
        assert repo.table_name == 'test-table'
        assert repo.data_expiration_days is None
        assert repo.debug_mode is False
        assert isinstance(repo.logger, logging.Logger)

        # Test initialization with optional parameters
        custom_logger = logging.getLogger('test')
        repo = GenericRepository(table=mock_table, primary_key_name='pk', logger=custom_logger, data_expiration_days=7, debug_mode=True)
        assert repo.primary_key_name == 'pk'
        assert repo.logger == custom_logger
        assert repo.data_expiration_days == 7
        assert repo.debug_mode is True

    def test_get_expire_at_epoch(self, repository):
        """Test expiration timestamp calculation."""
        # Test that the method returns a future timestamp
        expire_at = repository._get_expire_at_epoch(7)
        assert isinstance(expire_at, int)
        assert expire_at > 0

    def test_serialize_for_dynamodb(self, repository):
        """Test data serialization for DynamoDB compatibility."""
        test_data = {'string': 'test', 'integer': 42, 'float': 3.14, 'boolean': True, 'none': None, 'list': [1, 2, 3], 'dict': {'nested': 'value'}}

        result = repository._serialize_for_dynamodb(test_data)

        # Check that floats are converted to Decimal
        assert isinstance(result['float'], Decimal)
        assert result['float'] == Decimal('3.14')

        # Check that other types are preserved
        assert result['string'] == 'test'
        assert result['integer'] == 42
        assert result['boolean'] is True
        assert result['none'] is None
        assert result['list'] == [1, 2, 3]
        assert result['dict'] == {'nested': 'value'}

    def test_load_success(self, repository, mock_table):
        """Test successful item loading."""
        expected_item = {'id': 'test-id', 'name': 'Test Item'}
        mock_table.get_item.return_value = {'Item': expected_item}

        result = repository.load('test-id')

        mock_table.get_item.assert_called_once_with(Key={'id': 'test-id'})
        assert result == expected_item

    def test_load_not_found(self, repository, mock_table):
        """Test loading when item is not found."""
        mock_table.get_item.return_value = {}

        result = repository.load('nonexistent-id')

        mock_table.get_item.assert_called_once_with(Key={'id': 'nonexistent-id'})
        assert result is None

    def test_load_client_error(self, repository, mock_table):
        """Test loading when DynamoDB raises an error."""
        mock_table.get_item.side_effect = ClientError({'Error': {'Code': 'ValidationException', 'Message': 'Test error'}}, 'GetItem')

        with pytest.raises(ClientError):
            repository.load('test-id')

    def test_load_or_throw_success(self, repository, mock_table):
        """Test load_or_throw when item exists."""
        expected_item = {'id': 'test-id', 'name': 'Test Item'}
        mock_table.get_item.return_value = {'Item': expected_item}

        result = repository.load_or_throw('test-id')

        assert result == expected_item

    def test_load_or_throw_not_found(self, repository, mock_table):
        """Test load_or_throw when item is not found."""
        mock_table.get_item.return_value = {}

        with pytest.raises(ValueError, match='Key not found in table'):
            repository.load_or_throw('nonexistent-id')

    def test_save_basic(self, repository, mock_table):
        """Test basic save operation."""
        test_data = {'name': 'Test Item', 'value': 42}
        expected_saved_item = {'id': 'test-id', 'name': 'Test Item', 'value': 42}

        # Mock the put_item and subsequent load
        mock_table.put_item.return_value = {}
        mock_table.get_item.return_value = {'Item': expected_saved_item}

        result = repository.save('test-id', test_data)

        # Verify put_item was called with correct data
        put_call_args = mock_table.put_item.call_args[1]['Item']
        assert put_call_args['id'] == 'test-id'
        assert put_call_args['name'] == 'Test Item'
        assert put_call_args['value'] == 42
        assert '_expireAt' in put_call_args  # Should have expiration

        # Verify return value
        assert result == expected_saved_item

    def test_save_without_return_model(self, repository, mock_table):
        """Test save operation without returning the model."""
        test_data = {'name': 'Test Item'}
        mock_table.put_item.return_value = {}

        result = repository.save('test-id', test_data, return_model=False)

        mock_table.put_item.assert_called_once()
        mock_table.get_item.assert_not_called()
        assert result is None

    def test_save_debug_mode(self, debug_repository, mock_table):
        """Test save operation in debug mode."""
        test_data = {'name': 'Test Item'}

        result = debug_repository.save('test-id', test_data)

        mock_table.put_item.assert_not_called()
        mock_table.get_item.assert_not_called()
        assert result is None

    def test_load_by_composite_key(self, repository, mock_table):
        """Test loading by composite key."""
        key_dict = {'partition_key': 'USER', 'sort_key': 'profile#123'}
        expected_item = {'partition_key': 'USER', 'sort_key': 'profile#123', 'name': 'Test'}

        mock_table.get_item.return_value = {'Item': expected_item}

        result = repository.load_by_composite_key(key_dict)

        mock_table.get_item.assert_called_once_with(Key=key_dict)
        assert result == expected_item

    def test_save_with_composite_key(self, repository, mock_table):
        """Test saving with composite key."""
        item_data = {'partition_key': 'USER', 'sort_key': 'profile#123', 'name': 'Test User'}

        mock_table.put_item.return_value = {}

        result = repository.save_with_composite_key(item_data)

        # Verify put_item was called
        mock_table.put_item.assert_called_once()
        put_call_args = mock_table.put_item.call_args[1]['Item']
        assert put_call_args['partition_key'] == 'USER'
        assert put_call_args['sort_key'] == 'profile#123'
        assert put_call_args['name'] == 'Test User'
        assert '_expireAt' in put_call_args

        # In composite key mode, should return original data
        assert result == item_data

    def test_save_batch(self, repository, mock_table):
        """Test batch save operation."""
        test_models = [
            {'id': 'item1', 'name': 'Item 1'},
            {'id': 'item2', 'name': 'Item 2'},
        ]

        # Mock batch writer context manager
        mock_batch_writer = Mock()
        mock_table.batch_writer.return_value.__enter__ = Mock(return_value=mock_batch_writer)
        mock_table.batch_writer.return_value.__exit__ = Mock(return_value=None)

        repository.save_batch(test_models)

        # Verify batch writer was used
        mock_table.batch_writer.assert_called_once()
        assert mock_batch_writer.put_item.call_count == 2

    def test_count(self, repository, mock_table):
        """Test count operation."""
        mock_table.meta.client.describe_table.return_value = {'Table': {'ItemCount': 42}}

        result = repository.count()

        mock_table.meta.client.describe_table.assert_called_once_with(TableName='test-table')
        assert result == 42


class TestGenericRepositoryIntegration:
    """Integration-style tests that test multiple methods together."""

    @pytest.fixture
    def mock_table(self):
        """Create a more comprehensive mock table for integration tests."""
        table = Mock()
        table.table_name = 'integration-test-table'
        table.meta.client = Mock()

        # Mock paginator for query operations
        mock_paginator = Mock()
        mock_page_iterator = [
            {'Items': [{'id': 'item1', 'name': 'Item 1'}]},
            {'Items': [{'id': 'item2', 'name': 'Item 2'}]},
        ]
        mock_paginator.paginate.return_value = mock_page_iterator
        table.meta.client.get_paginator.return_value = mock_paginator

        return table

    @pytest.fixture
    def repository(self, mock_table):
        """Create repository for integration tests."""
        return GenericRepository(table=mock_table, primary_key_name='id', data_expiration_days=30)

    def test_find_all(self, repository, mock_table):
        """Test find_all query operation."""
        result = repository.find_all('USER')

        # Verify paginator was used correctly
        mock_table.meta.client.get_paginator.assert_called_once_with('query')
        paginator = mock_table.meta.client.get_paginator.return_value
        paginator.paginate.assert_called_once()

        # Should return all items from all pages
        expected_items = [{'id': 'item1', 'name': 'Item 1'}, {'id': 'item2', 'name': 'Item 2'}]
        assert result == expected_items

    def test_find_all_with_empty_key(self, repository):
        """Test find_all with empty primary key value."""
        result = repository.find_all('')
        assert result == []

        result = repository.find_all(None)
        assert result == []


# Test fixtures and utilities
@pytest.fixture
def sample_dynamodb_item():
    """Sample DynamoDB item for testing."""
    return {
        'id': 'test-item-123',
        'name': 'Sample Item',
        'description': 'This is a test item',
        'tags': ['test', 'sample'],
        'metadata': {'created_by': 'test-user', 'version': 1},
        'active': True,
        'price': Decimal('19.99'),
    }


@pytest.fixture
def mock_client_error():
    """Create a mock ClientError for testing error scenarios."""
    return ClientError(
        error_response={'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Requested resource not found'}}, operation_name='GetItem'
    )
