from leettools.flow.flows.post.flow_post import _section_plan_for_posts
from leettools.flow.schemas.article import ArticleSectionPlan


def test_create_plan_for_posts():

    query = "test query"
    search_phrases = "test search phrase"
    section_plan: ArticleSectionPlan = _section_plan_for_posts(
        query=query, search_phrases=search_phrases
    )

    assert section_plan.title == query
    assert section_plan.search_query == search_phrases + " " + query
    assert query in section_plan.user_prompt_template
