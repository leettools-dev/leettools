from typing import Dict, List, Optional

from fastapi import Depends, HTTPException

from leettools.common.exceptions import EntityNotFoundException
from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.strategy import Strategy, StrategyCreate
from leettools.core.strategy.schemas.strategy_display_settings import (
    StrategyOptionItemDisplay,
    StrategySectionDisplay,
    get_llm_inference_display_options,
    get_strategy_display_sections,
)
from leettools.core.strategy.schemas.strategy_status import StrategyStatus
from leettools.flow.flow_manager import FlowManager
from leettools.flow.flow_option_items import FlowOptionItem
from leettools.svc.api_router_base import APIRouterBase


class StrategyRouter(APIRouterBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.user_store = context.get_user_store()
        self.strategy_store = context.get_strategy_store()
        self.flow_manager = FlowManager(context.settings)

        @self.get(
            "/display_sections",
            response_model=List[StrategySectionDisplay],
            summary="Get the display sections for the strategy settings.",
        )
        async def display_sections():
            """
            Get all strategies
            """
            return get_strategy_display_sections()

        @self.get(
            "/llm_inference_options",
            response_model=Dict[str, StrategyOptionItemDisplay],
            summary="Get the model options for the LLM.",
        )
        async def llm_inference_options() -> Dict[str, StrategyOptionItemDisplay]:
            """
            Get the inference options for the LLM.
            """
            return get_llm_inference_display_options()

        @self.get(
            "/flow_options/{flow_type}",
            response_model=List[FlowOptionItem],
            summary="Get the flow options for the flow type.",
        )
        async def flow_options(flow_type: str) -> List[FlowOptionItem]:
            """
            Get the flow options for the flow type.
            """
            try:
                flow = self.flow_manager.get_flow_by_type(flow_type)

                return flow.get_flow_option_items()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid flow type {flow_type}",
                )

        @self.get(
            "/",
            response_model=List[Strategy],
            summary="Get all available strategies for the current user.",
        )
        async def get_strategies(
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Get all strategies for the current user (including system ones)
            """

            return self.strategy_store.list_active_strategies_for_user(
                user=calling_user
            )

        @self.get(
            "/strategy_id/{strategy_id}",
            response_model=Optional[Strategy],
            summary="Get an active strategy by id.",
        )
        async def get_strategy_by_id(
            strategy_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Optional[Strategy]:
            """
            Get a strategy by id, only the active strategy will be returned
            """

            strategy = self.strategy_store.get_strategy_by_id(strategy_id)
            if strategy is None:
                raise EntityNotFoundException(
                    entity_name=strategy_id, entity_type="Strategy"
                )

            # TODO: the strategy could be shared among users
            if (
                calling_user.user_uuid != strategy.user_uuid
                and calling_user.user_uuid != self.auth.get_admin_user().user_uuid
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} does not have permission to access "
                    f"strategy {strategy_id}",
                )
            return strategy

        @self.put(
            "/",
            response_model=Strategy,
            summary="Create a strategy for the current user.",
        )
        async def create_strategy(
            strategy_create: StrategyCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Create a strategy for the current user.
            """

            return self.strategy_store.create_strategy(
                strategy_create=strategy_create, user=calling_user
            )

        @self.post(
            "/status/{strategy_id}/{strategy_status}",
            response_model=None,
            summary="Update the status of a strategy by id.",
        )
        async def set_strategy_status(
            strategy_id: str,
            strategy_status: StrategyStatus,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ):
            """
            Update a strategy for the current user.
            """
            strategy = await get_strategy_by_id(strategy_id, calling_user)
            if strategy is None:
                raise EntityNotFoundException(
                    entity_name=get_strategy_by_id, entity_type="ChatStrategy"
                )
            self.strategy_store.set_strategy_status_by_id(
                strategy_id=strategy.strategy_id, status=strategy_status
            )
