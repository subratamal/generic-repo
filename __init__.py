"""
Generic Repository Package for DynamoDB Operations

A comprehensive repository pattern implementation for Amazon DynamoDB that provides
a clean, standardized interface for common database operations including CRUD,
batch operations, querying, and index-based searches.

Key Features:
- Simple and composite key support
- Automatic data serialization
- Built-in expiration handling
- Batch operations for performance
- Comprehensive query capabilities
- Debug mode for testing
- Extensive logging support
"""

from .generic_repo import GenericRepository

__version__ = '1.0.0'
__author__ = 'Subrat'
__email__ = '06.subrat@gmail.com'

__all__ = ['GenericRepository']
