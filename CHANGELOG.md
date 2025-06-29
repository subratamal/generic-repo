# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-06-29

### BREAKING CHANGES 🚨

- **Major API Change**: Both `GenericRepository` and `AsyncGenericRepository` now accept `table_name` instead of table objects
- **Simplified Authentication**: No longer requires clients to manage boto3/aioboto3 resources
- **Removed Dependency**: Clients no longer need to install and import boto3/aioboto3 directly

### Added

- ✨ **New Constructor Parameters**:
  - `table_name` (required): Name of the DynamoDB table
  - `region_name` (optional): AWS region name
  - `session` (optional): Pre-configured boto3/aioboto3 session for custom authentication
  
- 🔐 **Built-in Authentication Support**:
  - AWS default credentials from environment variables (default)
  - Custom boto3/aioboto3 sessions for advanced authentication scenarios
  - Optional region specification

### Changed

- 🔧 **Constructor Signature** (BREAKING):
  ```python
  # OLD API (v1.x)
  repo = GenericRepository(table=dynamodb_table, primary_key_name='id')
  
  # NEW API (v2.x)
  repo = GenericRepository(table_name='my-table', primary_key_name='id', region_name='us-west-2')
  ```

- 📦 **Internal Resource Management**: 
  - Both repositories now create and manage their own DynamoDB resources internally
  - Automatic resource cleanup in async context managers

### Removed

- ❌ **Removed Parameters** (BREAKING):
  - `table` parameter no longer accepted
  - No support for passing pre-created DynamoDB table objects

### Migration Guide

#### For Sync Repository:
```python
# Before (v1.x)
import boto3
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('my-table')
repo = GenericRepository(
    table=table,
    primary_key_name='id',
    region_name='eu-west-2'  # Optional
)

# After (v2.x)
repo = GenericRepository(
    table_name='my-table',
    primary_key_name='id',
    region_name='eu-west-2'  # Optional
)
```

#### For Async Repository:
```python
# Before (v1.x)
import aioboto3
session = aioboto3.Session()
async with session.resource('dynamodb', region_name='us-west-2') as dynamodb:
    table = await dynamodb.Table('my-table')
    async with AsyncGenericRepository(table=table, primary_key_name='id') as repo:
        # operations

# After (v2.x)
async with AsyncGenericRepository(
    table_name='my-table',
    primary_key_name='id',
    region_name='us-west-2'  # Optional
) as repo:
    # operations
```

### Benefits of v2.0

- 🎯 **Simplified API**: No need to manage boto3/aioboto3 resources manually
- 🔒 **Better Security**: Built-in support for AWS default authentication patterns
- 📦 **Reduced Dependencies**: Clients don't need to import boto3/aioboto3
- 🐛 **Fewer Errors**: Less boilerplate code reduces chances of resource management mistakes
- 🚀 **Easier Testing**: Simplified mocking and testing scenarios

---

## [1.0.0] - 2025-06-23

### Added
- Initial release with sync DynamoDB repository pattern
- Support for basic CRUD operations
- Batch operations for improved performance
- Query operations with pagination
- Index-based queries
- Automatic data serialization and expiration handling
- Comprehensive test suite
- Documentation and examples

### Features
- `GenericRepository` class with full DynamoDB abstraction
- Methods: `save`, `load`, `delete`, `save_batch`, `delete_batch_by_keys`
- Composite key methods: `load_by_composite_key`, `save_with_composite_key`, `delete_by_composite_key`
- Query methods: `find_all`, `load_all`, `count`
- Index methods: `find_one_with_index`, `find_all_with_index`
- Utility methods for expiration and serialization

### Dependencies
- boto3 ~= 1.38.29
- botocore ~= 1.38.29
- Python 3.9+ support

### Documentation
- Comprehensive README with usage examples
- Detailed docstrings for all methods
- Type annotations throughout the codebase

## [Unreleased]

### Planned
- More advanced query builders
- Built-in caching layer
- CloudFormation templates for common DynamoDB setups
- Integration with AWS CDK
- Comprehensive test suite
- Performance benchmarks 