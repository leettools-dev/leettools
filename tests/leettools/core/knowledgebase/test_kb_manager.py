from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import DocSourceCreate
from leettools.core.schemas.knowledgebase import KBCreate, KBUpdate, KnowledgeBase
from leettools.core.schemas.organization import Org


def test_kb_manager():

    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]
        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
            _test_adhoc_kb(context, org, kb)
            _test_kb_name(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):
    kb_manager = context.get_kb_manager()
    ds_store = context.get_repo_manager().get_docsource_store()

    test_name = "test_kb_1"
    test_desc = "This is a test KB"
    kb_create = KBCreate(name=test_name, description=test_desc)
    kb_1 = kb_manager.add_kb(org, kb_create)
    assert kb_1.name == test_name

    kb_1 = kb_manager.get_kb_by_name(org, test_name)
    assert kb_1 is not None
    assert kb_1.name == test_name
    assert kb_1.description == test_desc

    kb_1 = kb_manager.get_kb_by_name(org, "non_existent")
    assert kb_1 is None

    try:
        kb_1 = kb_manager.add_kb(org, kb_create)
        assert False
    except Exception as e:
        assert e.__class__.__name__ == "EntityExistsException"

    kb_2 = kb_manager.add_kb(
        org, KBCreate(name="test_kb_2", description="This is a test KB 2")
    )
    assert kb_2 is not None
    assert kb_2.name == "test_kb_2"

    kbs = kb_manager.get_all_kbs_for_org(org)
    assert len(kbs) == 3

    kb_2_get = kb_manager.get_kb_by_id(org, kb_2.kb_id)
    assert kb_2_get is not None
    assert kb_2_get.name == kb_2.name
    assert kb_2_get.description == kb_2.description
    assert kb_2_get.kb_id == kb_2.kb_id

    update_desc = "Updated description."
    kb_1 = kb_manager.update_kb(org, KBUpdate(name=test_name, description=update_desc))
    assert kb_1 is not None
    assert kb_1.name == test_name
    assert kb_1.description == update_desc
    assert kb_1.updated_at is not None
    assert kb_1.updated_at > kb_1.created_at
    assert kb_1.promotion_metadata is None

    promotion_metadata = {"image": "image_url", "link": "link_url"}

    kb_1 = kb_manager.update_kb(
        org,
        KBUpdate(name=test_name, promotion_metadata=promotion_metadata),
    )
    assert kb_1 is not None
    assert kb_1.name == test_name
    assert kb_1.description == update_desc
    assert kb_1.updated_at is not None
    assert kb_1.updated_at > kb_1.created_at
    assert kb_1.promotion_metadata == promotion_metadata

    kb_1 = kb_manager.get_kb_by_name(org, test_name)
    assert kb_1 is not None
    assert kb_1.name == test_name
    assert kb_1.description == update_desc
    assert kb_1.updated_at is not None
    assert kb_1.updated_at > kb_1.created_at

    docsource_create = DocSourceCreate(
        org_id=org.org_id,
        kb_id=kb_1.kb_id,
        source_type=DocSourceType.URL,
        uri="https://www.example.com",
    )
    docsource1 = ds_store.create_docsource(org, kb_1, docsource_create)
    assert docsource1.docsource_uuid is not None

    docsources = ds_store.get_docsources_for_kb(org, kb_1)
    assert len(docsources) == 1

    rtn_value = kb_manager.delete_kb_by_name(org, test_name)
    assert rtn_value is True
    kbs = kb_manager.get_all_kbs_for_org(org)
    assert len(kbs) == 2

    docsources = ds_store.get_docsources_for_kb(org, kb_1)
    assert len(docsources) == 0


def _test_adhoc_kb(context: Context, org: Org, kb: KnowledgeBase):

    kb_manager = context.get_kb_manager()
    adhoc_kb = kb_manager.add_kb(
        org,
        KBCreate(
            name="adhoc_kb", description="This is an adhoc KB", auto_schedule=False
        ),
    )
    assert adhoc_kb is not None

    adhoc_kb_retrieved = kb_manager.get_kb_by_id(org, adhoc_kb.kb_id)
    assert adhoc_kb_retrieved is not None
    assert adhoc_kb_retrieved.name == "adhoc_kb"
    assert adhoc_kb_retrieved.description == "This is an adhoc KB"
    assert adhoc_kb_retrieved.auto_schedule is False

    all_kbs = kb_manager.get_all_kbs_for_org(org, list_adhoc=True)
    # we have another KB created in the previous test function
    assert len(all_kbs) == 3

    all_kbs = kb_manager.get_all_kbs_for_org(org)
    assert len(all_kbs) == 2

    rtn_value = kb_manager.delete_kb_by_name(org, "adhoc_kb")
    assert rtn_value is True

    # since we do soft delete, we should still be able to retrieve the adhoc KB by id
    adhoc_kb_retrieved = kb_manager.get_kb_by_id(org, adhoc_kb.kb_id)
    assert adhoc_kb_retrieved is not None
    assert adhoc_kb_retrieved.is_deleted is True

    adhoc_kb_retrieved = kb_manager.get_kb_by_name(org, adhoc_kb.name)
    assert adhoc_kb_retrieved is None


def _test_kb_name(context: Context, org: Org, kb: KnowledgeBase):

    kb_manager = context.get_kb_manager()
    lower_case_name = "case_kb"
    lower_case_kb = kb_manager.add_kb(
        org,
        KBCreate(name=lower_case_name, description="This is an adhoc KB"),
    )
    upper_case_name = "CASE_KB"
    upper_case_kb = kb_manager.add_kb(
        org,
        KBCreate(name=upper_case_name, description="This is an adhoc KB"),
    )
    assert lower_case_kb.kb_id != upper_case_kb.kb_id
    assert lower_case_kb.name != upper_case_kb.name
    assert lower_case_kb.description == upper_case_kb.description
