from typing import List, Optional

from fastapi import Depends, HTTPException

from leettools.chat.history_manager import get_history_manager
from leettools.chat.schemas.chat_history import ChatHistory
from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.utils import time_utils
from leettools.core.schemas.user import User, UserCreate, UserUpdate
from leettools.eds.usage.schemas.usage_api_call import UsageAPICall, UsageAPICallSummary
from leettools.svc.api_router_base import APIRouterBase
from leettools.svc.util.svc_utils import get_user_with_auth


class UserRouter(APIRouterBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context

        self.context = context
        self.user_store = context.get_user_store()
        self.usage_store = context.get_usage_store()

        @self.get("/shared/{username}/{article_type}", response_model=List[ChatHistory])
        async def get_shared_articles_by_user(
            username: str,
            article_type: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[ChatHistory]:
            """
            Retrieves a list of shared articles by a specific user.

            Args:
            - username (str): The username of the user whose shared articles are to be retrieved.
            - article_type (str): The type of articles to retrieve (e.g., "news", "blog").
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[ChatHistory]: A list of shared articles by the specified user.

            Raises:
            - EntityNotFoundException: If the specified user does not exist.
            """
            user = self._get_user(username)
            if user is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=username, entity_type="User"
                )
            chat_manager = get_history_manager(context)
            ch_list = chat_manager.get_ch_entries_by_username_with_type(
                username=username, article_type=article_type
            )
            shared_list: List[ChatHistory] = []
            for ch in ch_list:
                if ch.share_to_public:
                    shared_list.append(ch)
            return shared_list

        @self.get("/usage_detail/{usage_record_id}", response_model=UsageAPICall)
        async def get_api_usage_detail_by_id(
            usage_record_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> UsageAPICall:
            """
            Get the API usage details for the given usage record ID.

            Args:
                usage_record_id (str): The usage record ID.
                calling_user_dict: Injected information about the calling user.

            Returns:
                UsageAPICall: The usage details.

            Raises:
                HTTPException: If the calling user is not allowed to access this API.
                EntityNotFoundException: If the usage record with the given ID is not found.
            """
            usage_record = self.usage_store.get_api_usage_detail_by_id(usage_record_id)
            if usage_record is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=usage_record_id, entity_type="Usage record"
                )

            user = self.user_store.get_user_by_uuid(usage_record.user_uuid)
            if user is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=usage_record.user_uuid, entity_type="User"
                )

            if (
                calling_user.username != User.ADMIN_USERNAME
                and calling_user.username != user.username
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"User {calling_user.username} is not allowed to access this record {usage_record_id}.",
                )

            return usage_record

        @self.post("/usage_details/{username}", response_model=List[UsageAPICall])
        async def get_api_usage_details_by_user(
            username: str,
            start_time_in_ms: Optional[int] = None,
            end_time_in_ms: Optional[int] = None,
            start: Optional[int] = 0,
            limit: Optional[int] = 0,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[UsageAPICall]:
            """
            Get the API usage details for the given user within the given time range.

            Args:
            - username (str): The username.
            - start_time_in_ms (Optional[int]): The start time in milliseconds, exclusive.
            - end_time_in_ms (Optional[int]): The end time in milliseconds, inclusive.
            - start (Optional[int]): The start index of the usage records to return, default 0.
            - limit (Optional[int]): The maximum number of usage records to return, 0 means no limit.
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[UsageAPICall]: A list of usage details.
            """
            if calling_user.username != User.ADMIN_USERNAME:
                if calling_user.username != username:
                    raise HTTPException(
                        status_code=403,
                        detail=f"User {calling_user.username} is not allowed to access the usage of {username}",
                    )
                else:
                    # the user can access his own usage
                    pass
            else:
                # admin can access any user's usage
                pass

            user = self._get_user(username)
            if user is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=username, entity_type="User"
                )

            if start_time_in_ms is None:
                start_time_in_ms = 0
            if end_time_in_ms is None:
                end_time_in_ms = time_utils.cur_timestamp_in_ms()

            usage_list = self.usage_store.get_api_usage_details_by_user(
                user.user_uuid, start_time_in_ms, end_time_in_ms, start, limit
            )
            return usage_list

        @self.post("/usage_detail_count/{username}", response_model=int)
        async def get_api_usage_count_by_user(
            username: str,
            start_time_in_ms: Optional[int] = None,
            end_time_in_ms: Optional[int] = None,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> int:
            """
            Get the API usage record count for the given user within the given time range.

            Args:
            - username (str): The username.
            - start_time_in_ms (Optional[int]): The start time in milliseconds, exclusive.
            - end_time_in_ms (Optional[int]): The end time in milliseconds, inclusive.
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[UsageAPICall]: A list of usage details.
            """
            if calling_user.username != User.ADMIN_USERNAME:
                if calling_user.username != username:
                    raise HTTPException(
                        status_code=403,
                        detail=f"User {calling_user.username} is not allowed to access the usage of {username}",
                    )
                else:
                    # the user can access his own usage
                    pass
            else:
                # admin can access any user's usage
                pass

            user = self._get_user(username)
            if user is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=username, entity_type="User"
                )

            if start_time_in_ms is None:
                start_time_in_ms = 0
            if end_time_in_ms is None:
                end_time_in_ms = time_utils.cur_timestamp_in_ms()

            usage_count = self.usage_store.get_api_usage_count_by_user(
                user.user_uuid, start_time_in_ms, end_time_in_ms
            )
            return usage_count

        @self.post("/usage_summary/{username}", response_model=UsageAPICallSummary)
        async def get_usage_summary_by_user(
            username: str,
            start_time_in_ms: Optional[int] = None,
            end_time_in_ms: Optional[int] = None,
            start: Optional[int] = 0,
            limit: Optional[int] = 0,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> UsageAPICallSummary:
            """
            Get the API token count for the given user within the given time range.

            Args:
            - username (str): The username.
            - start_time_in_ms (Optional[int]): The start time in milliseconds, exclusive.
            - end_time_in_ms (Optional[int]): The end time in milliseconds, inclusive.
            - start (Optional[int]): The start index of the usage records to return.
            - limit (Optional[int]): The maximum number of usage records to return. 0 means no limit.
            - calling_user: The calling user by dependency injection.

            Returns:
            - UsageAPICallSummary: A summary of the API usage.

            Raises:
            - HTTPException: If the calling user is not allowed to access the usage of the given username.
            - EntityNotFoundException: If the user with the given username is not found.
            """
            if calling_user.username != User.ADMIN_USERNAME:
                if calling_user.username != username:
                    raise HTTPException(
                        status_code=403,
                        detail=f"User {calling_user.username} is not allowed to access the usage of {username}",
                    )
                else:
                    # the user can access his own usage
                    pass
            else:
                # admin can access any user's usage
                pass

            user = self._get_user(username)
            if user is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=username, entity_type="User"
                )

            if start_time_in_ms is None:
                start_time_in_ms = 0
            if end_time_in_ms is None:
                end_time_in_ms = time_utils.cur_timestamp_in_ms()

            usage_summary = self.usage_store.get_usage_summary_by_user(
                user.user_uuid, start_time_in_ms, end_time_in_ms, start, limit
            )
            return usage_summary

        @self.get("/list", response_model=List[User])
        async def list_users(
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[User]:
            """
            List all users. Only the admin user is allowed to access this API.

            Args:
            - calling_user: The calling user by dependency injection.

            Returns:
            - List[User]: A list of user objects.

            Raises:
            - HTTPException: If the current user is not authorized to access this API.
            """
            if calling_user.username != User.ADMIN_USERNAME:
                raise HTTPException(
                    status_code=403,
                    detail=f"Only {User.ADMIN_USERNAME} is allowed to access this API",
                )
            users = self.user_store.get_users()
            return users

        @self.get("/{username}", response_model=User)
        async def get_user_by_name(
            username: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> User:
            """
            Retrieve a user by username.

            Args:
            - username (str): The username of the user to retrieve.
            - calling_user_dict: Injected information about the calling user.

            Returns:
            - User: The user object.

            Raises:
            - HTTPException: If the calling user is not allowed to access this API.
            - EntityNotFoundException: If the user with the given username is not found.
            """
            if (
                calling_user.username != User.ADMIN_USERNAME
                and calling_user.username != username
            ):
                raise HTTPException(
                    status_code=403, detail="User is not allowed to access this API"
                )

            user = self._get_user(username)
            return user

        @self.put("/", response_model=User)
        async def create_user(
            user_create: UserCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> User:
            """
            Create a new user. Only the admin user is allowed to access this API.

            If the username an empty string, the user will be created based on the
            information from the auth provider / email. If the username is already in
            use, the existing user will be returned.

            Args:
            - user_create (UserCreate): The user creation data.
            - calling_user: The calling user by dependency injection.

            Returns:
            - User: The created user.

            Raises:
            - HTTPException: If the current user is not authorized to access this API.
            """
            if calling_user.username != User.ADMIN_USERNAME:
                raise HTTPException(
                    status_code=403,
                    detail=f"Only {User.ADMIN_USERNAME} is allowed to access this API",
                )
            if user_create.username == "":
                user = get_user_with_auth(
                    auth_provider=user_create.auth_provider,
                    full_name=user_create.full_name,
                    email=user_create.email,
                    auth_uuid=user_create.auth_uuid,
                    auth_username=user_create.auth_username,
                )
            else:
                user = self.user_store.get_user_by_name(user_create.username)
                if user is None:
                    user = self.user_store.create_user(user_create)
                    return user
                logger().info(
                    f"User {user_create.username} already exists, returning the existing user"
                )
            return user

        @self.post("/", response_model=User)
        async def update_user(
            user_update: UserUpdate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> User:
            target_uuid = user_update.user_uuid
            if (
                calling_user.username != User.ADMIN_USERNAME
                and calling_user.user_uuid != target_uuid
            ):
                raise HTTPException(
                    status_code=403, detail="User is not allowed to access this API"
                )

            user = self.user_store.get_user_by_uuid(target_uuid)
            if user is None:
                raise exceptions.EntityNotFoundException(
                    entity_name=target_uuid, entity_type="User"
                )
            updated_user = self.user_store.update_user(user_update)
            return updated_user

    def _get_user(self, username: str):
        user = self.user_store.get_user_by_name(username)
        if user is None:
            raise exceptions.EntityNotFoundException(
                entity_name=username, entity_type="User"
            )
        return user
