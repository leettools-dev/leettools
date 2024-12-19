from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from leettools.core.consts.display_type import DisplayType


class TopicSpec(BaseModel):
    title: str
    prompt: str


class TopicList(BaseModel):
    topics: List[TopicSpec]


class ArticleSectionPlan(BaseModel):
    title: str
    search_query: str
    user_prompt_template: str
    system_prompt_template: str


class ArticleSection(BaseModel):
    title: str
    content: str
    plan: Optional[ArticleSectionPlan] = None
    display_type: Optional[DisplayType] = None
    user_data: Optional[Dict[str, Any]] = None
