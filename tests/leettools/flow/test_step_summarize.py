from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.flow_option import (
    FLOW_OPTION_OUTPUT_LANGUAGE,
    FLOW_OPTION_SEARCH_LANGUAGE,
)
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import steps


def test_get_summarize():

    temp_setup = TempSetup()

    context = temp_setup.context

    org, kb, user = temp_setup.create_tmp_org_kb_user()

    user = temp_setup.create_tmp_user()

    try:
        _test_flow_step(context, org, kb, user)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_flow_step(context: Context, org: Org, kb: KnowledgeBase, user: User):

    query = "web design"

    from leettools.chat import chat_utils

    exec_info = chat_utils.setup_exec_info(
        context=context,
        query=query,
        org_name=org.name,
        kb_name=kb.name,
        username=user.username,
        strategy_name=None,
        flow_options={
            FLOW_OPTION_OUTPUT_LANGUAGE: "CN",
            FLOW_OPTION_SEARCH_LANGUAGE: "EN",
        },
        display_logger=None,
    )

    content = """
**The Art and Science of Web Design**

Web design is a dynamic discipline that blends creativity and technical expertise to craft visually appealing, user-friendly websites. At its core, web design is about creating digital experiences that engage users, convey information effectively, and meet specific goals—whether they are commercial, educational, or social.

A successful web design starts with understanding the target audience and the purpose of the website. Designers consider factors such as demographics, user behavior, and preferences to tailor the site's layout and functionality. This user-centric approach ensures that the final product resonates with visitors and keeps them engaged.

Visual elements play a pivotal role in web design. From color schemes and typography to images and animations, every element contributes to the overall aesthetics and feel of the website. A well-designed site strikes a balance between creativity and simplicity, ensuring that visuals enhance the content rather than overshadow it.

Equally important is the functionality of the website. Navigation must be intuitive, with clear menus and logical page hierarchies. Responsive design is crucial in today’s digital landscape, ensuring that websites look and function seamlessly across devices, from desktops to smartphones.

Web design also involves technical considerations, such as optimizing load times, ensuring accessibility, and adhering to web standards. Tools like HTML, CSS, and JavaScript form the foundation of web design, while frameworks like Bootstrap or Tailwind streamline development. Furthermore, integrating SEO principles ensures that the website is discoverable by search engines.

As technology evolves, so do web design trends. Minimalism, dark mode, interactive animations, and personalized user experiences are just a few of the trends shaping the industry today.

In essence, web design is a harmonious blend of art and science. By combining creativity with technical proficiency, designers can build websites that not only captivate users but also achieve their intended objectives.

https://www.example.com/web-design

Published by: John Doep
Date: Feburary 22, 2022
"""

    document_summary = steps.StepSummarize._summarize_content(
        exec_info=exec_info, content=content
    )

    print(document_summary)

    assert document_summary is not None
    assert document_summary.summary is not None
    assert document_summary.keywords is not None
    assert len(document_summary.summary) > 0
    assert len(document_summary.keywords) > 0
    assert document_summary.links is not None
    assert len(document_summary.links) == 1
    assert document_summary.links[0] == "https://www.example.com/web-design"
    assert document_summary.authors is not None
    assert len(document_summary.authors) == 1
    assert document_summary.authors[0] == "John Doep"
    assert document_summary.content_date is not None
    assert document_summary.content_date == "2022-02-22"
