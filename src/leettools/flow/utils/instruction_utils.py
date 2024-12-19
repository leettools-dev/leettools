import json
from typing import List

from leettools.flow.schemas.instruction_vars import InstructionVars


def get_instruction_description(vars: List[InstructionVars]) -> str:
    """
    Convert a list of InstructionVars to a human-readable string.
    """
    description_str = "Supported variables:\n"

    for var in vars:
        var_name = var.var_name
        var_type = var.var_type
        var_description = var.var_description
        required = var.required
        default_value = var.default_value

        description_str += (
            f"{var_name}: {var_type} - {var_description}"
            f"{' (required)' if required else ''}"
            f"{' (default: ' + default_value + ')' if default_value is not None else ''}\n"
        )
    return description_str


def get_instruction_json(vars: List[InstructionVars]) -> str:
    return json.dumps([var.model_dump() for var in vars])
