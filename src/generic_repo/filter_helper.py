"""
Filter helper for DynamoDB repositories.

This module provides filtering functionality that can be shared between
sync and async repository implementations.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from boto3.dynamodb.conditions import Attr


class FilterHelper:
    """
    Helper class for converting JSON filters to DynamoDB FilterExpressions.

    This class provides methods to convert client-friendly JSON filter formats
    into DynamoDB-compatible filter expressions without requiring clients to
    import boto3 or understand DynamoDB-specific syntax.
    """

    @staticmethod
    def convert_value_to_dynamodb_type(value: Any, explicit_type: Optional[str] = None) -> Any:
        """
        Convert a value to appropriate DynamoDB type with optional explicit type hint.

        Args:
            value: The value to convert
            explicit_type: Optional explicit type ('S', 'N', 'B', 'SS', 'NS', 'BS', 'M', 'L', 'NULL', 'BOOL')

        Returns:
            Value converted to appropriate DynamoDB type
        """
        if explicit_type:
            if explicit_type == 'N' and isinstance(value, (int, float)):
                return Decimal(str(value))
            elif explicit_type == 'S':
                return str(value)
            elif explicit_type == 'BOOL':
                return bool(value)
            # Add other explicit type conversions as needed

        # Auto-detect type
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, str):
            return value
        elif isinstance(value, list):
            return [FilterHelper.convert_value_to_dynamodb_type(v) for v in value]
        elif isinstance(value, dict):
            return {k: FilterHelper.convert_value_to_dynamodb_type(v) for k, v in value.items()}
        else:
            return str(value)

    @staticmethod
    def build_filter_expression(filters: Dict[str, Any]) -> Optional[Any]:
        """
        Convert JSON filters to DynamoDB FilterExpression.

        Supports multiple filter formats:
        1. Simple equality: {"attribute": "value"}
        2. Operator format: {"attribute": {"operator": "value"}}
        3. List format for multiple conditions on same attribute
        4. Type hints: {"attribute": {"value": "val", "type": "S"}}

        Supported operators:
        - eq: equals (default)
        - ne: not equals
        - lt: less than
        - le: less than or equal
        - gt: greater than
        - ge: greater than or equal
        - between: between two values (value should be [min, max])
        - in: in list of values
        - contains: contains substring/value
        - begins_with: string begins with
        - exists: attribute exists (no value needed)
        - not_exists: attribute does not exist (no value needed)

        Args:
            filters: Dictionary containing filter conditions

        Returns:
            DynamoDB FilterExpression or None if no filters

        Examples:
            {"status": "active"}
            {"age": {"gt": 18}}
            {"name": {"begins_with": "John"}}
            {"tags": {"contains": "python"}}
            {"score": {"between": [10, 20]}}
            {"category": {"in": ["tech", "science"]}}
            {"optional_field": {"exists": True}}
            {"deleted_at": {"not_exists": True}}
            {"price": {"value": 19.99, "type": "N", "operator": "ge"}}
        """
        if not filters:
            return None

        filter_expressions = []

        for attr_name, condition in filters.items():
            if isinstance(condition, dict):
                # Handle operator format
                if 'operator' in condition:
                    operator = condition['operator']
                    value = condition.get('value')
                    explicit_type = condition.get('type')
                elif len(condition) == 1:
                    # Single operator: {"gt": 18}
                    operator, value = next(iter(condition.items()))
                    explicit_type = None
                else:
                    # Handle value with type: {"value": "val", "type": "S"}
                    value = condition.get('value', condition)
                    operator = condition.get('operator', 'eq')
                    explicit_type = condition.get('type')

                # Convert value to appropriate DynamoDB type
                if value is not None:
                    value = FilterHelper.convert_value_to_dynamodb_type(value, explicit_type)

                # Build the filter expression based on operator
                if operator == 'eq':
                    filter_expressions.append(Attr(attr_name).eq(value))
                elif operator == 'ne':
                    filter_expressions.append(Attr(attr_name).ne(value))
                elif operator == 'lt':
                    filter_expressions.append(Attr(attr_name).lt(value))
                elif operator == 'le':
                    filter_expressions.append(Attr(attr_name).lte(value))
                elif operator == 'gt':
                    filter_expressions.append(Attr(attr_name).gt(value))
                elif operator == 'ge':
                    filter_expressions.append(Attr(attr_name).gte(value))
                elif operator == 'between':
                    if isinstance(value, list) and len(value) == 2:
                        filter_expressions.append(Attr(attr_name).between(value[0], value[1]))
                    else:
                        raise ValueError("'between' operator requires a list of two values")
                elif operator == 'in':
                    if isinstance(value, list):
                        filter_expressions.append(Attr(attr_name).is_in(value))
                    else:
                        raise ValueError("'in' operator requires a list of values")
                elif operator == 'contains':
                    filter_expressions.append(Attr(attr_name).contains(value))
                elif operator == 'begins_with':
                    filter_expressions.append(Attr(attr_name).begins_with(value))
                elif operator == 'exists':
                    filter_expressions.append(Attr(attr_name).exists())
                elif operator == 'not_exists':
                    filter_expressions.append(Attr(attr_name).not_exists())
                else:
                    raise ValueError(f'Unsupported operator: {operator}')
            else:
                # Simple equality: {"attribute": "value"}
                value = FilterHelper.convert_value_to_dynamodb_type(condition)
                filter_expressions.append(Attr(attr_name).eq(value))

        # Combine all filter expressions with AND logic
        if len(filter_expressions) == 1:
            return filter_expressions[0]
        elif len(filter_expressions) > 1:
            result = filter_expressions[0]
            for expr in filter_expressions[1:]:
                result = result & expr
            return result

        return None
