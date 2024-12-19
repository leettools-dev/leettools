import inspect
import traceback
from typing import List, Optional


class EdsExceptionBase(Exception):
    """
    This class serves as the base for all customized exceptions. It ensures that exceptions
    are uniform across the system.
    """

    def __init__(self, exception_message: str):
        """
        Initializes the exception with a detailed message in a specific format.
        """

        self.exception_name = self.__class__.__name__
        self.exception_trace = "".join(traceback.format_stack()[:-2])
        fn, ln, func = self.__get_call_info()
        if not exception_message:
            self.exception_message = f"system exception ({fn}:{ln} {func})"
        else:
            self.exception_message = f"{exception_message} ({fn}:{ln} {func})"
        super(EdsExceptionBase, self).__init__(self.exception_message)

    def __repr__(self):
        """
        Returns a string representation of the exception.
        """
        return "'{}: {}'".format(self.exception_name, self.exception_message)

    @staticmethod
    def __get_call_info():
        """
        Retrieves information about where the exception was raised.
        """
        stack = inspect.stack()

        # stack[1] gives previous function ('info' in our case)
        # stack[2] gives before previous function and so on

        fn = stack[3][1]
        fn = fn.split("/")[-1]
        ln = stack[3][2]
        func = stack[3][3]

        return fn, ln, func


class InsufficientBalanceException(EdsExceptionBase):
    def __init__(self, username: str, balance: int):
        detailed_message = f"Insufficient balance for {username}"
        EdsExceptionBase.__init__(self, detailed_message)


class ConfigValueException(EdsExceptionBase):
    def __init__(self, config_item: str, config_value: str):
        detailed_message = f"{config_item} has invalid value {config_value}."
        EdsExceptionBase.__init__(self, detailed_message)


class UnknownParameterException(EdsExceptionBase):
    def __init__(self, parameter_name: str):
        detailed_message = f"Unknown parameter name {parameter_name}."
        EdsExceptionBase.__init__(self, detailed_message)


class MissingParametersException(EdsExceptionBase):
    def __init__(self, missing_parameter: str):
        detailed_message = f"Expected parameter {missing_parameter} not found."
        EdsExceptionBase.__init__(self, detailed_message)


class ParametersValidationException(EdsExceptionBase):
    def __init__(self, error_msg_list: List[str]):
        detailed_message = f"Parameter validation errors: {error_msg_list}."
        EdsExceptionBase.__init__(self, detailed_message)


class InvalidStatusException(EdsExceptionBase):
    def __init__(self, entity: str, expected: str, actual: str):
        detailed_message = (
            f"Expected status {expected} for {entity}, actual status {actual}"
        )
        EdsExceptionBase.__init__(self, detailed_message)


class InvalidValueException(EdsExceptionBase):
    def __init__(self, name: str, expected: str, actual: str):
        detailed_message = f"{name} should be {expected}, but actual value is {actual}"
        EdsExceptionBase.__init__(self, detailed_message)


class ExpectedFailureException(EdsExceptionBase):
    def __init__(self, failure_desc: str):
        detailed_message = f"Expected failure due to: {failure_desc}"
        EdsExceptionBase.__init__(self, detailed_message)


class UnexpectedOperationFailureException(EdsExceptionBase):
    def __init__(self, operation_desc: str, error: str):
        detailed_message = f"Operation {operation_desc} failed: {error}"
        EdsExceptionBase.__init__(self, detailed_message)


class ModuleLoadingException(EdsExceptionBase):
    def __init__(self, module_path: str, err_msg: Optional[str] = ""):
        detailed_message = f"Faile to load module from path {module_path}: {err_msg}"
        EdsExceptionBase.__init__(self, detailed_message)


class EntityNotFoundException(EdsExceptionBase):
    def __init__(self, entity_name, entity_type):
        detailed_message = f"{entity_type} {entity_name} does not exist."
        EdsExceptionBase.__init__(self, detailed_message)


class EntityExistsException(EdsExceptionBase):
    def __init__(self, entity_name, entity_type):
        detailed_message = f"{entity_type} {entity_name} already exists."
        EdsExceptionBase.__init__(self, detailed_message)


class UnexpectedIOException(EdsExceptionBase):
    def __init__(self, operation_desc: str, e: Exception):
        detailed_message = (
            f"This simple IO operation {operation_desc} should not cause exception: {e}"
        )
        EdsExceptionBase.__init__(self, detailed_message)


class UnexpectedCaseException(EdsExceptionBase):
    def __init__(self, unexpecected_case: str):
        detailed_message = f"{unexpecected_case}, which should not happen."
        EdsExceptionBase.__init__(self, detailed_message)


class UnrecoverableOperationException(EdsExceptionBase):
    def __init__(self, operation_desc: str, error: str):
        detailed_message = f"Unrecoverable operation {operation_desc} failed: {error}"
        EdsExceptionBase.__init__(self, detailed_message)


class EmptySearchResultException(EdsExceptionBase):
    def __init__(self, search_query: str):
        detailed_message = f"Search query {search_query} returned 0 results."
        EdsExceptionBase.__init__(self, detailed_message)


class UnexpectedNullValueException(EdsExceptionBase):
    def __init__(self, operation_desc: str, entity: str):
        detailed_message = (
            f"When executing {operation_desc}, {entity} should not be null."
        )
        EdsExceptionBase.__init__(self, detailed_message)


class CaseNotSupportedException(EdsExceptionBase):
    def __init__(self, operation: str, case: str):
        detailed_message = f"The {case} case is not supported for {operation}."
        EdsExceptionBase.__init__(self, detailed_message)


class FileNotExistsException(EdsExceptionBase):
    def __init__(self, file_path):
        detailed_message = f"File {file_path} does not exist."
        EdsExceptionBase.__init__(self, detailed_message)


class PathNotExistsException(EdsExceptionBase):
    def __init__(self, file_path):
        detailed_message = f"Path {file_path} does not exist."
        EdsExceptionBase.__init__(self, detailed_message)


class PathTargetExistsException(EdsExceptionBase):
    def __init__(self, path):
        detailed_message = f"Target path {path} already exist."
        EdsExceptionBase.__init__(self, detailed_message)


class CopyFileException(EdsExceptionBase):
    def __init__(self, error_msg):
        detailed_message = f"Copying file failed: {error_msg}"
        EdsExceptionBase.__init__(self, detailed_message)


class HTTPRequestException(EdsExceptionBase):
    def __init__(self, method, url, params=None, payload=None, msg=None):
        __basic_message = "RequestMethod={} url={} failure({}).".format(
            method, url, msg
        )
        detailed_message = __basic_message
        if params:
            detailed_message = "{}(Request Params={})".format(__basic_message, params)
        if payload:
            detailed_message = "{}(Request Body={})".format(__basic_message, payload)
        if params and payload:
            detailed_message = "{}(Request Params={},Body={})".format(
                __basic_message, params, payload
            )
        EdsExceptionBase.__init__(self, detailed_message)


class LoadYamlException(EdsExceptionBase):
    def __init__(self, name: str):
        detailed_message = f"Failed to load YAML file:{name}"
        EdsExceptionBase.__init__(self, detailed_message)


class YAMLFileContentException(EdsExceptionBase):
    def __init__(self, name: str):
        detailed_message = f"Failed to load YAML file content:{name}"
        EdsExceptionBase.__init__(self, detailed_message)


class JSONSchemaError(EdsExceptionBase):
    def __init__(self, err_msg: str):
        detailed_message = f"JSONSchemaError:{err_msg}"
        EdsExceptionBase.__init__(self, detailed_message)


class LLMInferenceResultException(EdsExceptionBase):
    def __init__(self, error_msg: str):
        detailed_message = f"Unexpected LLM Inference Result: {error_msg}"
        EdsExceptionBase.__init__(self, detailed_message)
