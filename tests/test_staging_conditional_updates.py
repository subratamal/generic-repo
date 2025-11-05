"""
Test conditional updates against REAL DynamoDB staging environment.

⚠️  WARNING: This connects to REAL AWS resources!

Prerequisites:
1. AWS credentials configured (via ~/.aws/credentials or environment variables)
2. DynamoDB table created in staging
3. Appropriate IAM permissions

Setup:
    export AWS_PROFILE=your-staging-profile  # Optional
    export STAGING_TABLE_NAME=your-table-name
    export STAGING_REGION=us-east-1  # or your region

Run:
    python tests/test_staging_conditional_updates.py
"""

import logging
import os
import sys
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from generic_repo import GenericRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StagingTestConfig:
    """Configuration for staging tests."""
    
    def __init__(self):
        self.table_name = os.getenv('STAGING_TABLE_NAME', 'generic-repo-staging-test')
        self.region = os.getenv('STAGING_REGION', 'eu-west-2')
        self.aws_profile = os.getenv('AWS_PROFILE', 'default')
        
        logger.info(f"Configuration:")
        logger.info(f"  Table: {self.table_name}")
        logger.info(f"  Region: {self.region}")
        logger.info(f"  Profile: {self.aws_profile or 'default'}")


class StagingTestRunner:
    """Runner for staging environment tests."""
    
    def __init__(self, config: StagingTestConfig):
        self.config = config
        self.session = self._create_session()
        self.repo = self._create_repository()
        self.test_prefix = f"test-{int(time.time())}"
        self.cleanup_ids = []
    
    def _create_session(self) -> boto3.Session:
        """Create boto3 session with optional profile."""
        if self.config.aws_profile:
            return boto3.Session(profile_name=self.config.aws_profile)
        return boto3.Session()
    
    def _create_repository(self) -> GenericRepository:
        """Create GenericRepository instance."""
        return GenericRepository(
            table_name=self.config.table_name,
            primary_key_name='id',
            region_name=self.config.region,
            session=self.session
        )
    
    def _get_test_id(self, suffix: str) -> str:
        """Generate test item ID."""
        test_id = f"{self.test_prefix}-{suffix}"
        self.cleanup_ids.append(test_id)
        return test_id
    
    def cleanup(self):
        """Clean up test data."""
        logger.info(f"\n🧹 Cleaning up {len(self.cleanup_ids)} test items...")
        for item_id in self.cleanup_ids:
            try:
                self.repo.table.delete_item(Key={'id': item_id})
                logger.info(f"  ✓ Deleted {item_id}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to delete {item_id}: {e}")
    
    def verify_table_exists(self) -> bool:
        """Verify the DynamoDB table exists."""
        try:
            response = self.repo.table.meta.client.describe_table(
                TableName=self.config.table_name
            )
            logger.info(f"✓ Table '{self.config.table_name}' exists")
            logger.info(f"  Status: {response['Table']['TableStatus']}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.error(f"✗ Table '{self.config.table_name}' not found!")
                logger.error(f"  Create it with:")
                logger.error(f"  aws dynamodb create-table --table-name {self.config.table_name} \\")
                logger.error(f"    --attribute-definitions AttributeName=id,AttributeType=S \\")
                logger.error(f"    --key-schema AttributeName=id,KeyType=HASH \\")
                logger.error(f"    --billing-mode PAY_PER_REQUEST \\")
                logger.error(f"    --region {self.config.region}")
                return False
            raise
    
    def test_simple_equality_condition(self) -> bool:
        """Test 1: Simple equality condition."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: Simple Equality Condition")
        logger.info("="*70)
        
        try:
            item_id = self._get_test_id('equality')
            
            # Create item
            logger.info(f"Creating item {item_id} with status='active'...")
            self.repo.save(item_id, {'status': 'active', 'value': 10})
            
            # Update with matching condition (should succeed)
            logger.info("Updating with condition: status='active'...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 20},
                conditions={'status': 'active'}
            )
            
            if result.get('success') == False:
                logger.error(f"  ✗ Update failed: {result['message']}")
                return False
            
            logger.info(f"  ✓ Update succeeded! Value: {result['value']}")
            
            # Try update with non-matching condition (should fail)
            logger.info("Updating with condition: status='inactive' (should fail)...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 30},
                conditions={'status': 'inactive'},
                rejection_message="Status must be inactive"
            )
            
            if result.get('success') == False:
                logger.info(f"  ✓ Update correctly rejected: {result['message']}")
                return True
            else:
                logger.error("  ✗ Update should have been rejected!")
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            return False
    
    def test_comparison_operators(self) -> bool:
        """Test 2: Comparison operators (lt, gt, etc)."""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: Comparison Operators")
        logger.info("="*70)
        
        try:
            item_id = self._get_test_id('comparison')
            
            # Create item
            logger.info(f"Creating item {item_id} with version=5...")
            self.repo.save(item_id, {'version': 5, 'content': 'old'})
            
            # Update with lt condition (should succeed)
            logger.info("Updating with condition: version < 10...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'content': 'new'},
                conditions={'version': {'lt': 10}}
            )
            
            if result.get('success') == False:
                logger.error(f"  ✗ Update failed: {result['message']}")
                return False
            
            logger.info(f"  ✓ Update succeeded! Content: {result['content']}")
            
            # Update version to 15
            self.repo.update(item_id, {'version': 15})
            
            # Try update with lt condition (should fail)
            logger.info("Updating with condition: version < 10 (should fail)...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'content': 'newer'},
                conditions={'version': {'lt': 10}},
                rejection_message="Version must be < 10"
            )
            
            if result.get('success') == False:
                logger.info(f"  ✓ Update correctly rejected: {result['message']}")
                return True
            else:
                logger.error("  ✗ Update should have been rejected!")
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            return False
    
    def test_multiple_conditions(self) -> bool:
        """Test 3: Multiple conditions (AND logic)."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Multiple Conditions (AND)")
        logger.info("="*70)
        
        try:
            item_id = self._get_test_id('multiple')
            
            # Create item
            logger.info(f"Creating item {item_id}...")
            self.repo.save(item_id, {
                'status': 'draft',
                'approved': False,
                'value': 10
            })
            
            # Update with both conditions matching (should succeed)
            logger.info("Updating with conditions: status='draft' AND approved=False...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 20},
                conditions={
                    'status': 'draft',
                    'approved': False
                }
            )
            
            if result.get('success') == False:
                logger.error(f"  ✗ Update failed: {result['message']}")
                return False
            
            logger.info(f"  ✓ Update succeeded! Value: {result['value']}")
            
            # Update approved to True
            self.repo.update(item_id, {'approved': True})
            
            # Try update with one condition failing (should fail)
            logger.info("Updating with conditions: status='draft' AND approved=False (should fail)...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 30},
                conditions={
                    'status': 'draft',
                    'approved': False
                },
                rejection_message="Must be unapproved draft"
            )
            
            if result.get('success') == False:
                logger.info(f"  ✓ Update correctly rejected: {result['message']}")
                return True
            else:
                logger.error("  ✗ Update should have been rejected!")
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            return False
    
    def test_optimistic_locking(self) -> bool:
        """Test 4: Optimistic locking pattern."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: Optimistic Locking")
        logger.info("="*70)
        
        try:
            item_id = self._get_test_id('locking')
            
            # Create document with version
            logger.info(f"Creating document {item_id} with version=1...")
            self.repo.save(item_id, {'content': 'v1', 'version': 1})
            
            # Update with version check (should succeed)
            logger.info("Updating with version=1 check...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'content': 'v2', 'version': 2},
                conditions={'version': 1}
            )
            
            if result.get('success') == False:
                logger.error(f"  ✗ Update failed: {result['message']}")
                return False
            
            logger.info(f"  ✓ Updated to version {result['version']}")
            
            # Try to update with old version (should fail)
            logger.info("Trying to update with stale version=1 (should fail)...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'content': 'v3', 'version': 3},
                conditions={'version': 1},
                rejection_message="Document was modified by another user"
            )
            
            if result.get('success') == False:
                logger.info(f"  ✓ Stale update correctly rejected: {result['message']}")
                return True
            else:
                logger.error("  ✗ Stale update should have been rejected!")
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            return False
    
    def test_in_operator(self) -> bool:
        """Test 5: IN operator for list membership."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: IN Operator")
        logger.info("="*70)
        
        try:
            item_id = self._get_test_id('in-operator')
            
            # Create item
            logger.info(f"Creating item {item_id} with status='pending'...")
            self.repo.save(item_id, {'status': 'pending', 'value': 10})
            
            # Update with IN condition (should succeed)
            logger.info("Updating with condition: status IN ['pending', 'processing']...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 20},
                conditions={'status': {'in': ['pending', 'processing']}}
            )
            
            if result.get('success') == False:
                logger.error(f"  ✗ Update failed: {result['message']}")
                return False
            
            logger.info(f"  ✓ Update succeeded! Value: {result['value']}")
            
            # Update status to shipped
            self.repo.update(item_id, {'status': 'shipped'})
            
            # Try update with IN condition (should fail)
            logger.info("Updating with condition: status IN ['pending', 'processing'] (should fail)...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 30},
                conditions={'status': {'in': ['pending', 'processing']}},
                rejection_message="Can only update pending or processing items"
            )
            
            if result.get('success') == False:
                logger.info(f"  ✓ Update correctly rejected: {result['message']}")
                return True
            else:
                logger.error("  ✗ Update should have been rejected!")
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            return False
    
    def test_exists_operator(self) -> bool:
        """Test 6: EXISTS operator."""
        logger.info("\n" + "="*70)
        logger.info("TEST 6: EXISTS Operator")
        logger.info("="*70)
        
        try:
            item_id = self._get_test_id('exists')
            
            # Create item with email
            logger.info(f"Creating item {item_id} with email...")
            self.repo.save(item_id, {'email': 'test@example.com', 'value': 10})
            
            # Update with exists condition (should succeed)
            logger.info("Updating with condition: email EXISTS...")
            result = self.repo.update(
                primary_key_value=item_id,
                update_data={'value': 20},
                conditions={'email': {'exists': True}}
            )
            
            if result.get('success') == False:
                logger.error(f"  ✗ Update failed: {result['message']}")
                return False
            
            logger.info(f"  ✓ Update succeeded! Value: {result['value']}")
            return True
                
        except Exception as e:
            logger.error(f"  ✗ Test failed with exception: {e}")
            return False
    
    def run_all_tests(self) -> None:
        """Run all staging tests."""
        logger.info("\n" + "="*70)
        logger.info("STAGING ENVIRONMENT TESTS - Conditional Updates")
        logger.info("="*70)
        
        # Verify table exists
        if not self.verify_table_exists():
            logger.error("\n❌ Cannot proceed without table. Exiting.")
            sys.exit(1)
        
        # Run tests
        tests = [
            ("Simple Equality Condition", self.test_simple_equality_condition),
            ("Comparison Operators", self.test_comparison_operators),
            ("Multiple Conditions", self.test_multiple_conditions),
            ("Optimistic Locking", self.test_optimistic_locking),
            ("IN Operator", self.test_in_operator),
            ("EXISTS Operator", self.test_exists_operator),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                logger.error(f"\n❌ Test '{test_name}' crashed: {e}")
                results.append((test_name, False))
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"  {status} - {test_name}")
        
        logger.info("\n" + "="*70)
        logger.info(f"Results: {passed}/{total} tests passed")
        logger.info("="*70)
        
        # Cleanup
        self.cleanup()
        
        # Exit with appropriate code
        if passed == total:
            logger.info("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            logger.error(f"\n❌ {total - passed} test(s) failed")
            sys.exit(1)


def main():
    """Main entry point."""
    logger.info("Starting staging environment tests...")
    
    # Create config
    config = StagingTestConfig()
    
    # Confirm before proceeding
    print("\n⚠️  WARNING: This will connect to REAL AWS resources!")
    print(f"   Table: {config.table_name}")
    print(f"   Region: {config.region}")
    response = input("\nContinue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Aborted.")
        sys.exit(0)
    
    # Run tests
    runner = StagingTestRunner(config)
    try:
        runner.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Tests interrupted by user")
        runner.cleanup()
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Unexpected error: {e}")
        runner.cleanup()
        raise


if __name__ == '__main__':
    main()

