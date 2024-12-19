from typing import Optional

from pydantic import BaseModel


class InstructionVars(BaseModel):
    """
    When using a Python program as the input, we can specify the variables that
    the program expects. We can specify a list of InstructionVars and generates
    the instruction string and JSON representation of the variables.
    """

    var_name: str
    var_type: str
    required: bool
    var_description: Optional[str]
    default_value: Optional[str]
