from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class BaseCondition(BaseModel):
    field: str
    # Added "like" operator
    operator: Literal["==", "!=", ">", "<", ">=", "<=", "in", "like"]
    value: Any

    @model_validator(mode="after")
    def validate_operator(cls, values):
        operator = values.operator
        value = values.value

        if operator == "in":
            if not isinstance(value, list):
                raise ValueError("Value must be a list for 'in' operator.")
        if isinstance(value, list):
            if operator != "in":
                raise ValueError("Operator must be 'in' for list values.")
        return values


class Filter(BaseModel):
    relation: Optional[Literal["and", "or", "not"]] = None
    conditions: List[Union[BaseCondition, "Filter"]] = Field(..., min_items=1)

    @model_validator(mode="after")
    def validate_criteria(cls, values):
        relation = values.relation
        conditions = values.conditions

        # If operator is None, allow exactly one condition
        if relation is None:
            if len(conditions) != 1:
                raise ValueError(
                    "When 'operator' is None, there must be exactly one condition."
                )
        elif relation in {"and", "or"}:
            # If operator is 'and' or 'or', must have at least two conditions
            if len(conditions) < 2:
                raise ValueError(
                    "When 'operator' is 'and' or 'or', there must be at least two conditions."
                )
        elif relation == "not":
            # If operator is 'not', must have exactly one condition
            if len(conditions) != 1:
                raise ValueError(
                    "When 'operator' is 'not', there must be exactly one condition."
                )
        return values


# Needed for recursive model references
Filter.model_rebuild()
