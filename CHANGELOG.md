# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-19

### Added
- Initial release of Generic DynamoDB Repository
- Basic CRUD operations (Create, Read, Update, Delete)
- Support for both simple and composite key tables
- Batch operations for improved performance
- Query operations with automatic pagination
- Index-based queries (GSI/LSI support)
- Automatic data serialization for DynamoDB compatibility
- Built-in item expiration using TTL
- Debug mode for testing environments
- Comprehensive logging support
- Type hints for better IDE support
- Extensive documentation and examples

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
- Async/await support for better performance
- More advanced query builders
- Built-in caching layer
- CloudFormation templates for common DynamoDB setups
- Integration with AWS CDK
- Comprehensive test suite
- Performance benchmarks 