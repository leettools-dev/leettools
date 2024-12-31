from pathlib import Path

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.flow_option import (
    FLOW_OPTION_OUTPUT_LANGUAGE,
    FLOW_OPTION_SEARCH_LANGUAGE,
)
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import steps


def test_step_vectdb_search(tmp_path: Path):

    temp_setup = TempSetup()
    context = temp_setup.context

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
    file_name = "web_design.txt"

    org, kb, user = temp_setup.create_tmp_org_kb_user()
    docsource = temp_setup.create_and_process_docsource(
        org=org,
        kb=kb,
        user=user,
        tmp_path=tmp_path,
        file_name=file_name,
        content=content,
    )
    try:
        _test_flow_step(context, org, kb, user, docsource)
    finally:
        temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_flow_step(
    context: Context, org: Org, kb: KnowledgeBase, user: User, docsource: DocSource
):

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

    search_results = steps.StepVectorSearch.run_step(
        exec_info=exec_info,
        query_metadata=None,
        rewritten_query=query,
    )

    assert search_results is not None
    assert len(search_results) > 0
    print("========================")
    print(search_results)
    print(len(search_results))
