"""
Generic DynamoDB Repository Package

This package provides both synchronous and asynchronous repository classes
for DynamoDB operations with a consistent interface.

Classes:
    GenericRepository: Synchronous DynamoDB repository
    AsyncGenericRepository: Asynchronous DynamoDB repository

Example:
    from src import GenericRepository, AsyncGenericRepository

    # Sync usage
    repo = GenericRepository(table=table, primary_key_name='id')
    item = repo.load('key1')

    # Async usage
    async with AsyncGenericRepository(table=async_table, primary_key_name='id') as repo:
        item = await repo.load('key1')
"""

from .async_repo import AsyncGenericRepository

# Import both repository classes
from .sync_repo import GenericRepository

# Export both classes
__all__ = ['GenericRepository', 'AsyncGenericRepository']

# Package metadata
__version__ = '1.0.0'
__author__ = 'Subrat'
__email__ = '06.subrata@gmail.com'
__description__ = 'Generic DynamoDB Repository with sync and async support'
