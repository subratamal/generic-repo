# Conditional Updates - Quick Reference

## ✨ Simple Dict-Based Syntax

No need to import `Attr()` from boto3! Just use simple dictionaries:

```python
from generic_repo import GenericRepository

repo = GenericRepository(
    table_name='my-table',
    primary_key_name='id',
    region_name='us-east-1'
)

# Simple condition
result = repo.update(
    primary_key_value='item-123',
    update_data={'value': 100},
    conditions={'status': 'active'},
    rejection_message="Item must be active"
)
```

## 📋 Operator Reference

| Operator | Dict Syntax | Example |
|----------|-------------|---------|
| **Equals** | `{'field': value}` | `{'status': 'active'}` |
| **Not Equals** | `{'field': {'ne': value}}` | `{'status': {'ne': 'deleted'}}` |
| **Less Than** | `{'field': {'lt': value}}` | `{'version': {'lt': 10}}` |
| **Less or Equal** | `{'field': {'lte': value}}` | `{'age': {'lte': 65}}` |
| **Greater Than** | `{'field': {'gt': value}}` | `{'score': {'gt': 50}}` |
| **Greater or Equal** | `{'field': {'gte': value}}` | `{'age': {'gte': 18}}` |
| **Between** | `{'field': {'between': [min, max]}}` | `{'price': {'between': [10, 100]}}` |
| **IN** | `{'field': {'in': [values]}}` | `{'status': {'in': ['pending', 'active']}}` |
| **Contains** | `{'field': {'contains': value}}` | `{'tags': {'contains': 'urgent'}}` |
| **Begins With** | `{'field': {'begins_with': prefix}}` | `{'email': {'begins_with': 'admin'}}` |
| **Exists** | `{'field': {'exists': True}}` | `{'phone': {'exists': True}}` |
| **Not Exists** | `{'field': {'not_exists': True}}` | `{'deleted_at': {'not_exists': True}}` |

## 🔗 Multiple Conditions (AND Logic)

```python
# All conditions must be met
repo.update(
    primary_key_value='order-123',
    update_data={'shipped': True},
    conditions={
        'status': 'pending',           # AND
        'payment_received': True,      # AND
        'amount': {'gt': 0}            # AND
    }
)
```

## 🎯 Common Patterns

### Optimistic Locking

```python
# Read current version
item = repo.load('doc-123')
current_version = item['version']

# Update only if version unchanged
result = repo.update(
    primary_key_value='doc-123',
    update_data={
        'content': 'Updated',
        'version': current_version + 1
    },
    conditions={'version': current_version},
    rejection_message="Document was modified by another user"
)
```

### Workflow Validation

```python
# Only allow state transitions
repo.update(
    primary_key_value='task-456',
    update_data={'status': 'completed'},
    conditions={
        'status': {'in': ['pending', 'in_progress']},
        'assignee': {'exists': True}
    },
    rejection_message="Invalid state transition"
)
```

### E-commerce Protection

```python
# Prevent modifying shipped orders
repo.update(
    primary_key_value='order-789',
    update_data={'quantity': 5},
    conditions={'status': {'ne': 'shipped'}},
    rejection_message="Cannot modify shipped orders"
)
```

## 🔄 Async Usage

```python
import asyncio
from generic_repo import AsyncGenericRepository

async def main():
    async with AsyncGenericRepository(
        table_name='orders',
        primary_key_name='id',
        region_name='us-east-1'
    ) as repo:
        result = await repo.update(
            primary_key_value='order-123',
            update_data={'status': 'shipped'},
            conditions={'status': 'pending'},
            rejection_message="Order must be pending"
        )

asyncio.run(main())
```

## ✅ Error Handling

```python
result = repo.update(
    primary_key_value='item-123',
    update_data={'value': 100},
    conditions={'status': 'active'},
    rejection_message="Item must be active"
)

# Check if update was rejected
if result.get('success') == False:
    print(f"Update rejected: {result['message']}")
    print(f"Reason: {result.get('reason', 'Condition not met')}")
else:
    print(f"Update successful: {result}")
```

## 🔧 Composite Keys

```python
result = repo.update_by_composite_key(
    key_dict={'user_id': 'user-123', 'order_id': 'order-456'},
    update_data={'total': 150.00},
    conditions={'status': 'draft'},
    rejection_message="Can only modify draft orders"
)
```

## 🚀 Advanced: Direct Attr() Usage

For complex conditions with OR logic:

```python
from boto3.dynamodb.conditions import Attr

result = repo.update(
    primary_key_value='item-999',
    update_data={'processed': True},
    conditions=(
        Attr('status').eq('pending') & 
        (Attr('priority').gt(5) | Attr('urgent').eq(True))
    )
)
```

## 📚 More Information

- **Full Documentation**: See "Conditional Updates" section in `README.md`
- **Examples**: `examples/simple_conditions_example.py`
- **Testing Guide**: `tests/README_TESTING.md`
- **Quick Start**: `QUICKSTART_TESTING.md`

## 💡 Key Benefits

- ✅ **Atomic**: Server-side checks prevent race conditions
- ✅ **Simple**: Dict-based syntax is easy to read/write
- ✅ **Flexible**: Supports both dicts and Attr() conditions
- ✅ **Dynamic**: Easy to construct from API/config
- ✅ **Safe**: No extra read operations needed


