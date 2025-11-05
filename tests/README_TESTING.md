# Testing Conditional Updates

This guide explains how to test the conditional updates feature both locally (with moto) and against a real staging environment.

## Option 1: Local Testing with Moto (Recommended for Development)

Moto mocks AWS services locally, allowing you to test without connecting to real AWS.

### Setup

1. **Install dependencies:**
   ```bash
   pip install pytest moto[dynamodb]
   ```

2. **Run the tests:**
   ```bash
   # Run all conditional update tests
   uv run pytest tests/test_conditional_updates.py -v

   # Run specific test class
   uv run pytest tests/test_conditional_updates.py::TestSimpleConditions -v

   # Run specific test
   uv run pytest tests/test_conditional_updates.py::TestSimpleConditions::test_equality_condition_success -v

   # Show detailed output
   uv run pytest tests/test_conditional_updates.py -v -s
   ```

### What's Tested

The moto tests cover:
- ✅ Simple equality conditions
- ✅ Comparison operators (lt, gt, lte, gte)
- ✅ Not equal conditions
- ✅ IN operator (list membership)
- ✅ EXISTS and NOT_EXISTS operators
- ✅ Multiple conditions (AND logic)
- ✅ Optimistic locking pattern
- ✅ Workflow state validation
- ✅ E-commerce order protection
- ✅ Composite key updates with conditions
- ✅ Backwards compatibility with Attr() syntax
- ✅ Edge cases (non-existent items, None conditions, etc.)

### Example Output

```
tests/test_conditional_updates.py::TestSimpleConditions::test_equality_condition_success PASSED
tests/test_conditional_updates.py::TestSimpleConditions::test_equality_condition_failure PASSED
tests/test_conditional_updates.py::TestSimpleConditions::test_less_than_condition PASSED
...
========================== 25 passed in 2.34s ==========================
```

### Benefits of Moto Testing

- ⚡ **Fast**: No network calls, tests run in seconds
- 💰 **Free**: No AWS costs
- 🔒 **Safe**: No risk of affecting real data
- 🔄 **Repeatable**: Clean slate for each test
- 🚀 **CI/CD friendly**: Perfect for automated pipelines

---

## Option 2: Staging Environment Testing (Production-Like)

Test against a **real DynamoDB table** in your staging environment.

### Prerequisites

1. **AWS Credentials configured:**
   ```bash
   # Option A: Using AWS CLI profile
   export AWS_PROFILE=your-staging-profile

   # Option B: Using environment variables
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   ```

2. **Create DynamoDB table** (if it doesn't exist):
   ```bash
   aws dynamodb create-table \
     --table-name generic-repo-staging-test \
     --attribute-definitions AttributeName=id,AttributeType=S \
     --key-schema AttributeName=id,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region us-east-1
   ```

3. **IAM Permissions needed:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "dynamodb:PutItem",
           "dynamodb:GetItem",
           "dynamodb:UpdateItem",
           "dynamodb:DeleteItem",
           "dynamodb:DescribeTable"
         ],
         "Resource": "arn:aws:dynamodb:*:*:table/generic-repo-staging-test"
       }
     ]
   }
   ```

### Setup

1. **Configure environment:**
   ```bash
   # Required
   export STAGING_TABLE_NAME=generic-repo-staging-test
   export STAGING_REGION=us-east-1

   # Optional (if using profiles)
   export AWS_PROFILE=your-staging-profile
   ```

2. **Run the staging tests:**
   ```bash
   python tests/test_staging_conditional_updates.py
   ```

### What Happens

The script will:
1. ✅ Verify table exists
2. ✅ Ask for confirmation before proceeding
3. ✅ Run 6 comprehensive tests
4. ✅ Clean up test data automatically
5. ✅ Show detailed results

### Example Output

```
================================================================================
STAGING ENVIRONMENT TESTS - Conditional Updates
================================================================================
Configuration:
  Table: generic-repo-staging-test
  Region: us-east-1
  Profile: staging

⚠️  WARNING: This will connect to REAL AWS resources!
   Table: generic-repo-staging-test
   Region: us-east-1

Continue? (yes/no): yes

================================================================================
TEST 1: Simple Equality Condition
================================================================================
Creating item test-1234567890-equality with status='active'...
Updating with condition: status='active'...
  ✓ Update succeeded! Value: 20
Updating with condition: status='inactive' (should fail)...
  ✓ Update correctly rejected: Status must be inactive

================================================================================
TEST 2: Comparison Operators
================================================================================
...

================================================================================
TEST SUMMARY
================================================================================
  ✓ PASS - Simple Equality Condition
  ✓ PASS - Comparison Operators
  ✓ PASS - Multiple Conditions
  ✓ PASS - Optimistic Locking
  ✓ PASS - IN Operator
  ✓ PASS - EXISTS Operator

================================================================================
Results: 6/6 tests passed
================================================================================

🧹 Cleaning up 6 test items...
  ✓ Deleted test-1234567890-equality
  ✓ Deleted test-1234567890-comparison
  ...

🎉 All tests passed!
```

### What's Tested

The staging tests cover:
1. ✅ Simple equality conditions
2. ✅ Comparison operators (lt, gt)
3. ✅ Multiple conditions (AND logic)
4. ✅ Optimistic locking with version numbers
5. ✅ IN operator for list membership
6. ✅ EXISTS operator for attribute presence

### Safety Features

- ⚠️ **Requires confirmation** before running
- 🧹 **Auto-cleanup**: Deletes test items after completion
- 🏷️ **Unique prefixes**: Uses timestamps to avoid conflicts
- 📝 **Detailed logging**: Clear output of what's happening
- ✅ **Verification**: Checks table exists before starting

### Troubleshooting

**Error: Table not found**
```bash
# Create the table first
aws dynamodb create-table \
  --table-name generic-repo-staging-test \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**Error: Credentials not found**
```bash
# Configure AWS credentials
aws configure --profile staging

# Or export directly
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

**Error: Access Denied**
- Check IAM permissions (see Prerequisites above)
- Verify you have permissions for the specific table

---

## Comparison: Moto vs Staging

| Feature | Moto | Staging |
|---------|------|---------|
| **Speed** | ⚡ Very fast (seconds) | 🐢 Slower (network calls) |
| **Cost** | 💰 Free | 💵 AWS charges apply |
| **Safety** | 🔒 100% safe | ⚠️ Real resources |
| **Realism** | 🎭 Mocked behavior | ✅ Real DynamoDB |
| **CI/CD** | ✅ Perfect | ⚠️ Requires credentials |
| **Setup** | 🚀 pip install moto | 🔧 AWS config needed |
| **Use Case** | Development, CI | Pre-production validation |

## Recommended Testing Strategy

```
┌─────────────────┐
│  Development    │  →  Use Moto (fast feedback)
└─────────────────┘

┌─────────────────┐
│  Pull Request   │  →  Use Moto (CI pipeline)
└─────────────────┘

┌─────────────────┐
│  Pre-Release    │  →  Use Staging (real validation)
└─────────────────┘

┌─────────────────┐
│  Production     │  →  Monitor & alerts
└─────────────────┘
```

## Writing Your Own Tests

### For Moto

```python
import pytest
from moto import mock_dynamodb
from generic_repo import GenericRepository

@mock_dynamodb
def test_my_condition():
    # Setup mock DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(...)
    
    # Create repository
    repo = GenericRepository(...)
    
    # Test your condition
    result = repo.update(
        primary_key_value='test-id',
        update_data={'field': 'value'},
        conditions={'status': 'active'}
    )
    
    # Assert
    assert result.get('success') != False
```

### For Staging

```python
from generic_repo import GenericRepository

# Real AWS session
repo = GenericRepository(
    table_name='your-staging-table',
    primary_key_name='id',
    region_name='us-east-1'
)

# Test
result = repo.update(
    primary_key_value='test-item',
    update_data={'value': 123},
    conditions={'status': {'lt': 10}},
    rejection_message="Value too high"
)

# Check result
if result.get('success') == False:
    print(f"Update rejected: {result['message']}")
else:
    print("Update succeeded!")

# Cleanup
repo.table.delete_item(Key={'id': 'test-item'})
```

## Additional Resources

- **Main Documentation**: See "Conditional Updates" section in `README.md`
- **Examples**: `examples/simple_conditions_example.py`
- **FilterHelper Reference**: `src/generic_repo/filter_helper.py`
- **Quick Start Guide**: `QUICKSTART_TESTING.md`

## Need Help?

- Check existing tests for examples
- Review error messages carefully
- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
- Check AWS CloudWatch logs for DynamoDB errors

