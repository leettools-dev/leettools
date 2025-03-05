from typing import ClassVar, Dict, List, Type

from leettools.common import exceptions
from leettools.core.strategy.schemas.prompt import PromptBase
from leettools.flow import flow_option_items
from leettools.flow.flow_component_type import FlowComponentType
from leettools.flow.flow_option_items import FlowOptionItem


class FlowComponent:
    """
    Any program that is part of the flow and uses the flow options should inherit from
    this class. It provides the metadata for the upper level components to get the
    options and dependencies.
    """

    COMPONENT_TYPE: ClassVar[FlowComponentType] = None
    COMPONENT_NAME: ClassVar[str] = None

    @classmethod
    def short_description(cls) -> str:
        return "Default short description."

    @classmethod
    def full_description(cls) -> str:
        return "Default full description."

    @classmethod
    def used_prompt_templates(cls) -> Dict[str, PromptBase]:
        """
        Return all the prompt templates used by this component.

        The key is the purpose of the prompt template.
        The value is the prompt template object as the PromptBase class.
        """
        return {}

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return []

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        # Options that shared by all the flows
        return [
            flow_option_items.FOI_OUTPUT_LANGUAGE(),
            flow_option_items.FOI_CONTEXT_LIMIT(),
        ]

    @classmethod
    def can_depend_on_class(cls, dep_cls: Type["FlowComponent"]) -> bool:
        # currently we do not restrict the classes that can depend on each other
        return True

    @classmethod
    def get_foi_dict(cls) -> Dict[FlowComponentType, Dict[str, List[FlowOptionItem]]]:
        """
        Get all the flow option items in a dictionary format.

        The first key is the component type: step, subflow, iterator.
        The second key is the component name.
        The value is the list of the flow option items used by that component.
        """
        foi_dict: Dict[FlowComponentType, Dict[str, List[FlowOptionItem]]] = {}
        for type in FlowComponentType:
            foi_dict[type] = {}
        cls._add_foi_dict(foi_dict)
        return foi_dict

    @classmethod
    def _add_foi_dict(
        cls, full_foi_dict: Dict[FlowComponentType, Dict[str, List[FlowOptionItem]]]
    ):
        """
        Add the flow option items of this component to the full flow option items dictionary.
        """
        cur_type = cls.COMPONENT_TYPE
        if cls.COMPONENT_NAME in full_foi_dict[cur_type]:
            # the component is already added
            return

        full_foi_dict[cur_type][cls.COMPONENT_NAME] = cls.direct_flow_option_items()
        for dep_cls in cls.depends_on():
            if not cls.can_depend_on_class(dep_cls):
                raise exceptions.UnexpectedCaseException(
                    f"{cls.COMPONENT_TYPE} cannot depend on {dep_cls.COMPONENT_TYPE}"
                )
            # how to avoid infinite recursion?
            dep_cls._add_foi_dict(full_foi_dict)

    @classmethod
    def get_flow_option_items(cls) -> List[FlowOptionItem]:
        """
        Aggregate all the flow option items of all the depended components.
        """
        full_foi_dict = cls.get_foi_dict()
        foi_dict: Dict[str, FlowOptionItem] = {}

        for component_type, component_foi_dict in full_foi_dict.items():
            for component_name, foi_list in component_foi_dict.items():
                for foi in foi_list:
                    if foi.flow_components is None:
                        foi.flow_components = {}

                    foi_name = foi.name
                    if foi_name not in foi_dict:
                        foi.flow_components[component_type] = [component_name]
                        foi_dict[foi_name] = foi
                    else:
                        existing_foi = foi_dict[foi_name]
                        if component_type not in foi_dict[foi_name].flow_components:
                            existing_foi.flow_components[component_type] = [
                                component_name
                            ]
                        else:
                            existing_foi.flow_components[component_type].append(
                                component_name
                            )
                        # need to check 'required' and 'explicit' values
                        if foi.required:
                            existing_foi.required = True
                        if foi.explicit:
                            existing_foi.explicit = True
        return list(foi_dict.values())
