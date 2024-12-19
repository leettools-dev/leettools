from typing import Type

from pydantic import BaseModel

from leettools.common.temp_setup import TempSetup
from leettools.common.utils.obj_utils import TypeVar_BaseModel
from leettools.context_manager import Context
from leettools.core.consts.flow_option import FLOW_OPTION_OUTPUT_LANGUAGE
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import steps


class CompanyTest(BaseModel):
    name: str
    employees: int
    revenue: float


def test_step_extract_info():

    temp_setup = TempSetup()

    context = temp_setup.context

    org, kb, user = temp_setup.create_tmp_org_kb_user()

    user = temp_setup.create_tmp_user()

    try:
        _test_flow_step(context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_flow_step(context: Context, org: Org, kb: KnowledgeBase, user: User):

    query = "Not related"

    # TODO: basically for each pair of (instruction, target_class) we should have a test
    extraction_instructions = """
Extract all the company names, number of employees, and revenue from the content.
"""
    target_class: Type[TypeVar_BaseModel] = CompanyTest

    content = """
In the ever-evolving landscape of American business, several companies stand out due to 
their significant contributions to the economy. These industry giants not only dominate 
their respective fields but also provide employment to millions of individuals and 
generate substantial revenue, playing a critical role in the nation's financial health.
Among these, some of the most noteworthy companies include Walmart, Amazon, Apple, CVS 
Health, and UnitedHealth Group. Each of these organizations has carved a niche for 
itself through innovation, customer service, and strategic expansion.

Below is a table listing the top 5 companies in the US based on their employee numbers 
and revenue:

| Company          | Employees (approx.) | Revenue (in billion USD) |
|------------------|---------------------|--------------------------|
| Walmart          | 2,300,000           | 572                      |
| Amazon           | 1,300,000           | 469.8                    |
| Apple            | 147,000             | 365                      |
| CVS Health       | 300,000             | 292.1                    |
| UnitedHealth Group | 330,000          | 287.6                    |

These companies not only lead in their respective industries but also significantly 
influence the global market. Walmart, with its vast network of retail stores, has the 
highest number of employees, making it the largest employer in the world. Amazon, known 
for its e-commerce dominance, continues to expand into various sectors, contributing to 
its impressive revenue figures. Apple remains a leader in technology and innovation, 
constantly pushing the boundaries with its cutting-edge products. CVS Health, with 
its extensive network of pharmacies and healthcare services, plays a crucial role in 
the health sector. UnitedHealth Group stands out in the healthcare industry, providing 
comprehensive health benefits and services. Together, these companies exemplify the 
strength and diversity of the American economy.
"""

    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org.name,
        kb_name=kb.name,
        username=user.username,
        strategy_name=None,
        flow_options={
            FLOW_OPTION_OUTPUT_LANGUAGE: "CN",
        },
    )

    extract_data = steps.StepExtractInfo.run_step(
        exec_info=exec_info,
        content=content,
        extraction_instructions=extraction_instructions,
        model_class=target_class,
        model_class_name="TestCompany",
        multiple_items=True,
    )

    assert extract_data is not None
    assert isinstance(extract_data, list)
    assert len(extract_data) == 5

    for company in extract_data:
        if company.name == "Walmart":
            assert company.employees == 2300000
            assert company.revenue == 572.0
        elif company.name == "Amazon":
            assert company.employees == 1300000
            assert company.revenue == 469.8
        elif company.name == "Apple":
            assert company.employees == 147000
            assert company.revenue == 365.0
        elif company.name == "CVS Health":
            assert company.employees == 300000
            assert company.revenue == 292.1
        elif company.name == "UnitedHealth Group":
            assert company.employees == 330000
            assert company.revenue == 287.6
        else:
            assert False, f"Unexpected company name: {company.name}"
