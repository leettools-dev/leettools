from typing import List

from pydantic import BaseModel, Field

from leettools.common.utils import dynamic_model
from leettools.common.utils.obj_utils import add_fieldname_constants


@add_fieldname_constants
class CompanyTest(BaseModel):
    """
    This is a data structure for dynamic field tests.
    """

    name: str = Field(..., description="The name of the company.")
    employees: int = Field(..., description="The number of employees in the company.")
    revenue: float = Field(..., description="The revenue of the company.")


class CompaniesTest(BaseModel):
    id: int = Field(..., description="The ID of the organization.")
    companies: List[CompanyTest] = Field(
        ..., description="The list of companies in the organization."
    )


def test_dynamic_fields_for_pydantic():

    value = CompanyTest(name="A", employees=100, revenue=570.0)
    assert value.name == "A"
    assert value.employees == 100
    assert value.revenue == 570.0

    x = CompanyTest.FIELD_NAME
    assert x == "name"

    y = CompanyTest.FIELD_EMPLOYEES
    assert y == "employees"

    z = CompanyTest.FIELD_REVENUE
    assert z == "revenue"

    try:
        w = CompanyTest.FIELD_XYZ
        assert False
    except Exception as e:
        pass


def test_dynamic_model_for_pydantic():
    schema_dict = {
        "company_name": "str",
        "company_id": "int",
        "amount_raised": "float",
        "round_type": "str",
        "investors": "list[str]",
        "round_date": "str",
        "main_product_or_service": "str",
    }

    example = {
        "company_name": "Company A",
        "company_id": 123,
        "amount_raised": 1000000.0,
        "round_type": "Seed",
        "investors": ["Investor A", "Investor B"],
        "round_date": "2022-01-01",
        "main_product_or_service": "Product A",
    }

    old_class = dynamic_model.create_pydantic_model(
        model_name="DynamicModel", schema_dict=schema_dict
    )
    old_obj = old_class.model_validate(example)
    assert old_obj != None
    assert old_obj.company_name == "Company A"
    assert old_obj.company_id == 123
    assert old_obj.amount_raised == 1000000.0
    assert old_obj.round_type == "Seed"
    assert old_obj.investors == ["Investor A", "Investor B"]
    assert old_obj.round_date == "2022-01-01"
    assert old_obj.main_product_or_service == "Product A"
