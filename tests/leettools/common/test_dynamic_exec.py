from leettools.common.utils.dynamic_exec_util import execute_pydantic_snippet


def test_execute_code_snippet():
    code = """
class MyClass(BaseModel):
    name: str
    value: list[int]
    
class MyOtherClass(BaseModel):
    name: str
    value: list[int]
    
test_var1 = "test1"
test_var2 = 123456
test_var3 = [1, 2, 3, 4, 5]
"""
    result_var_dict, result_type_dict = execute_pydantic_snippet(code)

    assert len(result_var_dict) == 3
    assert result_var_dict["test_var1"] == "test1"
    assert result_var_dict["test_var2"] == 123456
    assert result_var_dict["test_var3"] == [1, 2, 3, 4, 5]

    assert len(result_type_dict) == 2
    class1 = result_type_dict["MyClass"]
    x = class1(name="test", value=[1, 2, 3])
    assert x.name == "test"
    assert x.value == [1, 2, 3]

    class2 = result_type_dict["MyOtherClass"]
    y = class2(name="test", value=[1, 2, 3])
    assert y.name == "test"
    assert y.value == [1, 2, 3]
