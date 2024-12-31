from leettools.eds.rag.search.filter import BaseCondition, Filter
from leettools.eds.rag.search.filter_duckdb import to_duckdb_filter


def test_to_duckdb_filter():
    # Test case 1: Simple condition
    simple_condition = Filter(
        conditions=[BaseCondition(field="age", operator=">", value=30)]
    )
    duckdb_query, fields, values = to_duckdb_filter(simple_condition)
    assert duckdb_query == "age > ?"
    assert fields == ["age"]
    assert values == [30]

    # Test case 2: Nested condition with OR operator
    nested_condition = Filter(
        relation="or",
        conditions=[
            BaseCondition(field="age", operator="<", value=25),
            BaseCondition(field="city", operator="==", value="New York"),
        ],
    )
    duckdb_query, fields, values = to_duckdb_filter(nested_condition)
    assert duckdb_query == "(age < ?) OR (city = ?)"
    assert fields == ["age", "city"]
    assert values == [25, "New York"]

    # Test case 3: Query value with ' and "
    special_char_condition = Filter(
        conditions=[
            BaseCondition(
                field="description",
                operator="like",
                value="He said 'Hello' and \"Welcome\"",
            )
        ],
    )
    duckdb_query, fields, values = to_duckdb_filter(special_char_condition)
    assert duckdb_query == "description LIKE ?"
    assert fields == ["description"]
    assert values == ["He said 'Hello' and \"Welcome\""]

    # Test case 4: Nested three layers with all operators
    complex_nested_condition = Filter(
        relation="and",
        conditions=[
            Filter(
                relation="or",
                conditions=[
                    BaseCondition(field="age", operator="<", value=25),
                    BaseCondition(field="city", operator="==", value="New York"),
                ],
            ),
            Filter(
                relation="not",
                conditions=[
                    BaseCondition(field="status", operator="==", value="inactive")
                ],
            ),
        ],
    )
    duckdb_query, fields, values = to_duckdb_filter(complex_nested_condition)
    assert duckdb_query == "((age < ?) OR (city = ?)) AND (NOT (status = ?))"
    assert fields == ["age", "city", "status"]
    assert values == [25, "New York", "inactive"]

    # Test case 5: operator in
    filter_with_in_operator = Filter(
        relation="and",
        conditions=[
            Filter(
                relation="not",
                conditions=[BaseCondition(field="age", operator=">", value=25)],
            ),
            BaseCondition(
                field="city",
                operator="in",
                value=["New York", "San Francisco", "Boston"],
            ),
        ],
    )
    duckdb_query, fields, values = to_duckdb_filter(filter_with_in_operator)
    assert duckdb_query == "(NOT (age > ?)) AND (city in ?)"
    assert fields == ["age", "city"]
    assert values == [25, ["New York", "San Francisco", "Boston"]]
