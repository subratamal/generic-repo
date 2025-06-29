# Generic DynamoDB Repository

A powerful, production-ready Python package for DynamoDB operations with repository pattern supporting both **synchronous** and **asynchronous** operations.

## Features

- **Dual Interface**: Both sync and async implementations with identical APIs
- **Repository Pattern**: Clean, standardized interface for DynamoDB operations
- **Comprehensive Operations**: CRUD, batch operations, queries, and index-based searches
- **Auto-Serialization**: Automatic data type conversion for DynamoDB compatibility
- **Expiration Support**: Built-in TTL handling for automatic data expiration
- **Composite Key Support**: Full support for partition + sort key tables
- **Debug Mode**: Safe testing without actual database operations
- **Extensive Logging**: Comprehensive logging support for debugging
- **Type Hints**: Full type annotations for better IDE support

## Installation

```bash
pip install generic-repo
```

The package includes both synchronous and asynchronous functionality out of the box.

### Development Installation
```bash
pip install generic-repo[dev]
```

## Quick Start

### Synchronous Usage

```python
import boto3
from src import GenericRepository

# Initialize DynamoDB table
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('your-table-name')

# Create repository
repo = GenericRepository(
    table=table,
    primary_key_name='id',
    data_expiration_days=30  # Optional: TTL support
)

# Basic operations
item = repo.save('user-123', {'name': 'John Doe', 'email': 'john@example.com'})
loaded_item = repo.load('user-123')
repo.delete('user-123')
```

### Asynchronous Usage

```python
import asyncio
import aioboto3
from generic_repo import AsyncGenericRepository

async def main():
    # Initialize async DynamoDB session
    session = aioboto3.Session()
    
    async with session.resource('dynamodb', region_name='us-east-1') as dynamodb:
        table = await dynamodb.Table('your-table-name')
        
        # Create async repository
        async with AsyncGenericRepository(
            table=table,
            primary_key_name='id',
            data_expiration_days=30
        ) as repo:
            # Basic async operations
            item = await repo.save('user-123', {'name': 'John Doe', 'email': 'john@example.com'})
            loaded_item = await repo.load('user-123')
            
            # Async generator for scanning
            async for item in repo.load_all():
                print(item)

asyncio.run(main())
```

## API Reference

Both `GenericRepository` and `AsyncGenericRepository` provide identical APIs:

### Basic Operations
- `load(key)` / `await load(key)` - Load item by primary key
- `save(key, data)` / `await save(key, data)` - Save item
- `delete(key)` / `await delete(key)` - Delete item
- `load_or_throw(key)` / `await load_or_throw(key)` - Load item or raise error

### Batch Operations
- `save_batch(items)` / `await save_batch(items)` - Save multiple items
- `delete_batch_by_keys(keys)` / `await delete_batch_by_keys(keys)` - Delete multiple items

### Query Operations
- `find_all(partition_key)` / `await find_all(partition_key)` - Find all items with partition key
- `find_all_with_index(index, key, value)` / `await find_all_with_index(index, key, value)` - Query using GSI/LSI
- `load_all()` / `async for item in load_all()` - Scan entire table

### Composite Key Support
- `load_by_composite_key(key_dict)` / `await load_by_composite_key(key_dict)`
- `save_with_composite_key(item_data)` / `await save_with_composite_key(item_data)`
- `delete_by_composite_key(key_dict)` / `await delete_by_composite_key(key_dict)`

## Best Practices

### For PyPI Package Users

```python
from src import GenericRepository, AsyncGenericRepository

# Both sync and async functionality included out of the box
```

### Error Handling

```python
try:
    repo = GenericRepository(table=table, primary_key_name='id')
    item = repo.load_or_throw('nonexistent-key')
except ValueError as e:
    print(f"Item not found: {e}")
```

### Debug Mode

```python
# Safe for testing - won't make actual database calls
repo = GenericRepository(
    table=table,
    primary_key_name='id',
    debug_mode=True
)
```

## Requirements

- Python 3.9+
- boto3 >= 1.26.0
- botocore >= 1.29.0
- aiobotocore >= 2.5.0
- aioboto3 >= 11.0.0
- types-aiobotocore[dynamodb] >= 2.5.0

## License

Proprietary License - See LICENSE file for details.

## Contributing

See CONTRIBUTING.md for development setup and contribution guidelines.

## Changelog

See CHANGELOG.md for version history and changes.

## 🚀 Features

- **Simple & Composite Key Support**: Works with both simple primary key tables and composite key (partition + sort key) tables
- **Comprehensive CRUD Operations**: Create, Read, Update, Delete operations with error handling
- **Batch Operations**: Efficient batch save and delete operations that automatically handle DynamoDB's 25-item limit
- **Advanced Querying**: Query operations with automatic pagination support
- **Index Support**: Query operations on Global Secondary Indexes (GSI) and Local Secondary Indexes (LSI)
- **Automatic Data Serialization**: Handles Python to DynamoDB data type conversion seamlessly
- **Built-in Expiration**: Optional automatic item expiration using TTL
- **Debug Mode**: Testing-friendly debug mode that skips actual database operations
- **Comprehensive Logging**: Built-in logging support for monitoring and debugging
- **Type Hints**: Full type annotations for better IDE support and code quality

## 📦 Installation

### From PyPI (Recommended)
```bash
pip install generic-repo
```

### From GitHub
```bash
pip install git+https://github.com/subratamal/generic-repo.git
```

### For Development
```bash
git clone https://github.com/subratamal/generic-repo.git
cd generic-repo
pip install -e .
```

## 🔧 Requirements

- Python 3.9+
- boto3 ~= 1.38.29
- botocore ~= 1.38.29

## 📖 Quick Start

### Basic Setup

```python
import boto3
from src import GenericRepository

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('your-table-name')

# Create repository instance
repo = GenericRepository(
    table=table,
    primary_key_name='id',
    data_expiration_days=30,  # Optional: items expire after 30 days
    debug_mode=False
)
```

### Basic Operations

```python
# Save an item
item_data = {'name': 'John Doe', 'email': 'john@example.com', 'age': 30}
saved_item = repo.save('user-123', item_data)

# Load an item
user = repo.load('user-123')
if user:
    print(f"User: {user['name']}")

# Load with exception if not found
try:
    user = repo.load_or_throw('user-123')
    print(f"User: {user['name']}")
except ValueError as e:
    print(f"User not found: {e}")

# Delete an item
repo.delete('user-123')
```

### Composite Key Operations

```python
# For tables with partition key + sort key
composite_data = {
    'partition_key': 'USER',
    'sort_key': 'profile#123',
    'name': 'John Doe',
    'email': 'john@example.com'
}

# Save with composite key
repo.save_with_composite_key(composite_data)

# Load with composite key
key_dict = {'partition_key': 'USER', 'sort_key': 'profile#123'}
user = repo.load_by_composite_key(key_dict)

# Delete with composite key
repo.delete_by_composite_key(key_dict)
```

### Batch Operations

```python
# Batch save multiple items
users = [
    {'id': 'user-1', 'name': 'Alice', 'email': 'alice@example.com'},
    {'id': 'user-2', 'name': 'Bob', 'email': 'bob@example.com'},
    {'id': 'user-3', 'name': 'Charlie', 'email': 'charlie@example.com'}
]
repo.save_batch(users)

# Batch delete by keys
keys_to_delete = [
    {'id': 'user-1'},
    {'id': 'user-2'},
    {'id': 'user-3'}
]
repo.delete_batch_by_keys(keys_to_delete)
```

### Query Operations

```python
# Find all items with a specific partition key
items = repo.find_all('USER')

# Scan all items in the table (use carefully!)
for item in repo.load_all():
    print(f"Item: {item}")

# Count items in table
total_items = repo.count()
print(f"Total items: {total_items}")
```

### Index-Based Queries

```python
# Query using Global Secondary Index (GSI)
items = repo.find_all_with_index(
    index_name='email-index',
    key_name='email', 
    key_value='john@example.com'
)

# Find first matching item from index
item = repo.find_one_with_index(
    index_name='status-index',
    key_name='status',
    key_value='active'
)
```

## 🏗️ Advanced Configuration

### Custom Logger

```python
import logging

# Setup custom logger
logger = logging.getLogger('my-app')
logger.setLevel(logging.INFO)

repo = GenericRepository(
    table=table,
    primary_key_name='id',
    logger=logger
)
```

### Debug Mode for Testing

```python
# Enable debug mode to skip actual database operations
repo = GenericRepository(
    table=table,
    primary_key_name='id',
    debug_mode=True  # Perfect for unit testing
)
```

### Automatic Item Expiration

```python
# Items will automatically expire after 7 days
repo = GenericRepository(
    table=table,
    primary_key_name='id',
    data_expiration_days=7
)
```

## 🧪 Testing

The package includes comprehensive test coverage. Run tests with:

```bash
# Install development dependencies
pip install -e .[dev]

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=generic_repo --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

```bash
git clone https://github.com/subratamal/generic-repo.git
cd generic-repo
pip install -e .[dev]
```

### Code Quality

This project uses:
- **Ruff** for linting and formatting
- **Type hints** for better code quality
- **Comprehensive docstrings** for documentation

```bash
# Format code
ruff check --fix .
ruff format .
```

## 📄 License

This project is licensed under the Proprietary License. See the LICENSE file for details.

## 🔗 Links

- **GitHub Repository**: https://github.com/subratamal/generic-repo
- **PyPI Package**: https://pypi.org/project/generic-repo/
- **Documentation**: https://github.com/subratamal/generic-repo/wiki
- **Issue Tracker**: https://github.com/subratamal/generic-repo/issues

## 📞 Support

- **Email**: 06.subrat@gmail.com
- **GitHub Issues**: https://github.com/subratamal/generic-repo/issues

## 🎯 Roadmap

- [x] Async/await support for better performance
- [ ] More advanced query builders
- [ ] Built-in caching layer
- [ ] CloudFormation templates for common DynamoDB setups
- [ ] Integration with AWS CDK

---

**Made with ❤️ by Subrat** 