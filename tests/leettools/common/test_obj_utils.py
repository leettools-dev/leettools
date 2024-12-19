from typing import Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import assign_properties, set_field_from_string


def test_obj_copy():

    class TestClass(BaseModel):
        name: str = None
        age: int = None

    test_obj_src = TestClass(name="test", age=10)
    test_obj_dest = TestClass()
    assign_properties(test_obj_src, test_obj_dest)
    assert test_obj_dest.name == "test"
    assert test_obj_dest.age == 10

    test_obj_src = TestClass(name="test", age=10)
    test_obj_dest = TestClass(name="test2", age=20)
    assign_properties(test_obj_src, test_obj_dest, override=False)
    assert test_obj_dest.name == "test2"
    assert test_obj_dest.age == 20

    test_obj_src = TestClass(name="test", age=10)
    test_obj_dest = TestClass(name="test2", age=20)
    assign_properties(test_obj_src, test_obj_dest, override=True)
    assert test_obj_dest.name == "test"
    assert test_obj_dest.age == 10


def test_set_field_from_string() -> None:

    class MyModel(BaseModel):
        name: str
        age: int
        active: bool
        value: Optional[int] = None

    my_model = MyModel(name="", age=0, active=False)

    # Set values using the function
    set_field_from_string(my_model, "name", "John Doe")
    set_field_from_string(my_model, "age", "30")
    set_field_from_string(my_model, "active", "True")

    set_field_from_string(my_model, "value", "-1")

    assert my_model.name == "John Doe"
    assert my_model.age == 30
    assert my_model.active is True
    assert my_model.value == -1
