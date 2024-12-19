import importlib
import importlib.util
import os
from pathlib import Path
from typing import Dict, Type

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.singleton_meta import SingletonMeta
from leettools.common.utils import module_utils
from leettools.flow.flow import AbstractFlow
from leettools.settings import SystemSettings

_script_dir = os.path.dirname(os.path.abspath(__file__))


class FlowManager(metaclass=SingletonMeta):

    def __init__(self, settings: SystemSettings):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            self.settings = settings
            # the key is the flow_type and the value is the flow
            self.flow_classes: Dict[str, Type[AbstractFlow]] = {}
            self._scan_all_flows()

    def get_default_flow_type(self) -> str:
        return self.settings.DEFAULT_FLOW_TYPE

    def get_flow_by_type(self, flow_type: str) -> AbstractFlow:
        if flow_type not in self.flow_classes:
            raise exceptions.EntityNotFoundException(
                entity_name=flow_type, entity_type="Flow"
            )
        flow_class = self.flow_classes[flow_type]
        from leettools.context_manager import ContextManager

        return flow_class(context=ContextManager().get_context())

    def _scan_all_flows(self):

        # the extension path is under the {project_root}/extensions
        # the current script is under the {project_root}/src/leettools/flow

        base_classes = self._scan_dir_for_flows(f"{_script_dir}/flows")
        self.flow_classes.update(base_classes)

        extension_flow_path = f"{self.settings.EXTENSION_PATH}/flow/flows"

        if Path(extension_flow_path).exists():
            extension_classes = self._scan_dir_for_flows(extension_flow_path)
            self.flow_classes.update(extension_classes)

    def _scan_dir_for_flows(self, dir_str: str) -> Dict[str, Type[AbstractFlow]]:
        flow_classes = {}
        dir_path = Path(dir_str).resolve()

        package = module_utils.generate_package_name(
            base_path=self.settings.CODE_ROOT_PATH, package_path=dir_path
        )

        for entry in dir_path.iterdir():
            if not entry.is_dir():
                continue
            subdir_name = entry.name
            module_name = f"{package}.{subdir_name}.flow_{subdir_name}"
            flow_file = f"{dir_path}/{subdir_name}/flow_{subdir_name}.py"
            if not os.path.exists(flow_file):
                continue
            try:
                spec = importlib.util.spec_from_file_location(module_name, flow_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                found_flow_classes = []
                for attr in module.__dict__.values():
                    if isinstance(attr, type) and issubclass(attr, AbstractFlow):
                        if attr is not AbstractFlow:
                            found_flow_classes.append(attr)
                if len(found_flow_classes) != 1:
                    logger().warning(
                        f"Executor module {module_name} contains {len(found_flow_classes)} "
                        f"flow classes, should contain exactly one."
                    )
                    continue
                flow_classes[subdir_name] = found_flow_classes[0]
            except Exception as e:
                # to avoid breaking the whole system, we print the error and continue
                logger().error(f"Error loading flow module {module_name}: {e}")
                raise e  # tmp solution, remove after the flows are fixed
        return flow_classes


if __name__ == "__main__":

    from leettools.context_manager import ContextManager

    context = ContextManager().get_context()
    flow_manager = FlowManager(context.settings)
    for flow_type, flow_class in flow_manager.flow_classes.items():
        print(f"{flow_type:<15}\t{flow_class}")
