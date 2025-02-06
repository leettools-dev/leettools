from typing import List, Optional

from fastapi import Body, Depends, HTTPException

from leettools.chat.history_manager import AbstractHistoryManager, get_history_manager
from leettools.chat.schemas.chat_history import ChatHistory
from leettools.common import exceptions
from leettools.common.exceptions import EntityNotFoundException
from leettools.core.consts.article_type import ArticleType
from leettools.core.schemas.chat_query_result import ChatAnswerItemCreate
from leettools.core.schemas.user import User
from leettools.flow import subflows
from leettools.flow.exec_info import ExecInfo
from leettools.flow.schemas.article import ArticleSection, ArticleSectionPlan
from leettools.svc.api_router_base import APIRouterBase


class ArticleRouter(APIRouterBase):
    """
    This class implements the router for artcile processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.chat_manager: AbstractHistoryManager = get_history_manager(context)
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.strategy_store = context.get_strategy_store()
        self.user_store = context.get_user_store()

        @self.get(
            "/shared_samples_by_type/{org_name}/{flow_type}",
            response_model=List[ChatHistory],
        )
        async def get_shared_samples_by_type(
            org_name: str,
            flow_type: str = None,
            list_only: Optional[bool] = False,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[ChatHistory]:
            """
            Get all shared articles from the specified user by the strategy type.

            Args:
            - org_name (str): The name of the organization.
            - flow_type (str): The flow_type of the article (case-sensitive).
            - list_only (Optional[bool]): If True, do not include the contents, default False.
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[ChatHistory]: The list of shared articles.

            Raises:
            - EntityNotFoundException: If the organization is not found.
            """

            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            chat_manager = get_history_manager(context)
            ch_list = chat_manager.get_shared_samples_by_flow_type(
                org=org, flow_type=flow_type
            )
            shared_list: List[ChatHistory] = []
            for ch in ch_list:
                if ch.share_to_public:
                    if list_only:
                        ch.queries = []
                        ch.answers = []
                    shared_list.append(ch)
            return shared_list

        @self.get("/shared/{org_name}/{kb_name}", response_model=List[ChatHistory])
        async def get_shared_articles_in_kb(
            org_name: str,
            kb_name: str,
            article_type: Optional[str] = None,
            list_only: Optional[bool] = False,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[ChatHistory]:
            """
            Get all shared articles in the knowledge base by the KB owner.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - article_type (Optional[str]): The type of the article. None means all.
            - list_only (Optional[bool]): If True, do not include the contents, default False.
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[ChatHistory]: The list of shared articles.

            Raises:
            - EntityNotFoundException: If the organization or knowledge base is not found.
            - HTTPException: If the user does not have access to the knowledge base.
            """
            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise EntityNotFoundException(entity_name=org_name, entity_type="Org")

            kb = self.kb_manager.get_kb_by_name(org=org, kb_name=kb_name)
            if kb is None:
                raise EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if self.auth.can_read_kb(org=org, kb=kb, user=calling_user) is False:
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} does not have access to KB {kb_name}",
                )

            if article_type is None or article_type == "" or article_type == "all":
                article_type = None
            else:
                article_type = ArticleType(article_type)

            chat_manager = get_history_manager(context)
            ch_list = chat_manager.get_kb_owner_ch_entries_by_type(
                org=org, kb=kb, article_type=article_type
            )
            shared_list: List[ChatHistory] = []
            for ch in ch_list:
                if ch.share_to_public:
                    if list_only:
                        ch.queries = []
                        ch.answers = []
                    shared_list.append(ch)
            return shared_list

        @self.post("/add_section", response_model=ChatHistory)
        async def add_section(
            org_name: str,
            kb_name: str,
            chat_id: str,
            query_id: str,
            position_in_answer: str,
            new_section_title: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatHistory:
            """
            Add a new section to an article at the provided position.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - chat_id (str): The ID of the chat history.
            - query_id (str): The ID of the query.
            - position_in_answer (str): The position in the answer.
            - new_section_title (str): The title for the new section.
            - calling_user: The calling user by dependency injection.

            Returns:
            - ChatHistory: The updated chat history.

            Raises:
            - EntityNotFoundException: If the organization, knowledge base, or chat history is not found.
            - UnexpectedCaseException: If the KB ID does not match the chat history.
            - HTTPException: If the user does not have access to the organization or knowledge base.
            """
            chat_history = self.chat_manager.get_ch_entry(
                calling_user.username, chat_id
            )
            if chat_history is None:
                raise EntityNotFoundException(
                    entity_name=chat_id, entity_type="ChatHistory"
                )

            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=org_name, entity_type="Organization"
                )

            kb = self.kb_manager.get_kb_by_name(org, kb_name)
            if kb is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            if kb.kb_id != chat_history.kb_id:
                raise exceptions.UnexpectedCaseException(
                    f"KB ID mismatch with Chat: {kb.kb_id} != {chat_history.kb_id}"
                )

            caic = ChatAnswerItemCreate(
                chat_id=chat_id,
                query_id=query_id,
                answer_content="",
                answer_plan=None,
                position_in_answer=position_in_answer,
                answer_title=new_section_title,
                answer_score=1.0,
                answer_source_items={},
            )

            updated_ch = self.chat_manager.add_answer_item_to_chat(
                username=calling_user.username,
                chat_id=chat_id,
                query_id=query_id,
                position_in_answer=position_in_answer,
                new_answer=caic,
            )
            return updated_ch

        @self.post(
            "/remove_section",
            response_model=Optional[ChatHistory],
        )
        async def remove_section(
            chat_id: str,
            query_id: str,
            position_in_answer: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[ChatHistory]:
            """
            Remove a section from an article at the provided position.

            Args:
            - chat_id (str): The ID of the chat history.
            - query_id (str): The ID of the query.
            - position_in_answer (str): The position in the answer.
            - calling_user: The calling user by dependency injection.

            Returns:
            - ChatHistory: The updated chat history. None if not updated.

            Raises:
            - EntityNotFoundException: If the chat history is not found.
            """
            chat_history = self.chat_manager.get_ch_entry(
                calling_user.username, chat_id
            )
            if chat_history is None:
                raise EntityNotFoundException(
                    entity_name=chat_id, entity_type="ChatHistory"
                )

            updated_ch = self.chat_manager.remove_answer_item_from_chat(
                username=calling_user.username,
                chat_id=chat_id,
                query_id=query_id,
                position_in_answer=position_in_answer,
            )
            return updated_ch

        @self.post("/update_title/{chat_id}", response_model=ChatHistory)
        async def update_article_title(
            chat_id: str,
            new_title: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatHistory:
            """
            Update the title of an article in the chat history.

            Args:
            - chat_id (str): The ID of the chat history.
            - new_title (str): The new title for the article.
            - calling_user: The calling user by dependency injection.

            Returns:
            - ChatHistory: The updated chat history.

            Raises:
            - EntityNotFoundException: If the chat history is not found.
            """
            chat_history = self.chat_manager.get_ch_entry(
                calling_user.username, chat_id
            )
            if chat_history is None:
                raise EntityNotFoundException(
                    entity_name=chat_id, entity_type="ChatHistory"
                )

            chat_history.name = new_title
            chat_history = self.chat_manager.update_ch_entry(chat_history)
            return chat_history

        @self.post(
            "/update_section/{chat_id}/{query_id}/{position_in_answer}",
            response_model=ChatHistory,
        )
        async def update_article_section(
            chat_id: str,
            query_id: str,
            position_in_answer: str,
            new_section_title: str = Body(...),
            new_section_content: str = Body(...),
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatHistory:
            """
            Manually update a section in an article in the chat history.

            The old section will have (tmp solution):
            - score=-2 to indicate that it is replaced
            - query_id="-{query_id}-" so that query_id based search will not use it
            - updated updated_at timestamp

            The answer plan for the new section will be set to None to indicate that
            it is manually created.

            Args:
            - chat_id (str): The ID of the chat history.
            - query_id (str): The ID of the query.
            - position_in_answer (str): The position in the answer.
            - new_section_title (str): The new title for the section.
            - new_section_content (str): The new content for the section.
            - calling_user: The calling user by dependency injection.

            Returns:
            - ChatHistory: The updated chat history.

            Raises:
            - EntityNotFoundException: If chat history or target section is not found.
            """
            chat_history = self.chat_manager.get_ch_entry(
                calling_user.username, chat_id
            )
            if chat_history is None:
                raise EntityNotFoundException(
                    entity_name=chat_id, entity_type="ChatHistory"
                )

            target_item = None
            for chat_answer_item in chat_history.answers:
                if chat_answer_item.query_id != query_id:
                    continue
                if chat_answer_item.position_in_answer != position_in_answer:
                    continue
                target_item = chat_answer_item

            if target_item is None:
                raise EntityNotFoundException(
                    entity_name=position_in_answer, entity_type="ChatAnswerItem"
                )

            target_item.answer_title = new_section_title
            target_item.answer_content = new_section_content
            target_item.answer_plan = None  # mean manually created
            new_chat_history = self.chat_manager.update_ch_entry_answer(
                username=calling_user.username,
                chat_id=chat_id,
                query_id=query_id,
                position_in_answer=position_in_answer,
                new_answer=target_item,
            )
            return new_chat_history

        @self.post("/regen_section", response_model=ChatHistory)
        async def regen_section(
            org_name: str,
            kb_name: str,
            chat_id: str,
            query_id: str,
            position_in_answer: str,
            new_section_plan: ArticleSectionPlan,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> ChatHistory:
            """
            Regenerates a section in the chat history based on the provided parameters.

            Args:
            - org_name (str): The name of the organization.
            - kb_name (str): The name of the knowledge base.
            - chat_id (str): The ID of the chat history.
            - query_id (str): The ID of the query.
            - position_in_answer (str): The position of the answer in the chat history.
            - new_section_plan (ArticleSectionPlan): The plan for the new section.
            - calling_user: The calling user by dependency injection.

            Returns:
            - ChatHistory: The updated chat history.

            Raises:
            - EntityNotFoundException: If the organization, knowledge base, chat history,
                chat query, chat answer item, or chat query item is not found.
            """
            org = self.org_manager.get_org_by_name(org_name)
            if org is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=org_name, entity_type="Organization"
                )

            kb = self.kb_manager.get_kb_by_name(org, kb_name)
            if kb is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=kb_name, entity_type="KnowledgeBase"
                )

            chat_query = self.chat_manager.get_ch_entry(
                username=calling_user.username, chat_id=chat_id
            )

            if chat_query is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=chat_id, entity_type="ChatHistory"
                )

            strategy = None
            global_answer_source_itemss = chat_query.answers[0].answer_source_items
            found_query_item = None
            for query_item in chat_query.queries:
                if query_item.query_id != query_id:
                    continue
                found_query_item = query_item
                if query_item.strategy_id is not None:
                    strategy = self.strategy_store.get_strategy_by_id(
                        query_item.strategy_id
                    )
                break

            if found_query_item is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=query_id, entity_type="ChatQuery"
                )

            if strategy is None:
                strategy = self.strategy_store.get_default_strategy()

            sections = []
            found_answer = None
            for answer in chat_query.answers:
                if answer.answer_score < 0:
                    continue

                if answer.query_id != query_id:
                    continue

                if answer.position_in_answer != position_in_answer:
                    sections.append(
                        ArticleSection(
                            title=answer.answer_title,
                            content=answer.answer_content,
                            plan=answer.answer_plan,
                        )
                    )
                    continue

                found_answer = answer
                break

            if found_answer is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=position_in_answer, entity_type="ChatAnswerItem"
                )

            exec_info = ExecInfo(
                context=context,
                org=org,
                kb=kb,
                user=calling_user,
                target_chat_query_item=found_query_item,
                display_logger=None,
            )

            new_section = subflows.SubflowGenSection.run_subflow(
                exec_info=exec_info,
                section_plan=new_section_plan,
                accumulated_source_items=global_answer_source_itemss,
                previous_sections=sections,
            )

            caic = ChatAnswerItemCreate(
                chat_id=chat_id,
                query_id=query_id,
                answer_content=new_section.content,
                answer_plan=new_section.plan,
                position_in_answer=position_in_answer,
                answer_title=new_section.title,
                answer_score=1.0,
                answer_source_items=global_answer_source_itemss,
            )

            updated_chat_query = self.chat_manager.update_ch_entry_answer(
                username=calling_user.username,
                chat_id=chat_id,
                query_id=query_id,
                position_in_answer=position_in_answer,
                new_answer=caic,
            )
            return updated_chat_query
