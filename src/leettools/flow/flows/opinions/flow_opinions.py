from typing import ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, create_model

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils, json_utils, url_utils
from leettools.common.utils.dynamic_exec_util import execute_pydantic_snippet
from leettools.common.utils.template_eval import render_template
from leettools.core.consts.article_type import ArticleType
from leettools.core.consts.display_type import DisplayType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.api_caller.api_caller_base import APICallerBase
from leettools.eds.extract.extract_store import (
    EXTRACT_DB_SOURCE_FIELD,
    EXTRACT_DB_TIMESTAMP_FIELD,
)
from leettools.flow import flow_option_items, iterators, steps
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.flow.schemas.instruction_vars import InstructionVars
from leettools.flow.utils import flow_utils
from leettools.flow.utils.instruction_utils import get_instruction_json


# Need to set the model_config for each model class
# Otherwise OpenAI API call will fail with error message:
# code: 400 - {'error': {'message': "Invalid schema for response_format 'xxx':
# In context=(), 'additionalProperties' is required to be supplied and to be false",
# 'type': 'invalid_request_error', 'param': 'response_format', 'code': None}}
class Opinions(BaseModel):
    description: str
    keywords: List[str]
    sentiment: str

    model_config = ConfigDict(extra="forbid")


class CombinedOpinions(BaseModel):
    description: str
    keywords: List[str]
    sentiment: str
    source_urls: List[str]

    model_config = ConfigDict(extra="forbid")


class PostprocessCombinedOpinions(CombinedOpinions):
    source_domains: Dict[str, int]

    model_config = ConfigDict(extra="forbid")


class Facts(BaseModel):
    description: str
    keywords: List[str]

    model_config = ConfigDict(extra="forbid")


class CombinedFacts(BaseModel):
    description: str
    keywords: List[str]
    source_urls: List[str]

    model_config = ConfigDict(extra="forbid")


class PostprocessCombinedFacts(CombinedFacts):
    source_domains: Dict[str, int]

    model_config = ConfigDict(extra="forbid")


class KeyWordCount(BaseModel):
    key_word: str
    positive: int
    negative: int
    neutral: int
    fact: int

    model_config = ConfigDict(extra="forbid")


def extract_items_from_docsource(
    exec_info: ExecInfo,
    docsource: DocSource,
    instructions: str,
    type_dict: Dict[str, type],
    target_model_name: str,
) -> List[type]:
    model_class = type_dict[target_model_name]

    # the key is the document.original_uri and the value is the list of extracted objects
    new_objs_dict, existing_objs_dict = iterators.ExtractKB.run(
        exec_info=exec_info,
        extraction_instructions=instructions,
        target_model_name=target_model_name,
        model_class=model_class,
        docsource=docsource,
    )

    # combine the new and existing objects
    all_objs_dict = {**new_objs_dict, **existing_objs_dict}
    target_list = flow_utils.flatten_results(all_objs_dict)
    return target_list


def dedupe_items(
    api_caller: APICallerBase,
    input_items: List[type],
    skip_fields: List[str],
    type_dict: Dict[str, type],
    target_model_name: str,
    dedupe_step: Dict[str, str],
    display_logger: EventLogger,
) -> List[type]:

    input_md_table = flow_utils.to_markdown_table(input_items, skip_fields=skip_fields)

    model_class = type_dict[target_model_name]
    model_class_name = target_model_name
    new_class_name = f"{model_class_name}_list"
    response_pydantic_model = create_model(
        new_class_name,
        items=(List[model_class], ...),
    )

    response_str, completion = api_caller.run_inference_call(
        system_prompt=dedupe_step["system_prompt_template"],
        user_prompt=render_template(
            dedupe_step["user_prompt_template"], {"results": input_md_table}
        ),
        need_json=True,
        call_target="dedup_and_combine",
        response_pydantic_model=response_pydantic_model,
    )

    display_logger.debug(f"response_str: {response_str}")
    message = completion.choices[0].message

    message = completion.choices[0].message
    if hasattr(message, "refusal"):
        if message.refusal:
            raise exceptions.LLMInferenceResultException(
                f"Refused to extract information from the document: {message.refusal}."
            )

    if hasattr(message, "parsed"):
        display_logger.debug(f"Returning list of objects using message.parsed.")
        extract_result = message.parsed
        return extract_result.items
    else:
        display_logger.debug(f"Returning list of objects using model_validate_json.")
        response_str = json_utils.ensure_json_item_list(response_str)
        try:
            items = response_pydantic_model.model_validate_json(response_str)
            return items.items
        except Exception as e:
            display_logger.error(
                f"ModelValidating {target_model_name} failed: {response_str}"
            )
            raise e


class FlowOpinions(AbstractFlow):
    """
    This flow will find the opinions about the topic on the internet.
    """

    FLOW_TYPE: ClassVar[str] = FlowType.OPINIONS.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.RESEARCH.value
    COMPONENT_NAME: ClassVar[str] = FlowType.OPINIONS.value

    @classmethod
    def short_description(cls) -> str:
        return "Generating a list of facts and opinions about the topic."

    @classmethod
    def full_description(cls) -> str:
        return """
Enter a topic for analysis,
- query the web (default) or local KB to find top web pages for the topic;
- crawl and scrape the top web pages to the local KB;
- for each scraped page, scan the page for sentiments and facts and save them to a DB;
- dedupe and combine the sentiments and facts;
- generate a final report with the combined sentiments and facts;
"""

    FLOW_OPTION_OPINIONS_INSTRUCTION: ClassVar[str] = "opinions_instruction"

    default_opinions_instructions: ClassVar[
        str
    ] = """
Please find the opinions about {{ query }} in the context and return
- The keywords about the opinion
- The description of the opinion
- the sentiment of the opinion (positive, negative, neutral)
"""

    default_facts_instructions: ClassVar[
        str
    ] = """
Please list interesting facts about {{ query }} in the context and return
- The keywords about the fact
- The description of the fact
"""

    @classmethod
    def get_instruction_vars(cls) -> List[InstructionVars]:
        return [
            InstructionVars(
                var_name="opinions_instructions",
                var_type="str",
                required=False,
                var_description="The prompt for the opinion extraction.",
                default_value=None,
            ),
            InstructionVars(
                var_name="fact_instructions",
                var_type="str",
                required=False,
                var_description="The prompt for the fact extraction.",
                default_value=None,
            ),
        ]

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [steps.StepSearchToDocsource]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        example_value = f"""
opinions_instructions = \"\"\"
{cls.default_opinions_instructions}
\"\"\"

facts_instructions = \"\"\"
{cls.default_facts_instructions}
\"\"\"
"""
        opinion_instruction = flow_option_items.FlowOptionItem(
            name=cls.FLOW_OPTION_OPINIONS_INSTRUCTION,
            display_name="Opinions Extraction Instruction",
            description=(
                "The backend will execute the Python code to get required settings and variables."
            ),
            default_value=None,
            example_value=example_value,
            explicit=False,
            multiline=True,
            value_type="str",
            code="python",
            code_variables=get_instruction_json(cls.get_instruction_vars()),
        )
        return AbstractFlow.direct_flow_option_items() + [
            opinion_instruction,
            flow_option_items.FOI_RETRIEVER(),
            flow_option_items.FOI_TARGET_SITE(),
            flow_option_items.FOI_SEARCH_LANGUAGE(),
            flow_option_items.FOI_SEARCH_MAX_RESULTS(),
            flow_option_items.FOI_DAYS_LIMIT(),
            flow_option_items.FOI_SEARCH_EXCLUDED_SITES(),
            flow_option_items.FOI_OUTPUT_LANGUAGE(),
            flow_option_items.FOI_SUMMARY_MODEL(),
            flow_option_items.FOI_WRITING_MODEL(),
        ]

    def execute_query(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
    ) -> ChatQueryResultCreate:

        # common setup
        exec_info = ExecInfo(
            context=self.context,
            org=org,
            kb=kb,
            user=user,
            target_chat_query_item=chat_query_item,
            display_logger=display_logger,
        )
        display_logger = exec_info.display_logger
        query = exec_info.query
        flow_options = exec_info.flow_options

        # read the instructions
        instruction_code = config_utils.get_str_option_value(
            options=flow_options,
            option_name=self.FLOW_OPTION_OPINIONS_INSTRUCTION,
            default_value="",
            display_logger=display_logger,
        )

        if instruction_code is not None and instruction_code.strip() != "":
            var_dict, type_dict = execute_pydantic_snippet(code=instruction_code)
            opinions_instructions = var_dict.get(
                "opinions_instructions",
                render_template(
                    self.default_opinions_instructions,
                    {"query": query},
                ),
            )
            facts_instructions = var_dict.get(
                "fact_instructions",
                render_template(self.default_facts_instructions, {"query": query}),
            )
        else:
            opinions_instructions = render_template(
                self.default_opinions_instructions,
                {"query": query},
            )
            facts_instructions = render_template(
                self.default_facts_instructions, {"query": query}
            )

        # the agent flow starts here
        docsource = steps.StepSearchToDocsource.run_step(
            exec_info=exec_info, search_keywords=query
        )

        # Get the opinions
        opinion_list: List[Opinions] = extract_items_from_docsource(
            exec_info=exec_info,
            docsource=docsource,
            instructions=opinions_instructions,
            type_dict={"Opinions": Opinions},
            target_model_name="Opinions",
        )

        # separate them into positive, negative and neutral
        positive_sentiment = [
            "positive",
            "good",
            "great",
            "excellent",
        ]
        negative_sentiment = [
            "negative",
            "bad",
            "poor",
            "terrible",
        ]
        neutral_sentiment = ["neutral", "mixed"]

        sep_opinion_lists: Dict[str, List[Opinions]] = {
            "positive": [],
            "negative": [],
            "neutral": [],
        }

        sep_opinion_sections: Dict[str, ArticleSection] = {}
        sep_deduped_opinion_sections: Dict[str, ArticleSection] = {}
        # the first key is the key word, the second key is the sentiment, the value is the count
        key_word_count: Dict[str, Dict[str, int]] = {}

        for target in opinion_list:
            if target.sentiment.lower() in positive_sentiment:
                target.sentiment = "Positive"
                sep_opinion_lists["positive"].append(target)
                for keyword in target.keywords:
                    if keyword not in key_word_count:
                        key_word_count[keyword] = {
                            "positive": 0,
                            "negative": 0,
                            "neutral": 0,
                            "fact": 0,
                        }
                    key_word_count[keyword]["positive"] += 1
            elif target.sentiment.lower() in negative_sentiment:
                target.sentiment = "Negative"
                sep_opinion_lists["negative"].append(target)
                for keyword in target.keywords:
                    if keyword not in key_word_count:
                        key_word_count[keyword] = {
                            "positive": 0,
                            "negative": 0,
                            "neutral": 0,
                            "fact": 0,
                        }
                    key_word_count[keyword]["negative"] += 1
            elif target.sentiment.lower() in neutral_sentiment:
                target.sentiment = "Neutral"
                sep_opinion_lists["neutral"].append(target)
                for keyword in target.keywords:
                    if keyword not in key_word_count:
                        key_word_count[keyword] = {
                            "positive": 0,
                            "negative": 0,
                            "neutral": 0,
                            "fact": 0,
                        }
                    key_word_count[keyword]["neutral"] += 1
            else:
                display_logger.warning(f"Unknown sentiment: {target.sentiment}")

        # generate the markdown tables and result sections
        for key in sep_opinion_lists:
            opinion_results = flow_utils.to_markdown_table(
                sep_opinion_lists[key],
                skip_fields=[EXTRACT_DB_TIMESTAMP_FIELD, "sentiment"],
                output_fields=None,
                url_compact_fields=[EXTRACT_DB_SOURCE_FIELD],
            )
            section = ArticleSection(
                title=f"{key.capitalize()} Opinions",
                content=opinion_results,
                plan=ArticleSectionPlan(
                    title=f"{key.capitalize()} Opinions",
                    search_query=query,
                    user_prompt_template=opinions_instructions,
                    system_prompt_template="",
                ),
            )
            sep_opinion_sections[key] = section

        # dedupe the opinions
        item_type = "opinion"
        opinion_dedupe_step = {
            "system_prompt_template": "You are an expert of deduplicate items.",
            "user_prompt_template": f"""
Given the following {item_type}s in a table where the left most column is the description, 
the second column is the key words of the {item_type}, and the the right most column is 
the source url of the {item_type}:

{{{{ results }}}}

Please combine {item_type}s with similar descriptions and key words into one {item_type},
limit the length of the combined description to 100 words, adding all source urls in a 
list for the combined {item_type}, and return the combine {item_type}s as the schema provided.
""",
        }

        target_model_name = "CombinedOpinions"
        model_class = CombinedOpinions
        type_dict = {target_model_name: model_class}

        deduped_sep_opionion_lists: Dict[str, List[PostprocessCombinedOpinions]] = {}

        for key in sep_opinion_lists:
            deduped_sep_opionion_list: List[CombinedOpinions] = dedupe_items(
                api_caller=exec_info.get_inference_caller(),
                input_items=sep_opinion_lists[key],
                skip_fields=[EXTRACT_DB_TIMESTAMP_FIELD],
                type_dict=type_dict,
                target_model_name=target_model_name,
                dedupe_step=opinion_dedupe_step,
                display_logger=display_logger,
            )

            opinion_with_domains: List[PostprocessCombinedOpinions] = []

            for target in deduped_sep_opionion_list:
                new_target = PostprocessCombinedOpinions(
                    description=target.description,
                    keywords=target.keywords,
                    sentiment=target.sentiment,
                    source_urls=target.source_urls,
                    source_domains={},
                )

                for url in target.source_urls:
                    domains = url_utils.get_domain_from_url(url)
                    if domains not in new_target.source_domains:
                        new_target.source_domains[domains] = 1
                    else:
                        new_target.source_domains[domains] += 1
                opinion_with_domains.append(new_target)

            deduped_sep_opinion_md = flow_utils.to_markdown_table(
                opinion_with_domains, skip_fields=["source_urls", "sentiment"]
            )

            # dump the opinion_with_domain to a dictionary for user_data
            opinion_user_data = {"opinions": []}
            for target in opinion_with_domains:
                opinion_user_data["opinions"].append(target.model_dump())

            deduped_sep_opinion_section = ArticleSection(
                title=f"Deduped {key.capitalize()} Opinions",
                content=deduped_sep_opinion_md,
                plan=ArticleSectionPlan(
                    title=f"Deduped {key.capitalize()} Opinions",
                    search_query=query,
                    user_prompt_template=opinion_dedupe_step["user_prompt_template"],
                    system_prompt_template=opinion_dedupe_step[
                        "system_prompt_template"
                    ],
                ),
                user_data=opinion_user_data,
            )

            sep_deduped_opinion_sections[key] = deduped_sep_opinion_section
            deduped_sep_opionion_lists[key] = opinion_with_domains

        # Get the facts
        fact_list: List[Facts] = extract_items_from_docsource(
            exec_info=exec_info,
            docsource=docsource,
            instructions=facts_instructions,
            type_dict={"Facts": Facts},
            target_model_name="Facts",
        )

        # update keyword count
        for target in fact_list:
            for keyword in target.keywords:
                if keyword not in key_word_count:
                    key_word_count[keyword] = {
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0,
                        "fact": 0,
                    }
                key_word_count[keyword]["fact"] += 1

        fact_results = flow_utils.to_markdown_table(
            fact_list,
            skip_fields=[EXTRACT_DB_TIMESTAMP_FIELD],
            output_fields=None,
            url_compact_fields=[EXTRACT_DB_SOURCE_FIELD],
        )

        fact_section = ArticleSection(
            title="Facts",
            content=fact_results,
            plan=ArticleSectionPlan(
                title="Facts",
                search_query=query,
                user_prompt_template=facts_instructions,
                system_prompt_template="",
            ),
        )

        # Dedupe the facts
        fact_dedupe_step = {
            "system_prompt_template": "You are an expert of deduplicate items.",
            "user_prompt_template": """
Given the following facts in a table where the left most column is the description
of the fact, and the the right most column is the source url of the fact:

{{ results }}

Please combine facts with similar descriptions and key words into one fact, limit the 
length of the combined description to 100 words, adding all source urls in a list for 
the combined fact, and return the combine facts as the schema provided.
""",
        }

        target_model_name = "CombinedFacts"
        model_class = CombinedFacts
        type_dict = {target_model_name: model_class}

        deduped_fact_list: List[CombinedFacts] = dedupe_items(
            api_caller=exec_info.get_inference_caller(),
            input_items=fact_list,
            skip_fields=[EXTRACT_DB_TIMESTAMP_FIELD],
            type_dict=type_dict,
            target_model_name=target_model_name,
            dedupe_step=fact_dedupe_step,
            display_logger=display_logger,
        )

        deduped_fact_list_with_domain: List[PostprocessCombinedFacts] = []

        for target in deduped_fact_list:
            new_target = PostprocessCombinedFacts(
                description=target.description,
                keywords=target.keywords,
                source_urls=target.source_urls,
                source_domains={},
            )
            for url in target.source_urls:
                domains = url_utils.get_domain_from_url(url)
                if domains not in new_target.source_domains:
                    new_target.source_domains[domains] = 1
                else:
                    new_target.source_domains[domains] += 1

            deduped_fact_list_with_domain.append(new_target)

        deduped_items_md = flow_utils.to_markdown_table(
            deduped_fact_list_with_domain, skip_fields=["source_urls"]
        )

        fact_user_data = {"facts": []}
        for target in deduped_fact_list_with_domain:
            fact_user_data["facts"].append(target.model_dump())

        deduped_fact_section = ArticleSection(
            title="Deduped Facts",
            content=deduped_items_md,
            plan=ArticleSectionPlan(
                title="Deduped Facts",
                search_query=query,
                user_prompt_template=fact_dedupe_step["user_prompt_template"],
                system_prompt_template=fact_dedupe_step["system_prompt_template"],
            ),
            user_data=fact_user_data,
        )

        # create a summary section
        pos_count = len(sep_opinion_lists["positive"])
        if pos_count == 0:
            pos_count = 1
        neg_count = len(sep_opinion_lists["negative"])
        if neg_count == 0:
            neg_count = 1
        neu_count = len(sep_opinion_lists["neutral"])
        if neu_count == 0:
            neu_count = 1
        fact_count = len(fact_list)
        if fact_count == 0:
            fact_count = 1

        summary_data = {
            "Positive Opinion": {
                "Extracted": pos_count,
                "Deduped": len(deduped_sep_opionion_lists["positive"]),
                "Deduped / Extracted": len(deduped_sep_opionion_lists["positive"])
                / pos_count,
            },
            "Negative Opinion": {
                "Extracted": neg_count,
                "Deduped": len(deduped_sep_opionion_lists["negative"]),
                "Deduped / Extracted": len(deduped_sep_opionion_lists["negative"])
                / neg_count,
            },
            "Neutral Opinion": {
                "Extracted": neu_count,
                "Deduped": len(deduped_sep_opionion_lists["neutral"]),
                "Deduped / Extracted": len(deduped_sep_opionion_lists["neutral"])
                / neu_count,
            },
            "Facts": {
                "Extracted": fact_count,
                "Deduped": len(deduped_fact_list),
                "Deduped / Extracted": len(deduped_fact_list) / fact_count,
            },
        }

        # convert summary data to a markdown table
        summary_table_str = "| Category | Extracted | Deduped | Deduped / Extracted |\n"
        summary_table_str += "| --- | --- | --- | --- |\n"
        for key in summary_data:
            summary_table_str += (
                f"| {key} | {summary_data[key]['Extracted']} | {summary_data[key]['Deduped']} | "
                f"{summary_data[key]['Deduped / Extracted']:.2f} |\n"
            )

        opinion_summary_section = ArticleSection(
            title="Summary Count",
            content=summary_table_str,
            plan=None,
            user_data=summary_data,
        )

        # create a separate key word list section
        display_logger.debug(f"key_word_count: {key_word_count}")
        key_word_count_table: List[KeyWordCount] = []
        for key in key_word_count:
            key_word_count_table.append(
                KeyWordCount(
                    key_word=key,
                    positive=key_word_count[key]["positive"],
                    negative=key_word_count[key]["negative"],
                    neutral=key_word_count[key]["neutral"],
                    fact=key_word_count[key]["fact"],
                )
            )

        key_word_section = ArticleSection(
            title="Word Cloud",
            content=flow_utils.to_markdown_table(key_word_count_table),
            display_type=DisplayType.WORD_CLOUD,
            user_data=key_word_count,
            plan=None,
        )

        sections = [
            opinion_summary_section,
            key_word_section,
            deduped_fact_section,
            sep_deduped_opinion_sections["positive"],
            sep_deduped_opinion_sections["negative"],
            sep_deduped_opinion_sections["neutral"],
            fact_section,
            sep_opinion_sections["positive"],
            sep_opinion_sections["negative"],
            sep_opinion_sections["neutral"],
        ]

        return flow_utils.create_chat_result_with_sections(
            exec_info=exec_info,
            query=query,
            article_type=self.ARTICLE_TYPE,
            sections=sections,
            accumulated_source_items={},
        )
