from abc import ABC
from unittest import mock

import pytest

from leettools.common import exceptions
from leettools.common.utils.factory_util import create_object


class BaseClass(ABC):
    pass


class ValidSubclass(BaseClass):
    def __init__(self, config_param):
        self.config_param = config_param


class AnotherValidSubclass(BaseClass):
    def __init__(self, config_param):
        self.config_param = config_param


def test_factory_util_invalid_base_class():
    with pytest.raises(exceptions.InvalidValueException):
        create_object("some_module", str, "config")


@mock.patch("leettools.common.utils.factory_util.importlib.import_module")
def test_factory_util_module_not_found(mock_import_module):
    mock_import_module.side_effect = ModuleNotFoundError
    with pytest.raises(exceptions.EntityNotFoundException):
        create_object("non_existent_module", BaseClass, "config")


@mock.patch("leettools.common.utils.factory_util.importlib.import_module")
def test_factory_util_no_subclasses_found(mock_import_module):
    mock_import_module.return_value = mock.Mock()
    with pytest.raises(exceptions.UnexpectedCaseException):
        create_object("some_module", BaseClass, "config")


@mock.patch("leettools.common.utils.factory_util.importlib.import_module")
def test_factory_util_multiple_subclasses_found(mock_import_module):
    mock_import_module.return_value = mock.Mock()
    mock_import_module.return_value.ValidSubclass = ValidSubclass
    mock_import_module.return_value.AnotherValidSubclass = AnotherValidSubclass
    with pytest.raises(exceptions.UnexpectedCaseException):
        create_object("some_module", BaseClass, "config")


@mock.patch("leettools.common.utils.factory_util.importlib.import_module")
def test_factory_util_valid_subclass(mock_import_module):
    mock_import_module.return_value = mock.Mock()
    mock_import_module.return_value.ValidSubclass = ValidSubclass
    instance = create_object("some_module", BaseClass, "config")
    assert isinstance(instance, ValidSubclass)
    assert instance.config_param == "config"
