from pathlib import Path

from leettools.common.logging import logger
from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts import flow_option
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.user import User
from leettools.flow import steps
from leettools.settings import preset_store_types_for_tests
from leettools.web.retrievers.local.local import LocalSearch


def test_local_search(tmp_path: Path):

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

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]
        context.settings.GRAPH_STORE_TYPE = store_types["graph_store"]

        org, kb, user = temp_setup.create_tmp_org_kb_user()

        logger().info(
            f"Testing with doc_store: {context.settings.DOC_STORE_TYPE} "
            f"and vector_store: {context.settings.VECTOR_STORE_TYPE} "
            f"and graph_store: {context.settings.GRAPH_STORE_TYPE}"
        )

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
            logger().info(
                f"Finished testing with doc_store: {context.settings.DOC_STORE_TYPE} "
                f"and vector_store: {context.settings.VECTOR_STORE_TYPE} "
                f"and graph_store: {context.settings.GRAPH_STORE_TYPE}"
            )


def _test_flow_step(
    context: Context, org: Org, kb: KnowledgeBase, user: User, docsource: DocSource
):

    query = "web design"

    local_search = LocalSearch(
        context=context,
        org=org,
        kb=kb,
        user=user,
    )

    flow_options = {
        flow_option.FLOW_OPTION_SEARCH_LANGUAGE: "en",
        flow_option.FLOW_OPTION_OUTPUT_LANGUAGE: "cn",
    }

    segment_store = context.get_repo_manager().get_segment_store()
    segments = segment_store.get_segments_for_docsource(org, kb, docsource)
    assert segments is not None
    assert len(segments) > 0

    search_results = local_search.retrieve_search_result(
        search_keywords=query,
        flow_options=flow_options,
    )
    assert search_results is not None
    assert len(search_results) > 0

    flow_options[flow_option.FLOW_OPTION_DOC_SOURCE_UUID] = docsource.docsource_uuid
    search_results = local_search.retrieve_search_result(
        search_keywords=query,
        flow_options=flow_options,
    )
    assert search_results is not None
    assert len(search_results) > 0

    flow_options[flow_option.FLOW_OPTION_DOC_SOURCE_UUID] = "random-str"
    search_results = local_search.retrieve_search_result(
        search_keywords=query,
        flow_options=flow_options,
    )
    assert search_results is not None
    assert len(search_results) == 0
