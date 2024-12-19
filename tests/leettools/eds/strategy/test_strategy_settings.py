from leettools.core.strategy.schemas.strategy_display_settings import (
    get_strategy_display_sections,
)
from leettools.core.strategy.schemas.strategy_section_name import StrategySectionName


def test_strateg_settings():
    list_of_sections = get_strategy_display_sections()
    assert len(list_of_sections) == 7

    assert list_of_sections[0].section_name == StrategySectionName.INTENTION
    assert list_of_sections[1].section_name == StrategySectionName.REWRITE
    assert list_of_sections[2].section_name == StrategySectionName.SEARCH
    assert list_of_sections[3].section_name == StrategySectionName.RERANK
    assert list_of_sections[4].section_name == StrategySectionName.CONTEXT
    assert list_of_sections[5].section_name == StrategySectionName.INFERENCE
    assert list_of_sections[6].section_name == StrategySectionName.GENERAL

    for x in list_of_sections:
        assert x.section_display_name is not None
        assert x.section_description is not None
        assert x.default_strategy_name is not None
