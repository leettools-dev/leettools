from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar, Dict, List, Optional, Set, Tuple, Type

from pydantic import BaseModel, ConfigDict, create_model

from leettools.common import exceptions
from leettools.common.logging.event_logger import EventLogger
from leettools.common.utils import config_utils, json_utils, lang_utils, time_utils
from leettools.common.utils.template_eval import render_template
from leettools.core.consts import flow_option
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.chat_query_result import ChatQueryResultCreate
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.eds.extract.extract_store import (
    EXTRACT_DB_METADATA_FIELD,
    EXTRACT_DB_SOURCE_FIELD,
    EXTRACT_DB_TIMESTAMP_FIELD,
    create_extract_store,
)
from leettools.eds.rag.search.filter import BaseCondition
from leettools.eds.str_embedder.dense_embedder import create_dense_embedder_for_kb
from leettools.eds.str_embedder.utils.cluster import cluster_strings
from leettools.flow import flow_option_items, iterators
from leettools.flow.exec_info import ExecInfo
from leettools.flow.flow import AbstractFlow
from leettools.flow.flow_component import FlowComponent
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.flow.flow_type import FlowType
from leettools.flow.utils import flow_utils


# Need to set the model_config for each model class
# Otherwise OpenAI API call will fail with error message:
# code: 400 - {'error': {'message': "Invalid schema for response_format 'xxx':
# In context=(), 'additionalProperties' is required to be supplied and to be false",
# 'type': 'invalid_request_error', 'param': 'response_format', 'code': None}}
class NewsItem(BaseModel):
    title: str
    description: str
    categories: List[str]
    keywords: List[str]
    date: str

    model_config = ConfigDict(extra="forbid")


class CombinedNewsItems(BaseModel):
    title: str
    description: str
    date: str
    categories: List[str]
    keywords: List[str]
    source_urls: List[str]

    model_config = ConfigDict(extra="forbid")


@dataclass
class _NewsParams:
    news_source_min: int
    updated_time_threshold: datetime
    word_count: int
    article_style: str
    language_instruction: str
    old_news_instruction: str
    include_old_news: bool


class FlowNews(AbstractFlow):
    """
    This flow will find the news items from updated data in the KB and summarize them.
    """

    FLOW_TYPE: ClassVar[str] = FlowType.NEWS.value
    ARTICLE_TYPE: ClassVar[str] = ArticleType.RESEARCH.value
    COMPONENT_NAME: ClassVar[str] = FlowType.NEWS.value

    @classmethod
    def short_description(cls) -> str:
        return "Generating a list of news items from the KB."

    @classmethod
    def full_description(cls) -> str:
        return """
This flow generates a list of news items from the updated items in the KB: 
1. check the KB for recently updated documents and find news items in them.
2. combine all the similar items into one.
3. remove items that have been reported before.
4. rank the items by the number of sources.
5. generate a list of news items with references.
"""

    default_news_instructions: ClassVar[
        str
    ] = """
Please find the news items in the context about {{ query }} and return
- The title of the news item
- The detailed description of the news in the style of {{ article_style }}, up to {{ word_count }} words
- The categories of the news
- The keywords of the news
- The date of the news item
"""

    @classmethod
    def depends_on(cls) -> List[Type["FlowComponent"]]:
        return [iterators.ExtractKB]

    @classmethod
    def direct_flow_option_items(cls) -> List[FlowOptionItem]:
        foi_news_source_min = FlowOptionItem(
            name=flow_option.FLOW_OPTION_NEWS_SOURCE_MIN,
            display_name="News item source count threshold",
            description=(
                "Number of sources a news item has to have to be included in the result."
                "Default is 2. Depends on the nature of the knowledge base."
            ),
            default_value="2",
            value_type="int",
            explicit=False,
            required=False,
        )

        foi_news_include_old = FlowOptionItem(
            name=flow_option.FLOW_OPTION_NEWS_INCLUDE_OLD,
            display_name="Include previously reported news items",
            description=(
                "Include all news items in the result, even if it has been reported before."
                "Default is False."
            ),
            default_value="False",
            value_type="bool",
            explicit=False,
            required=False,
        )

        return AbstractFlow.direct_flow_option_items() + [
            flow_option_items.FOI_DAYS_LIMIT(),
            flow_option_items.FOI_OUTPUT_LANGUAGE(),
            flow_option_items.FOI_WORD_COUNT(),
            flow_option_items.FOI_ARTICLE_STYLE(),
            foi_news_source_min,
            foi_news_include_old,
        ]

    def _get_news_params(self, exec_info: ExecInfo) -> _NewsParams:
        flow_options = exec_info.flow_options
        display_logger = exec_info.display_logger

        days_limit = config_utils.get_int_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_DAYS_LIMIT,
            default_value=0,
            display_logger=display_logger,
        )

        if days_limit < 0:
            display_logger.warning(
                f"Days limit is set to {days_limit}, which is negative."
                f"Setting it to default value 0."
            )
            days_limit = 0

        if days_limit != 0:
            cur_date = time_utils.current_datetime().date()
            cur_date_start = time_utils.parse_date(f"{cur_date}")
            updated_time_threshold = cur_date_start - timedelta(days=days_limit)
            display_logger.info(
                f"Setting the updated_time_threshold to {updated_time_threshold}."
            )
        else:
            updated_time_threshold = None

        output_language = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_OUTPUT_LANGUAGE,
            default_value=None,
            display_logger=display_logger,
        )
        if output_language is not None:
            output_language = lang_utils.normalize_lang_name(output_language)
            language_instruction = f"Please generate the output in {output_language}."
        else:
            language_instruction = ""

        word_count = config_utils.get_int_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_WORD_COUNT,
            default_value=200,
            display_logger=display_logger,
        )

        article_style = config_utils.get_str_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_ARTICLE_STYLE,
            default_value="news",
            display_logger=display_logger,
        )

        news_source_min = config_utils.get_int_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_NEWS_SOURCE_MIN,
            default_value=1,
            display_logger=display_logger,
        )

        include_old_news = config_utils.get_bool_option_value(
            options=flow_options,
            option_name=flow_option.FLOW_OPTION_NEWS_INCLUDE_OLD,
            default_value=False,
            display_logger=display_logger,
        )

        news_params = _NewsParams(
            news_source_min=news_source_min,
            updated_time_threshold=updated_time_threshold,
            word_count=word_count,
            article_style=article_style,
            language_instruction=language_instruction,
            old_news_instruction="",
            include_old_news=include_old_news,
        )
        return news_params

    def _llm_dedupe(
        self, exec_info: ExecInfo, news_params: _NewsParams, news_results_md: str
    ) -> List[CombinedNewsItems]:

        display_logger = exec_info.display_logger
        query = exec_info.query
        word_count = news_params.word_count
        language_instruction = news_params.language_instruction
        old_news_instruction = news_params.old_news_instruction

        item_type = "news item"
        system_prompt_template = "You are an expert of combine and dedupe news items."
        user_prompt_template = f"""
Given a list of {item_type}s in a table where the columns are
- The title of the {item_type}
- The detailed description
- The categories
- The keywords
- The publishing date
- The URL of the source

Please find only the items about {{{{ query }}}} and combine {item_type}s about the same
topic according to their title and descriptions into one {item_type}, limit the length
of the combined title to 30 words, description to {{{{ word_count }}}} words, and combine
their keywords and categories. List for the combined {item_type}, and return the combine
{item_type}s as the schema provided.

{{{{ language_instruction}}}}

{{{{ old_news_instruction }}}}

Here are the news items to combine, dedupe, remove, and rank by the number of sources:

{{{{ results }}}}
"""
        # we added the old_news_instruction to the user prompt
        # but OpenAI API does not follow the instruction very well
        # the news item with the same title is not removed

        target_model_name = "CombinedNewsItems"
        model_class = CombinedNewsItems

        new_class_name = f"{target_model_name}_list"
        response_pydantic_model = create_model(
            new_class_name,
            items=(List[model_class], ...),
        )

        api_caller = exec_info.get_inference_caller()

        user_prompt = render_template(
            user_prompt_template,
            {
                "query": query,
                "results": news_results_md,
                "word_count": word_count,
                "language_instruction": language_instruction,
                "old_news_instruction": old_news_instruction,
            },
        )

        display_logger.info(f"user_prompt: {user_prompt}")

        response_str, completion = api_caller.run_inference_call(
            system_prompt=system_prompt_template,
            user_prompt=user_prompt,
            need_json=True,
            call_target="dedup_and_combine",
            response_pydantic_model=response_pydantic_model,
        )

        display_logger.debug(f"response_str: {response_str}")
        message = completion.choices[0].message
        if message.refusal:
            raise exceptions.LLMInferenceResultException(
                f"Refused to extract information from the document: {message.refusal}."
            )

        if hasattr(message, "parsed"):
            extract_result = message.parsed
            deduped_news_items: List[CombinedNewsItems] = extract_result.items
        else:
            response_str = json_utils.ensure_json_item_list(response_str)
            reponse_items_obj = response_pydantic_model.model_validate_json(
                response_str
            )
            deduped_news_items = reponse_items_obj.items
        return deduped_news_items

    def _clustering_dedupe(
        self,
        exec_info: ExecInfo,
        news_params: _NewsParams,
        all_objs_dict: Dict[str, List[NewsItem]],
    ) -> List[CombinedNewsItems]:
        # cluster the news items
        display_logger = exec_info.display_logger
        org = exec_info.org
        kb = exec_info.kb
        user = exec_info.user
        news_source_min = news_params.news_source_min

        dense_embedder = create_dense_embedder_for_kb(
            org=org,
            kb=kb,
            user=user,
            context=self.context,
        )

        # news_items: the key is the title + description of the news item
        # the value is the url and the news item
        news_items: Dict[str, Tuple[str, NewsItem]] = {}
        for url, item_list in all_objs_dict.items():
            for item in item_list:
                news_items[f"{item.title} {item.description}"] = (url, item)

        # news_clusters: the key is the cluster id
        # the value is the list of title + description of the news items in the cluster
        news_clusters: Dict[int, List[str]] = cluster_strings(
            strings=list(news_items.keys()),
            embedder=dense_embedder,
            eps=0.25,
            min_samples=1,
        )

        clustered_news: List[CombinedNewsItems] = []
        for cluster_id, cluster in news_clusters.items():
            if cluster_id == -1:
                display_logger.info(f"Ignore outlier cluster with id -1: {cluster}.")
                continue

            if len(cluster) < news_source_min:
                display_logger.info(
                    f"Ignore cluster with size less than source count threshold "
                    f"{news_source_min} [{cluster_id} : {len(cluster)}]: {cluster}"
                )
                continue

            display_logger.info(
                f"Adding cluster with item count [{cluster_id} : {len(cluster)}]: {cluster}"
            )

            source_urls: set[str] = set()
            news_date: datetime = None
            title: str = ""
            description: str = ""
            categories: Set[str] = set()
            keywords: Set[str] = set()

            for news_str in cluster:
                url, news_item = news_items[news_str]
                source_urls.add(url)
                if news_date is None:
                    news_date = time_utils.parse_date(news_item.date)
                else:
                    item_date = time_utils.parse_date(news_item.date)
                    if item_date is not None:
                        news_date = max(news_date, item_date)
                if len(title) < len(news_item.title):
                    title = news_item.title
                if len(description) < len(news_item.description):
                    description = news_item.description
                categories.update(news_item.categories)
                keywords.update(news_item.keywords)

            if news_date is None:
                display_logger.debug(f"Ignore cluster without news date: {cluster}")
                continue

            # we will just use the title and description of the first item in the cluster
            combined_news_item = CombinedNewsItems(
                title=title,
                description=description,
                date=str(news_date.date()),
                categories=list(categories),
                keywords=list(keywords),
                source_urls=list(source_urls),
            )
            clustered_news.append(combined_news_item)
        deduped_news_items = clustered_news
        return deduped_news_items

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

        news_params = self._get_news_params(exec_info)

        # the flow starts here
        extract_instructions = render_template(
            self.default_news_instructions,
            {
                "query": query,
                "word_count": news_params.word_count,
                "article_style": news_params.article_style,
            },
        )

        def document_filter(_: ExecInfo, document: Document) -> bool:
            document_update = document.updated_at
            if (
                news_params.updated_time_threshold is not None
                and document_update < news_params.updated_time_threshold
            ):
                display_logger.debug(
                    f"Document {document.original_uri} has updated_time "
                    f"{document_update} before {news_params.updated_time_threshold}. Skipped."
                )
                return False
            return True

        # the key is the document.original_uri and the value is the list of extracted objects
        new_objs_dict, existing_objs_dict = iterators.ExtractKB.run(
            exec_info=exec_info,
            extraction_instructions=extract_instructions,
            target_model_name="NewsItem",
            model_class=NewsItem,
            document_filter=document_filter,
        )

        # combine the new and existing objects
        all_objs_dict = {**new_objs_dict, **existing_objs_dict}

        # generate the markdown tables with the news
        target_list = flow_utils.flatten_results(all_objs_dict)
        news_results = flow_utils.to_markdown_table(
            instances=target_list,
            skip_fields=[EXTRACT_DB_METADATA_FIELD, EXTRACT_DB_TIMESTAMP_FIELD],
            output_fields=None,
            url_compact_fields=[],
        )
        display_logger.info(f"Extracted raw news item results: {news_results}")

        # find the existing combined news items
        target_model_name = "CombinedNewsItems"
        model_class = CombinedNewsItems
        combined_news_store = create_extract_store(
            context=self.context,
            org=org,
            kb=kb,
            target_model_name=target_model_name,
            target_model_class=model_class,
        )

        if news_params.updated_time_threshold is not None:
            filter = BaseCondition(
                field=EXTRACT_DB_TIMESTAMP_FIELD,
                operator="<",
                value=news_params.updated_time_threshold.timestamp() * 1000,
            )
        else:
            filter = None

        if news_params.include_old_news:
            display_logger.info("Including all news items in the result.")
            news_params.old_news_instruction = ""
        else:
            records = combined_news_store.get_records(filter)
            if records:
                display_logger.info(
                    f"Found {len(records)} existing combined news items. "
                )
                # TODO: limit the number of records to include in the message
                old_news = flow_utils.to_markdown_table(
                    instances=records,
                    skip_fields=[
                        EXTRACT_DB_METADATA_FIELD,
                        EXTRACT_DB_SOURCE_FIELD,
                        EXTRACT_DB_TIMESTAMP_FIELD,
                    ],
                    output_fields=["title"],
                    url_compact_fields=[],
                )

                news_params.old_news_instruction = (
                    f"Please remove news items about the following or similar topics:\n"
                    f"{old_news}\n"
                )
            else:
                display_logger.info("No existing combined news items found.")
                news_params.old_news_instruction = ""

        # dedupe the news items
        use_clustering_dedup = True
        if use_clustering_dedup:
            deduped_news_items = self._clustering_dedupe(
                exec_info=exec_info,
                news_params=news_params,
                all_objs_dict=all_objs_dict,
            )
        else:
            deduped_news_items = self._llm_dedupe(
                exec_info=exec_info,
                news_params=news_params,
                news_results_md=news_results,
            )

        deduped_news_results = flow_utils.to_markdown_table(
            instances=deduped_news_items,
            skip_fields=[EXTRACT_DB_METADATA_FIELD, EXTRACT_DB_TIMESTAMP_FIELD],
            output_fields=None,
            url_compact_fields=[],
        )

        display_logger.info(f"deduped_news_results:\n{deduped_news_results}")

        final_news_items = []
        for item in deduped_news_items:
            if item.source_urls is None or len(item.source_urls) == 0:
                display_logger.warning(
                    f"CombinedNewsItem has no source_urls: {item.model_dump()}"
                )
                continue
            if len(item.source_urls) < news_params.news_source_min:
                display_logger.info(
                    f"Ignoring news item with sources less than {news_params.news_source_min}: {item.source_urls}"
                )
                continue

            parse_item_date = time_utils.parse_date(item.date)
            if parse_item_date is None:
                display_logger.warning(f"CombinedNewsItem has no date: {item}")
                final_news_items.append(item)
                continue

            if news_params.updated_time_threshold is not None:
                if parse_item_date < news_params.updated_time_threshold:
                    display_logger.info(
                        f"Ignoring news item with date {parse_item_date} before {news_params.updated_time_threshold}: {item}"
                    )
                    continue
                else:
                    display_logger.debug(
                        f"Adding item with date {parse_item_date} after {news_params.updated_time_threshold}: {item}"
                    )
            final_news_items.append(item)

        display_logger.info(
            f"Saving items with more than one references: {len(final_news_items)})"
        )
        combined_news_store.save_records(final_news_items, metadata={})

        display_logger.info(f"Generating results for the final answer.")

        final_news_results = flow_utils.to_markdown_table(
            instances=final_news_items,
            skip_fields=[EXTRACT_DB_METADATA_FIELD, EXTRACT_DB_TIMESTAMP_FIELD],
            output_fields=None,
            url_compact_fields=[],
        )
        return flow_utils.create_chat_result_with_table_msg(
            msg=final_news_results,
            header=list(CombinedNewsItems.model_fields.keys()),
            rows=[item.model_dump() for item in deduped_news_items],
            exec_info=exec_info,
            query_metadata=None,
        )
