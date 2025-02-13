from typing import Dict, List, Optional

from fastapi import Depends, HTTPException

from leettools.common.logging import logger
from leettools.core.consts.retriever_type import supported_retriever
from leettools.core.schemas.api_provider_config import APIProviderConfig
from leettools.core.schemas.user import User
from leettools.core.schemas.user_settings import UserSettings, UserSettingsUpdate
from leettools.eds.api_caller.api_utils import get_api_function_list
from leettools.settings import (
    supported_audio_file_extensions,
    supported_file_extensions,
    supported_image_file_extensions,
    supported_video_file_extensions,
)
from leettools.svc.api_router_base import APIRouterBase


class SettingsRouter(APIRouterBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.user_settings_store = context.get_user_settings_store()

        @self.get("/suggested_model_names", response_model=Dict[str, str])
        async def get_suggested_model_names() -> Dict[str, str]:
            """
            Get the suggested model names, for suggestions only.

            The key is the model name, the value is the model description.

            Right now in the flow options we do not support chooseing the API provider.
            We need to change the API provider information in the InferenceSection of
            the strategy, which will be used by all the API calls outside the RAG process.

            To get actual available models from the API provider, we need to call the
            API provider's supported_models function, which is too complex for now.
            """
            return {
                "gpt-3.5-turbo": "OpenAI GPT-3.5 Turbo",
                "gpt-4": "OpenAI GPT-4",
                "gpt-4o": "OpenAI GPT-4o",
                "gpt-4o-mini": "OpenAI GPT-4o Mini",
            }

        @self.get("/supported_web_retriever", response_model=List[str])
        async def get_supported_web_retriever(
            region: Optional[str] = "all",
        ) -> List[str]:
            """
            Get the supported web retriever for the region:

            - "all": all supported web retrievers
            - "us": only US supported web retrievers
            - "eu": only EU supported web retrievers
            - "cn": only CN supported web retrievers
            """
            return supported_retriever(region)

        @self.get("/supported_file_extensions", response_model=List[str])
        async def get_supported_file_extensions() -> List[str]:
            """
            Get the supported file extensions
            """
            return supported_file_extensions()

        @self.get("/supported_api_functions", response_model=List[str])
        async def get_supported_api_functions() -> List[str]:
            """
            Get the supported API functions
            """
            return get_api_function_list()

        @self.get("/supported_audio_extensions", response_model=List[str])
        async def get_supported_audio_extensions() -> List[str]:
            """
            Get the supported audio extensions
            """
            return supported_audio_file_extensions()

        @self.get("/supported_image_extensions", response_model=List[str])
        async def get_supported_image_extensions() -> List[str]:
            """
            Get the supported image extensions
            """
            return supported_image_file_extensions()

        @self.get("/supported_video_extensions", response_model=List[str])
        async def get_supported_video_extensions() -> List[str]:
            """
            Get the supported video extensions
            """
            return supported_video_file_extensions()

        @self.get("/", response_model=UserSettings)
        async def get_settings_for_user(
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> UserSettings:
            """
            Get the settings for the current user
            """

            return self.user_settings_store.get_settings_for_user(calling_user)

        @self.put("/", response_model=UserSettings)
        async def update_settings_for_user(
            user_settings_update: UserSettingsUpdate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> UserSettings:
            """
            Update the settings for the current user
            """
            logger().info(f"Update settings for user {user_settings_update.username}")

            return self.user_settings_store.update_settings_for_user(
                calling_user, user_settings_update
            )

        @self.put("/api_provider", response_model=APIProviderConfig)
        async def add_api_provider_config(
            api_provider_config: APIProviderConfig,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> APIProviderConfig:
            """
            Add an API provider config
            """

            return self.user_settings_store.add_api_provider_config(
                calling_user, api_provider_config
            )

        @self.get("/api_providers", response_model=Dict[str, List[APIProviderConfig]])
        async def get_all_api_providers(
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Dict[str, List[APIProviderConfig]]:
            """
            Get the API providers available for the current user. The result is a
            dictionary with the username as the key and the list of API providers
            as the value.
            """

            user_providers = (
                self.user_settings_store.get_all_api_provider_configs_for_user(
                    calling_user
                )
            )
            admin_providers = (
                self.user_settings_store.get_all_api_provider_configs_for_user(
                    self.auth.get_admin_user()
                )
            )
            return {
                calling_user.username: user_providers,
                User.ADMIN_USERNAME: admin_providers,
            }

        @self.get(
            "/api_provider/{username}/{api_provider}", response_model=APIProviderConfig
        )
        async def get_api_provider(
            username: str,
            api_provider: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> APIProviderConfig:
            """
            Add an API provider config
            """

            if username != User.ADMIN_USERNAME and username != calling_user.username:
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not allowed to access user {username}'s API providers.",
                )
            if username == User.ADMIN_USERNAME:
                return self.user_settings_store.get_api_provider_config_by_name(
                    self.auth.get_admin_user(), api_provider
                )
            return self.user_settings_store.get_api_provider_config_by_name(
                calling_user, api_provider
            )
