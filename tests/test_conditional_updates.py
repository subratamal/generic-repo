"""
Test conditional updates using moto for local DynamoDB mocking.

Run with: pytest tests/test_conditional_updates.py -v
"""

from decimal import Decimal

import boto3
import pytest
from moto import mock_dynamodb

from generic_repo import GenericRepository


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_dynamodb():
        # Create DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table
        table = dynamodb.create_table(
            TableName='test-table',
            KeySchema=[
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.meta.client.get_waiter('table_exists').wait(TableName='test-table')
        
        yield table


@pytest.fixture
def repo(dynamodb_table):
    """Create a GenericRepository instance."""
    session = boto3.Session()
    return GenericRepository(
        table_name='test-table',
        primary_key_name='id',
        region_name='us-east-1',
        session=session
    )


class TestSimpleConditions:
    """Test simple dictionary-based conditions."""
    
    def test_equality_condition_success(self, repo):
        """Test update with equality condition that passes."""
        # Setup: Create item with status='active'
        repo.save('item-1', {'status': 'active', 'value': 10})
        
        # Test: Update with condition status='active'
        result = repo.update(
            primary_key_value='item-1',
            update_data={'value': 20},
            conditions={'status': 'active'}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')
    
    def test_equality_condition_failure(self, repo):
        """Test update with equality condition that fails."""
        # Setup: Create item with status='inactive'
        repo.save('item-2', {'status': 'inactive', 'value': 10})
        
        # Test: Update with condition status='active' (will fail)
        result = repo.update(
            primary_key_value='item-2',
            update_data={'value': 20},
            conditions={'status': 'active'},
            rejection_message="Item must be active"
        )
        
        # Assert: Update was rejected
        assert isinstance(result, dict)
        assert result['success'] == False
        assert result['error_code'] == 'ConditionalCheckFailedException'
        assert 'Item must be active' in result['message']
        
        # Verify item was not updated
        item = repo.load('item-2')
        assert item['value'] == Decimal('10')
    
    def test_less_than_condition(self, repo):
        """Test update with less than condition."""
        # Setup
        repo.save('item-3', {'version': 5, 'content': 'old'})
        
        # Test: Update only if version < 10
        result = repo.update(
            primary_key_value='item-3',
            update_data={'content': 'new'},
            conditions={'version': {'lt': 10}}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['content'] == 'new'
    
    def test_less_than_condition_failure(self, repo):
        """Test update with less than condition that fails."""
        # Setup
        repo.save('item-4', {'version': 15, 'content': 'old'})
        
        # Test: Update only if version < 10 (will fail)
        result = repo.update(
            primary_key_value='item-4',
            update_data={'content': 'new'},
            conditions={'version': {'lt': 10}},
            rejection_message="Version limit exceeded"
        )
        
        # Assert: Update was rejected
        assert isinstance(result, dict)
        assert result['success'] == False
        assert 'Version limit exceeded' in result['message']
    
    def test_not_equal_condition(self, repo):
        """Test update with not equal condition."""
        # Setup
        repo.save('item-5', {'locked': False, 'value': 10})
        
        # Test: Update only if locked != True
        result = repo.update(
            primary_key_value='item-5',
            update_data={'value': 20},
            conditions={'locked': {'ne': True}}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')
    
    def test_greater_than_or_equal_condition(self, repo):
        """Test update with gte condition."""
        # Setup
        repo.save('item-6', {'age': 25, 'status': 'pending'})
        
        # Test: Update only if age >= 18
        result = repo.update(
            primary_key_value='item-6',
            update_data={'status': 'approved'},
            conditions={'age': {'gte': 18}}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['status'] == 'approved'
    
    def test_in_list_condition(self, repo):
        """Test update with 'in' operator."""
        # Setup
        repo.save('item-7', {'status': 'pending', 'value': 10})
        
        # Test: Update only if status in ['pending', 'processing']
        result = repo.update(
            primary_key_value='item-7',
            update_data={'value': 20},
            conditions={'status': {'in': ['pending', 'processing']}}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')
    
    def test_exists_condition(self, repo):
        """Test update with exists condition."""
        # Setup
        repo.save('item-8', {'email': 'test@example.com', 'value': 10})
        
        # Test: Update only if email exists
        result = repo.update(
            primary_key_value='item-8',
            update_data={'value': 20},
            conditions={'email': {'exists': True}}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')
    
    def test_not_exists_condition(self, repo):
        """Test update with not_exists condition."""
        # Setup
        repo.save('item-9', {'status': 'active', 'value': 10})
        
        # Test: Update only if deleted_at does not exist
        result = repo.update(
            primary_key_value='item-9',
            update_data={'value': 20},
            conditions={'deleted_at': {'not_exists': True}}
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')


class TestMultipleConditions:
    """Test multiple conditions (AND logic)."""
    
    def test_multiple_conditions_success(self, repo):
        """Test update with multiple conditions that all pass."""
        # Setup
        repo.save('item-10', {'status': 'draft', 'approved': False, 'value': 10})
        
        # Test: Update only if status='draft' AND approved=False
        result = repo.update(
            primary_key_value='item-10',
            update_data={'value': 20},
            conditions={
                'status': 'draft',
                'approved': False
            }
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')
    
    def test_multiple_conditions_partial_failure(self, repo):
        """Test update with multiple conditions where one fails."""
        # Setup
        repo.save('item-11', {'status': 'draft', 'approved': True, 'value': 10})
        
        # Test: Update only if status='draft' AND approved=False (will fail)
        result = repo.update(
            primary_key_value='item-11',
            update_data={'value': 20},
            conditions={
                'status': 'draft',
                'approved': False
            },
            rejection_message="Must be unapproved draft"
        )
        
        # Assert: Update was rejected
        assert isinstance(result, dict)
        assert result['success'] == False
        assert 'Must be unapproved draft' in result['message']


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    def test_optimistic_locking(self, repo):
        """Test optimistic locking pattern with version numbers."""
        # Setup: Create document with version 5
        repo.save('doc-1', {'content': 'old content', 'version': 5})
        
        # Test: Update with optimistic lock (check version)
        result = repo.update(
            primary_key_value='doc-1',
            update_data={'content': 'new content', 'version': 6},
            conditions={'version': 5},  # Only update if version is still 5
            rejection_message="Document was modified by another user"
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['version'] == Decimal('6')
        
        # Try to update again with old version (should fail)
        result2 = repo.update(
            primary_key_value='doc-1',
            update_data={'content': 'another update', 'version': 7},
            conditions={'version': 5},  # Still checking for version 5
            rejection_message="Document was modified by another user"
        )
        
        # Assert: Second update was rejected
        assert isinstance(result2, dict)
        assert result2['success'] == False
        assert 'Document was modified by another user' in result2['message']
    
    def test_workflow_state_validation(self, repo):
        """Test workflow state transitions."""
        # Setup: Create task in 'in_progress' state
        repo.save('task-1', {
            'status': 'in_progress',
            'assignee': 'john@example.com',
            'completed': False
        })
        
        # Test: Complete task (only if in_progress and has assignee)
        result = repo.update(
            primary_key_value='task-1',
            update_data={'status': 'completed', 'completed': True},
            conditions={
                'status': 'in_progress',
                'assignee': {'exists': True}
            },
            rejection_message="Can only complete in-progress tasks with assignee"
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['status'] == 'completed'
    
    def test_ecommerce_order_protection(self, repo):
        """Test preventing updates to shipped orders."""
        # Setup: Create shipped order
        repo.save('order-1', {
            'status': 'shipped',
            'quantity': 2,
            'total': 50.00
        })
        
        # Test: Try to update shipped order (should fail)
        result = repo.update(
            primary_key_value='order-1',
            update_data={'quantity': 3, 'total': 75.00},
            conditions={'status': {'in': ['pending', 'processing']}},
            rejection_message="Cannot modify orders that have shipped"
        )
        
        # Assert: Update was rejected
        assert isinstance(result, dict)
        assert result['success'] == False
        assert 'Cannot modify orders that have shipped' in result['message']
        
        # Verify order was not changed
        order = repo.load('order-1')
        assert order['quantity'] == Decimal('2')


class TestCompositeKeyUpdates:
    """Test conditional updates with composite keys."""
    
    @pytest.fixture
    def composite_table(self):
        """Create a table with composite key."""
        with mock_dynamodb():
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            
            table = dynamodb.create_table(
                TableName='composite-table',
                KeySchema=[
                    {'AttributeName': 'tenant_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'document_id', 'KeyType': 'RANGE'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'tenant_id', 'AttributeType': 'S'},
                    {'AttributeName': 'document_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            table.meta.client.get_waiter('table_exists').wait(TableName='composite-table')
            yield table
    
    @pytest.fixture
    def composite_repo(self, composite_table):
        """Create repository for composite key table."""
        session = boto3.Session()
        return GenericRepository(
            table_name='composite-table',
            primary_key_name='tenant_id',
            region_name='us-east-1',
            session=session
        )
    
    def test_composite_key_conditional_update(self, composite_repo):
        """Test conditional update with composite key."""
        # Setup
        composite_repo.save_with_composite_key({
            'tenant_id': 'tenant-1',
            'document_id': 'doc-1',
            'status': 'draft',
            'content': 'old content'
        })
        
        # Test: Update with condition
        result = composite_repo.update_by_composite_key(
            key_dict={'tenant_id': 'tenant-1', 'document_id': 'doc-1'},
            update_data={'content': 'new content'},
            conditions={'status': 'draft'},
            rejection_message="Can only update draft documents"
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['content'] == 'new content'


class TestBackwardsCompatibility:
    """Test that old Attr() syntax still works."""
    
    def test_attr_syntax_still_works(self, repo):
        """Test that boto3 Attr() syntax is still supported."""
        from boto3.dynamodb.conditions import Attr

        # Setup
        repo.save('item-20', {'status': 'active', 'value': 10})
        
        # Test: Update using old Attr() syntax
        result = repo.update(
            primary_key_value='item-20',
            update_data={'value': 20},
            conditions=Attr('status').eq('active')  # Old syntax
        )
        
        # Assert: Update succeeded
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_update_nonexistent_item_with_condition(self, repo):
        """Test updating item that doesn't exist with condition."""
        # Test: Try to update non-existent item with condition
        result = repo.update(
            primary_key_value='nonexistent',
            update_data={'value': 20},
            conditions={'status': 'active'},
            rejection_message="Item must be active"
        )
        
        # Assert: Update was rejected (item doesn't exist)
        assert isinstance(result, dict)
        assert result['success'] == False
    
    def test_update_with_none_condition(self, repo):
        """Test update with None condition (should work normally)."""
        # Setup
        repo.save('item-21', {'value': 10})
        
        # Test: Update with conditions=None
        result = repo.update(
            primary_key_value='item-21',
            update_data={'value': 20},
            conditions=None
        )
        
        # Assert: Update succeeded (no condition)
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')
    
    def test_update_with_empty_dict_condition(self, repo):
        """Test update with empty dict condition."""
        # Setup
        repo.save('item-22', {'value': 10})
        
        # Test: Update with conditions={}
        result = repo.update(
            primary_key_value='item-22',
            update_data={'value': 20},
            conditions={}
        )
        
        # Assert: Update succeeded (empty condition = no condition)
        assert result is not None
        assert result.get('success') != False
        assert result['value'] == Decimal('20')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

