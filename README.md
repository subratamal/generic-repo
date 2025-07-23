# Generic DynamoDB Repository

A powerful, production-ready Python package for DynamoDB operations with repository pattern supporting both **synchronous** and **asynchronous** operations.

## Features

- **Dual Interface**: Both sync and async implementations with identical APIs
- **Repository Pattern**: Clean, standardized interface for DynamoDB operations
- **Comprehensive Operations**: CRUD, batch operations, queries, and index-based searches
- **Advanced Filtering**: Powerful client-side filtering with multiple operators and conditions
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
from generic_repo import GenericRepository

# Create repository - no need for boto3 setup!
repo = GenericRepository(
    table_name='your-table-name',
    primary_key_name='id',
    region_name='us-east-1',  # Optional: defaults to AWS SDK default
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
from generic_repo import AsyncGenericRepository

async def main():
    # Create async repository - no need for aioboto3 setup!
    async with AsyncGenericRepository(
        table_name='your-table-name',
        primary_key_name='id',
        region_name='us-east-1',  # Optional: defaults to AWS SDK default
        data_expiration_days=30
    ) as repo:
        # Basic async operations
        item = await repo.save('user-123', {'name': 'John Doe', 'email': 'john@example.com'})
        loaded_item = await repo.load('user-123')
        
        # Async generator for scanning
        async for item in repo.load_all():
            print(item)
            
        # Async scanning with filters
        async for item in repo.load_all(filters={'status': 'active'}):
            print(f"Active item: {item}")

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
- `find_all(partition_key, filters=None)` / `await find_all(partition_key, filters=None)` - Find all items with partition key
- `find_all_with_index(index, key, value, filters=None)` / `await find_all_with_index(index, key, value, filters=None)` - Query using GSI/LSI
- `find_one_with_index(index, key, value, filters=None)` / `await find_one_with_index(index, key, value, filters=None)` - Find first item using GSI/LSI
- `load_all(filters=None)` / `async for item in load_all(filters=None)` - Scan entire table

### Composite Key Support
- `load_by_composite_key(key_dict)` / `await load_by_composite_key(key_dict)`
- `save_with_composite_key(item_data)` / `await save_with_composite_key(item_data)`
- `delete_by_composite_key(key_dict)` / `await delete_by_composite_key(key_dict)`

## Best Practices

### For PyPI Package Users

```python
from generic_repo import GenericRepository, AsyncGenericRepository

# Both sync and async functionality included out of the box
```

### Error Handling

```python
try:
    repo = GenericRepository(table_name='your-table-name', primary_key_name='id', region_name='us-east-1')
    item = repo.load_or_throw('nonexistent-key')
except ValueError as e:
    print(f"Item not found: {e}")
```

### Debug Mode

```python
# Safe for testing - won't make actual database calls
repo = GenericRepository(
    table_name='your-table-name',
    primary_key_name='id',
    region_name='us-east-1',
    debug_mode=True
)
```

## Requirements

- Python 3.9+

**Note**: boto3, aioboto3, and related dependencies are automatically installed and managed by the package. You don't need to install them manually!

## License

MIT License - See LICENSE file for details.

## Contributing

See CONTRIBUTING.md for development setup and contribution guidelines.

## Changelog

See CHANGELOG.md for version history and changes.

## 🚀 Features

- **Simple & Composite Key Support**: Works with both simple primary key tables and composite key (partition + sort key) tables
- **Comprehensive CRUD Operations**: Create, Read, Update, Delete operations with error handling
- **Batch Operations**: Efficient batch save and delete operations that automatically handle DynamoDB's 25-item limit
- **Advanced Querying**: Query operations with automatic pagination support
- **Powerful Filtering**: Client-side filtering with 12+ operators (eq, ne, gt, lt, contains, between, etc.)
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

**Note**: All AWS dependencies (boto3, aioboto3, botocore, etc.) are automatically managed by the package - no manual installation required!

## 📖 Quick Start

### Basic Setup

```python
from generic_repo import GenericRepository

# Create repository instance - no boto3 setup needed!
repo = GenericRepository(
    table_name='your-table-name',
    primary_key_name='id',
    region_name='us-east-1',  # Optional: defaults to AWS SDK default
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

# Find items with filtering
active_users = repo.find_all('USER', filters={'status': 'active'})

# Scan all items in the table (use carefully!)
for item in repo.load_all():
    print(f"Item: {item}")

# Scan with filtering
for item in repo.load_all(filters={'age': {'gt': 18}}):
    print(f"Adult: {item}")

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

# Query with additional filtering
active_admins = repo.find_all_with_index(
    index_name='role-index',
    key_name='role',
    key_value='admin',
    filters={'status': 'active', 'last_login': {'exists': True}}
)

# Find first matching item from index
item = repo.find_one_with_index(
    index_name='status-index',
    key_name='status',
    key_value='active'
)

# Find first item with filtering
recent_active = repo.find_one_with_index(
    index_name='status-index',
    key_name='status',
    key_value='active',
    filters={'last_activity': {'gt': '2024-01-01'}}
)
```

## 🔍 Advanced Filtering

The repository supports powerful filtering capabilities for refining query results. Filters can be applied to `load_all()`, `find_all()`, `find_all_with_index()`, and `find_one_with_index()` methods.

### Filter Formats

#### 1. Simple Equality
```python
# Find all active users
active_users = repo.find_all('USER', filters={'status': 'active'})

# Scan for items with specific category
async for item in repo.load_all(filters={'category': 'electronics'}):
    print(item)
```

#### 2. Comparison Operators
```python
# Users older than 25
filters = {'age': {'gt': 25}}
older_users = repo.find_all('USER', filters=filters)

# Products with price between $10 and $50
filters = {'price': {'between': [10, 50]}}
products = repo.find_all('PRODUCT', filters=filters)

# Items with score >= 90
filters = {'score': {'ge': 90}}
high_scores = repo.find_all('SCORE', filters=filters)
```

#### 3. String Operations
```python
# Names containing "John"
filters = {'name': {'contains': 'John'}}
users = repo.find_all('USER', filters=filters)

# Emails starting with "admin"
filters = {'email': {'begins_with': 'admin'}}
admins = repo.find_all('USER', filters=filters)
```

#### 4. List and Set Operations
```python
# Users in specific cities
filters = {'city': {'in': ['New York', 'Los Angeles', 'Chicago']}}
city_users = repo.find_all('USER', filters=filters)

# Items with tags containing "python"
filters = {'tags': {'contains': 'python'}}
items = repo.find_all('ITEM', filters=filters)
```

#### 5. Existence Checks
```python
# Items that have an optional field
filters = {'optional_field': {'exists': True}}
items_with_field = repo.find_all('ITEM', filters=filters)

# Items without deleted_at field (active items)
filters = {'deleted_at': {'not_exists': True}}
active_items = repo.find_all('ITEM', filters=filters)
```

#### 6. Multiple Conditions (AND Logic)
```python
# Active users older than 18 in New York
filters = {
    'status': 'active',
    'age': {'gt': 18},
    'city': 'New York'
}
users = repo.find_all('USER', filters=filters)
```

#### 7. Type-Explicit Filters
```python
# For precise numeric comparisons
filters = {
    'price': {
        'value': 19.99,
        'type': 'N',  # Numeric type
        'operator': 'ge'
    }
}
products = repo.find_all('PRODUCT', filters=filters)
```

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals (default) | `{'status': 'active'}` |
| `ne` | Not equals | `{'status': {'ne': 'deleted'}}` |
| `lt` | Less than | `{'age': {'lt': 30}}` |
| `le` | Less than or equal | `{'age': {'le': 30}}` |
| `gt` | Greater than | `{'score': {'gt': 85}}` |
| `ge` | Greater than or equal | `{'score': {'ge': 85}}` |
| `between` | Between two values | `{'age': {'between': [18, 65]}}` |
| `in` | In list of values | `{'status': {'in': ['active', 'pending']}}` |
| `contains` | Contains substring/value | `{'name': {'contains': 'John'}}` |
| `begins_with` | String begins with | `{'email': {'begins_with': 'admin'}}` |
| `exists` | Attribute exists | `{'phone': {'exists': True}}` |
| `not_exists` | Attribute doesn't exist | `{'deleted_at': {'not_exists': True}}` |

### Filtering with Index Queries

```python
# Find active users in a specific index with additional filters
active_admins = repo.find_all_with_index(
    index_name='role-index',
    key_name='role',
    key_value='admin',
    filters={'status': 'active', 'last_login': {'exists': True}}
)

# Async version
async for user in repo.find_all_with_index(
    index_name='status-index',
    key_name='status', 
    key_value='active',
    filters={'age': {'gt': 21}}
):
    print(f"Adult active user: {user['name']}")
```

### Performance Notes

- Filters are applied **after** the initial query/scan operation
- For better performance, use proper indexing strategies rather than relying solely on filters
- Filters work on the client side after data retrieval, so they don't reduce DynamoDB read costs
- Consider using GSI/LSI for frequently filtered attributes

## 🏗️ Advanced Configuration

### Custom Logger

```python
import logging

# Setup custom logger
logger = logging.getLogger('my-app')
logger.setLevel(logging.INFO)

repo = GenericRepository(
    table_name='your-table-name',
    primary_key_name='id',
    region_name='us-east-1',
    logger=logger
)
```

### Debug Mode for Testing

```python
# Enable debug mode to skip actual database operations
repo = GenericRepository(
    table_name='your-table-name',
    primary_key_name='id',
    region_name='us-east-1',
    debug_mode=True  # Perfect for unit testing
)
```

### Automatic Item Expiration

```python
# Items will automatically expire after 7 days
repo = GenericRepository(
    table_name='your-table-name',
    primary_key_name='id',
    region_name='us-east-1',
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

This project is licensed under the MIT License. See the LICENSE file for details.

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
- [x] Advanced filtering with multiple operators and conditions
- [ ] More advanced query builders
- [ ] OR logic support for filters
- [ ] Built-in caching layer
- [ ] CloudFormation templates for common DynamoDB setups
- [ ] Integration with AWS CDK

---

**Made with ❤️ by Subrat** 