import inspect
import random
from pathlib import Path
from typing import Optional, Tuple

from leettools.chat.history_manager import _HMInstances
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.chat_query_item import ChatQueryItem
from leettools.core.schemas.docsource import DocSource, DocSourceCreate
from leettools.core.schemas.knowledgebase import KBCreate, KnowledgeBase
from leettools.core.schemas.organization import Org, OrgCreate
from leettools.core.schemas.user import User, UserCreate
from leettools.eds.pipeline.ingest.connector import create_connector
from leettools.flow.exec_info import ExecInfo
from leettools.flow.utils import pipeline_utils


class TempSetup:

    def __init__(self):
        from leettools.context_manager import ContextManager

        self.context = ContextManager().get_context()
        self.context.reset(is_test=True)
        self.context.settings.SINGLE_USER_MODE = False
        self.context.settings.DEFAULT_DENSE_EMBEDDER = "dense_embedder_local_svc_client"

        # TODO: the author should be dynamically set
        self.context.get_authorizer()._reset_for_test()

        _HMInstances().reset_for_test()

    def __get_call_info(self):
        stack = inspect.stack()

        # stack[1] gives previous function ('create_tmp_org_kb_user' in our case)
        # stack[2] gives before previous function and so on

        fn = stack[2][1]
        fn = fn.split("/")[-1]
        ln = stack[2][2]
        func = stack[2][3]

        return fn, ln, func

    def create_tmp_org_kb_user(
        self, user: Optional[User] = None, signature: Optional[str] = ""
    ) -> Tuple[Org, KnowledgeBase, User]:
        """
        Create a temporary org, kb with the user as the owner of the kb.
        If no user is specified, a temp user will be created.
        """
        org_manager = self.context.get_org_manager()
        kb_manager = self.context.get_kb_manager()
        if signature == "":
            fn, ln, func = self.__get_call_info()
            signature = fn.removesuffix(".py").replace("test_", "")
            logger().info(f"The temp signature is {signature}")

        if user is None:
            user = self.create_tmp_user(signature=signature)

        org_name = f"{Org.TEST_ORG_PREFIX}_{signature}_{random.randint(0, 1000)}"
        org = org_manager.add_org(OrgCreate(name=org_name))

        kb_name = (
            f"{KnowledgeBase.TEST_KB_PREFIX}_{signature}_{random.randint(0, 1000)}"
        )
        kb: KnowledgeBase = kb_manager.add_kb(
            org=org,
            kb_create=KBCreate(
                org_uuid=org.org_id,
                name=kb_name,
                user_uuid=user.user_uuid,
                description="Sample description",
                auto_schedule=False,
            ),
        )

        strategy_store = self.context.get_strategy_store()
        assert strategy_store is not None
        strategy_store._reset_for_test()

        return org, kb, user

    def create_tmp_user(self, signature: Optional[str] = "") -> User:
        user_store = self.context.get_user_store()
        user = user_store.create_user(
            UserCreate(
                username=f"{User.TEST_USERNAME_PREFIX}_{signature}_{random.randint(0, 1000)}",
            )
        )
        return user

    def delete_tmp_user(self, user: User) -> None:
        user_store = self.context.get_user_store()
        if not user.username.startswith(User.TEST_USERNAME_PREFIX):
            logger().warning(
                f"Trying to remove non-test user {user.username}. Ignored."
            )
            return
        user_store.delete_user_by_id(user.user_uuid)

    def clear_tmp_org_kb_user(
        self, org: Org, kb: KnowledgeBase, user: Optional[User] = None
    ) -> None:
        kb_manager = self.context.get_kb_manager()
        org_manager = self.context.get_org_manager()

        strategy_store = self.context.get_strategy_store()
        strategy_store._reset_for_test()

        if not kb.name.startswith(KnowledgeBase.TEST_KB_PREFIX):
            logger().warning(f"Trying to remove non-test kb {kb.name}. Ignored.")
            return
        kb_manager.delete_kb_by_name(org, kb.name)

        if not org.name.startswith(Org.TEST_ORG_PREFIX):
            logger().warning(f"Trying to remove non-test org {org.name}. Ignored.")
            return
        for kb in kb_manager.get_all_kbs_for_org(org, list_adhoc=True):
            kb_manager.delete_kb_by_name(org, kb.name)
        org_manager.delete_org_by_name(org.name)

        if user is not None:
            self.delete_tmp_user(user)
        else:
            user_store = self.context.get_user_store()
            assert user_store._get_dbname_for_test().endswith("_test")
            for user in user_store.get_users():
                if user.username != User.ADMIN_USERNAME:
                    assert user.username.startswith(User.TEST_USERNAME_PREFIX)
                user_store.delete_user_by_id(user.user_uuid)
            # TODO: remove tasks and jobs

    def remove_test_org_by_name(self, org_name: str):
        try:
            org_manager = self.context.get_org_manager()
            org_manager.delete_org_by_name(org_name)
        except Exception as e:
            logger().warning(
                f"Failed to remove org {org_name}. It is possible that the test "
                f"failed before the org was created. Error: {e}"
            )

    def remove_all_test_orgs(self):
        org_manager = self.context.get_org_manager()
        for org in org_manager.list_orgs():
            if org.name.startswith(Org.TEST_ORG_PREFIX):
                org_manager.delete_org_by_name(org.name)

    def remove_all_test_users(self):
        user_store = self.context.get_user_store()
        for user in user_store.get_users():
            if user.username.startswith(User.TEST_USERNAME_PREFIX):
                user_store.delete_user_by_id(user.user_uuid)

    def create_docsource(self, org: Org, kb: KnowledgeBase) -> DocSource:
        docsource_store = self.context.get_repo_manager().get_docsource_store()
        docsource = docsource_store.create_docsource(
            org,
            kb,
            DocSourceCreate(
                org_id=org.org_id,
                kb_id=kb.kb_id,
                source_type=DocSourceType.LOCAL,
                uri="dummyuri",
                display_name="test doc source",
            ),
        )
        return docsource

    def create_and_process_docsource(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        tmp_path: Path,
        file_name: str,
        content: str,
    ) -> DocSource:
        docsource_store = self.context.get_repo_manager().get_docsource_store()

        file_path = tmp_path / file_name
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        file_uri = f"file://{file_path.absolute()}"

        docsource = docsource_store.create_docsource(
            org,
            kb,
            DocSourceCreate(
                org_id=org.org_id,
                kb_id=kb.kb_id,
                source_type=DocSourceType.LOCAL,
                uri=file_uri,
                display_name="test doc source",
            ),
        )

        if kb.auto_schedule and not self.context.is_test:
            pipeline_utils.process_docsources_auto(
                org=org,
                kb=kb,
                docsources=[docsource],
                context=self.context,
                display_logger=logger(),
            )
        else:
            docsink_store = self.context.get_repo_manager().get_docsink_store()
            connector = create_connector(
                context=self.context,
                connector="connector_simple",
                org=org,
                kb=kb,
                docsource=docsource,
                docsinkstore=docsink_store,
                display_logger=logger(),
            )
            connector.ingest()
            docsink_create_list = connector.get_ingested_docsink_list()

            exec_info: ExecInfo = ExecInfo(
                context=self.context,
                org=org,
                kb=kb,
                user=user,
                display_logger=logger(),
                target_chat_query_item=ChatQueryItem(
                    query_content="dummy query",
                    query_id="dummy query id",
                    created_at=time_utils.current_datetime(),
                ),
            )
            pipeline_utils.run_adhoc_pipeline_for_docsinks(
                exec_info=exec_info, docsink_create_list=docsink_create_list
            )
        return docsource_store.get_docsource(org, kb, docsource.docsource_uuid)
