TestPyPI failed due to first uploading the package incorrectly from terminal using `python -m twine ... ` and then I removed it from the testpypi website.

But the next time, it won't let me upload from the GH CI.

I've then uploaded the prod package from the CLI correctly.

SO PyPi version is 2.0.0 but GH shows differently, which is incorrect

I've to wait for the next release to fix this on GH.



# 🚀 Generic DynamoDB Repository v2.0.0 - Major Release

We're excited to announce the release of Generic DynamoDB Repository v2.0.0! This major version brings significant improvements to developer experience, simplifies the API, and opens the project to the broader community with an MIT license.

## 🌟 What's New

### 🎯 Simplified API - No More boto3 Hassle!

The biggest change in v2.0.0 is the elimination of manual boto3/aioboto3 resource management. You can now initialize repositories with just a table name!

```python
# v2.0.0 - Simple and clean! ✨
from generic_repo import GenericRepository

repo = GenericRepository(
    table_name='my-table',
    primary_key_name='id'
)

# That's it! No boto3 imports or resource management needed.
```

### ⚡ Full Async/Await Support

v2.0.0 introduces comprehensive asynchronous functionality:
- **AsyncGenericRepository**: Complete async implementation with identical API
- **Async Context Managers**: Automatic resource management with `async with`
- **Async Generators**: Memory-efficient scanning with `async for`
- **Parallel Operations**: All async methods support concurrent execution

```python
# Async scanning with automatic pagination
async for item in repo.load_all():
    print(item)

# Async batch operations
await repo.save_batch(items)
```

### 🔍 Extensive Filtering System

Advanced client-side filtering with 12+ operators and multiple formats:
- **12+ Filter Operators**: `eq`, `ne`, `gt`, `lt`, `ge`, `le`, `between`, `in`, `contains`, `begins_with`, `exists`, `not_exists`
- **Multiple Filter Formats**: Simple equality, operator format, type-explicit filters
- **Complex Conditions**: Multiple filters with AND logic
- **Automatic Type Conversion**: Seamless Python to DynamoDB type handling

```python
# Advanced filtering examples
filters = {
    'status': 'active',
    'age': {'gt': 18},
    'name': {'contains': 'John'},
    'score': {'between': [80, 100]},
    'tags': {'contains': 'python'}
}
items = repo.find_all('USER', filters=filters)
```

### 🔐 Built-in Authentication

v2.0.0 automatically handles AWS authentication using:
- AWS default credential chain (environment variables, IAM roles, etc.)
- Optional custom boto3/aioboto3 sessions for advanced scenarios
- Seamless region configuration

## ⚠️ Breaking Changes

### Constructor Changes

**Before (v1.x):**
```python
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('my-table')
repo = GenericRepository(table=table, primary_key_name='id')
```

**After (v2.x):**
```python
repo = GenericRepository(
    table_name='my-table',
    primary_key_name='id'
)
```

### Async Usage Simplified

**Before (v1.x):**
```python
import aioboto3
session = aioboto3.Session()
async with session.resource('dynamodb') as dynamodb:
    table = await dynamodb.Table('my-table')
    async with AsyncGenericRepository(table=table, primary_key_name='id') as repo:
        # operations...
```

**After (v2.x):**
```python
async with AsyncGenericRepository(
    table_name='my-table',
    primary_key_name='id'
) as repo:
    # operations...
```

## 🏆 Key Benefits

| Benefit | Description |
|---------|-------------|
| **🎯 Simplified Usage** | No more boto3 resource management - just provide the table name |
| **⚡ Dual Interface** | Full sync and async support with identical APIs |
| **🔍 Advanced Filtering** | 12+ filter operators with multiple condition formats |
| **🔐 Secure by Default** | Uses AWS best practices for authentication automatically |
| **📦 Reduced Boilerplate** | ~70% less setup code required |
| **🐛 Fewer Errors** | Eliminates common resource management mistakes |
| **🚀 Faster Development** | Get started immediately without AWS SDK complexity |
| **🌍 Open Source** | MIT license enables community contributions |

## 📈 What This Means for You

### New Users
- **Instant Setup**: Install and start using in minutes
- **No AWS SDK Knowledge Required**: Focus on your business logic
- **Production Ready**: Built-in best practices and error handling
- **Modern Python**: Full async/await support for high-performance applications
- **Rich Filtering**: Advanced querying without complex DynamoDB expressions

### Existing Users
- **Migration Required**: Follow our migration guide (takes ~5 minutes)
- **Reduced Code**: Simplify your existing implementations
- **Better Maintainability**: Less infrastructure code to maintain
- **Performance Boost**: Leverage async operations for concurrent workloads
- **Enhanced Querying**: Replace custom filters with built-in operators

## 🛠️ Migration Guide

### Step 1: Update Installation
```bash
pip install --upgrade generic-repo==2.0.0
```

### Step 2: Update Your Code
Replace your existing initialization code:

```python
# Remove boto3 imports and resource creation
# - import boto3
# - dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
# - table = dynamodb.Table('my-table') 

# Replace with simple initialization
repo = GenericRepository(
    table_name='my-table',
    primary_key_name='id',
    region_name='us-west-2'  # Optional
)
```

### Step 3: Test & Explore New Features
All existing method calls work exactly the same - only initialization changes!

**New in v2.0.0 - Try these advanced features:**

```python
# Async operations with context manager
async with AsyncGenericRepository(
    table_name='my-table',
    primary_key_name='id'
) as repo:
    # Async batch operations
    await repo.save_batch([
        {'id': 'user1', 'name': 'Alice', 'age': 25},
        {'id': 'user2', 'name': 'Bob', 'age': 30}
    ])
    
    # Memory-efficient async scanning with filtering
    async for user in repo.load_all(filters={'age': {'gt': 18}}):
        print(f"Adult user: {user['name']}")

# Advanced filtering (sync or async)
complex_filters = {
    'status': 'active',
    'age': {'between': [18, 65]},
    'name': {'contains': 'John'},
    'score': {'ge': 85}
}
results = repo.find_all('USER', filters=complex_filters)
```

## 🏗️ Technical Highlights

**What makes v2.0.0 special:**

### Async Infrastructure
- ✅ Full `aioboto3` integration with automatic resource management
- ✅ Async generators for memory-efficient large dataset processing
- ✅ Context manager support for proper cleanup
- ✅ 100% API parity between sync and async implementations

### Advanced Filtering Engine
- ✅ **FilterHelper** class with 12+ operators
- ✅ JSON-based filter format (no boto3 expressions needed)
- ✅ Automatic type conversion and validation
- ✅ Support for complex nested conditions
- ✅ Works across all query and scan operations

### Simplified Architecture
- ✅ Removed boto3 dependency from client code
- ✅ Built-in AWS authentication patterns
- ✅ Automatic resource lifecycle management
- ✅ Debug mode for testing without AWS calls

## 🔮 What's Next

With v2.0.0's solid foundation, we're planning:
- Advanced query builders
- Built-in caching layer
- OR logic support for filters
- CloudFormation templates
- AWS CDK integration

## 📚 Resources

- **📖 Documentation**: [GitHub Wiki](https://github.com/subratamal/generic-repo/wiki)
- **💻 GitHub**: [subratamal/generic-repo](https://github.com/subratamal/generic-repo)
- **📦 PyPI**: [generic-repo](https://pypi.org/project/generic-repo/)
- **🐛 Issues**: [Report Issues](https://github.com/subratamal/generic-repo/issues)

## 🙏 Thank You

Special thanks to the community for feedback and suggestions that made v2.0.0 possible. The move to MIT license means we can grow this project together!

---

**Install Today:**
```bash
pip install generic-repo==2.0.0
```

**Questions?** Open an issue on GitHub or reach out to the community.

**Made with ❤️ for the developer community**