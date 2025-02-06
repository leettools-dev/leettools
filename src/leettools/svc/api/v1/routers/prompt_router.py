from typing import List, Optional

from fastapi import Depends

from leettools.core.schemas.user import User
from leettools.core.strategy.schemas.prompt import (
    Prompt,
    PromptCategory,
    PromptCreate,
    PromptStatus,
    PromptType,
)
from leettools.svc.api_router_base import APIRouterBase


class PromptRouter(APIRouterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = self.context
        self.prompt_store = context.get_prompt_store()

        @self.get("/", response_model=List[Prompt])
        async def get_all_prompts(
            category: Optional[PromptCategory] = None,
            type: Optional[PromptType] = None,
            status: Optional[PromptStatus] = None,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> List[Prompt]:
            """
            Get prompts based on the category, type, and status.

            Args:
            - category (Optional[PromptCategory]): The category of the prompts to retrieve.
            - type (Optional[PromptType]): The type of the prompts to retrieve.
            - status (Optional[PromptStatus]): The status of the prompts to retrieve.
            - calling_user: The calling user by dependency injection.

            Returns:
                List[Prompt]: A list of prompts that match the specified criteria.
            """

            prompts = self.prompt_store.list_prompts_by_filter(category, type, status)
            return prompts

        @self.get("/{prompt_id}", response_model=Prompt)
        async def get_prompt_by_id(
            prompt_id: str,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Prompt:
            """
            Get a prompt by ID.

            Args:
            - prompt_id (str): The ID of the prompt to retrieve.
            - calling_user: The calling user by dependency injection.

            Returns:
            - Prompt: The prompt object.

            """

            prompt = self.prompt_store.get_prompt(prompt_id)
            return prompt

        @self.put("/", response_model=Prompt)
        async def add_prompt_put(
            prompt_create: PromptCreate,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Prompt:
            """
            Add a prompt.

            Parameters:
            - prompt_create: The data required to create a prompt.
            - calling_user: The calling user by dependency injection.

            Returns:
            - The created prompt.
            """

            prompt = self.prompt_store.create_prompt(prompt_create)
            return prompt

        @self.post("/status/{prompt_id}", response_model=Prompt)
        async def update_status_post(
            prompt_id: str,
            status: PromptStatus,
            calling_user: User = Depends(self.auth.get_user_from_request),
        ) -> Prompt:
            """
            Set the prompt status.

            Args:
            - prompt_id (str): The ID of the prompt to update.
            - status (PromptStatus): The new status to set for the prompt.
            - calling_user: The calling user by dependency injection.

            Returns:
            - Prompt: The updated prompt object.

            """

            prompt = self.prompt_store.set_prompt_status(prompt_id, status)
            return prompt
