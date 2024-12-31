from typing import Any, List, Tuple, Union

from leettools.eds.rag.search.filter import BaseCondition, Filter


def _convert_condition_to_duckdb(
    condition: Union[BaseCondition, Filter]
) -> Tuple[str, List[str], List[Any]]:
    if isinstance(condition, Filter):
        return to_duckdb_filter(condition)
    base_condition: BaseCondition = condition
    if isinstance(base_condition.value, list):
        assert base_condition.operator == "in"
        filter_str = f"{base_condition.field} {base_condition.operator} ?"
        field_list = [base_condition.field]
        value_list = [base_condition.value]
    else:
        if base_condition.operator == "==":
            operator = "="
        elif base_condition.operator == "like":
            operator = "LIKE"
        else:
            operator = base_condition.operator
        filter_str = f"{base_condition.field} {operator} ?"
        field_list = [base_condition.field]
        value_list = [base_condition.value]
    return filter_str, field_list, value_list


def to_duckdb_filter(
    filter: Union[Filter, BaseCondition]
) -> Tuple[str, List[str], List[Any]]:
    """
    Convert a Filter to a DuckDB filter expression.

    Args:
    - filter: The Filter to convert.

    Returns:
    - A tuple of :
        the filter expression
        the list of fields used in the filter
        the list of values, one for each placeholder in the filter expression
    """
    if isinstance(filter, BaseCondition):
        return _convert_condition_to_duckdb(filter)

    if filter.relation is None:
        condition = filter.conditions[0]
        return _convert_condition_to_duckdb(condition)

    sub_filters, fields, values = [], [], []
    if filter.relation != "not":
        assert filter.relation in {"and", "or"}
        relation_str = f" {filter.relation.upper()} "
        for cond in filter.conditions:
            filter_part, field_part, value_part = _convert_condition_to_duckdb(cond)
            sub_filters.append(f"({filter_part})")
            fields.extend(field_part)
            values.extend(value_part)
        conditions_str = relation_str.join(sub_filters)
    else:
        assert len(filter.conditions) == 1
        filter_part, field_part, value_part = _convert_condition_to_duckdb(
            filter.conditions[0]
        )
        conditions_str = f"NOT ({filter_part})"
        fields.extend(field_part)
        values.extend(value_part)
    return conditions_str, fields, values
