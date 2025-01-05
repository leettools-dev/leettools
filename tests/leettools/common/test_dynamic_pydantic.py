from typing import Dict, List, Optional

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


def test_gen_example():

    # Example usage:
    class Address(BaseModel):
        street: str
        city: str
        zip_code: int

    class XYZ(BaseModel):
        X: int
        Y: str
        Z: List[str]
        details: Optional[Address]
        metadata: Dict[str, float]
        is_active: bool

    example_json = dynamic_model.gen_pydantic_example(XYZ, show_type=False)
    assert example_json != None
    assert type(example_json["X"]) == int
    assert type(example_json["Y"]) == str
    assert type(example_json["Z"]) == list
    assert type(example_json["details"]) == dict
    assert type(example_json["metadata"]) == dict
    assert type(example_json["is_active"]) == bool
    assert example_json["X"] == 42
    assert example_json["Y"] == "example"
    assert example_json["Z"] == ["example"]
    assert example_json["details"] == {
        "street": "example",
        "city": "example",
        "zip_code": 42,
    }
    assert example_json["metadata"] == {"key": 3.14}
    assert example_json["is_active"] == True

    example_json = dynamic_model.gen_pydantic_example(XYZ, show_type=True)
    assert example_json != None
    assert type(example_json["X"]) == str
    assert type(example_json["Y"]) == str
    assert type(example_json["Z"]) == list
    assert type(example_json["details"]) == dict
    assert type(example_json["metadata"]) == dict
    assert type(example_json["is_active"]) == str
    assert example_json["X"] == "int"
    assert example_json["Y"] == "str"
    assert example_json["Z"] == ["str"]
    assert example_json["details"] == {
        "street": "str",
        "city": "str",
        "zip_code": "int",
    }
