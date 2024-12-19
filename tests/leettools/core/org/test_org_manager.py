import random

from leettools.common.temp_setup import TempSetup
from leettools.context_manager import Context
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org, OrgCreate, OrgUpdate

# this one needs to be deleted
test_name2 = f"{Org.TEST_ORG_PREFIX}_manager_{random.randint(1, 1000)}"


def test_org_manager():
    from leettools.settings import preset_store_types_for_tests

    for store_types in preset_store_types_for_tests():

        temp_setup = TempSetup()
        context = temp_setup.context
        context.settings.DOC_STORE_TYPE = store_types["doc_store"]
        context.settings.VECTOR_STORE_TYPE = store_types["vector_store"]
        org, kb, user = temp_setup.create_tmp_org_kb_user()

        try:
            _test_function(context, org, kb)
        finally:
            temp_setup.clear_tmp_org_kb_user(org, kb)
            temp_setup.remove_test_org_by_name(test_name2)


def _test_function(context: Context, org: Org, kb: KnowledgeBase):

    org_manager = context.get_org_manager()

    test_name = f"{Org.TEST_ORG_PREFIX}_manager_{random.randint(1, 1000)}"

    test_desc = "This is a test organization entry."
    org_create = OrgCreate(name=test_name, description=test_desc)
    org1 = org_manager.add_org(org_create)
    assert org1.name == test_name
    assert org1.description == test_desc
    assert org1.org_id is not None
    assert org1.created_at is not None
    assert org1.updated_at is not None
    assert org1.updated_at == org1.created_at

    org2 = org_manager.get_org_by_id(org1.org_id)
    assert org2 is not None
    assert org2.name == test_name
    assert org2.description == test_desc
    assert org2.org_id == org1.org_id
    assert org2.created_at is not None
    assert org2.created_at == org1.created_at

    test_desc = "This is a test organization entry."
    org_update = OrgUpdate(
        name=test_name2,
        description=test_desc,
        org_id=org1.org_id,
        org_status=org1.org_status,
    )
    org3 = org_manager.update_org(org_update)
    assert org3 is not None
    assert org3.name == test_name2
    assert org3.description == test_desc
    assert org3.org_id == org1.org_id
    assert org3.created_at == org1.created_at
    assert org3.updated_at is not None
    assert org3.updated_at >= org3.created_at

    org4 = org_manager.get_org_by_id(org1.org_id)
    assert org4 is not None
    assert org4.name == test_name2
    assert org4.description == test_desc
    assert org4.org_id == org2.org_id
    assert org4.created_at == org2.created_at
    assert org4.updated_at > org4.created_at

    org5 = org_manager.get_org_by_name(test_name2)
    assert org5 is not None
    assert org5.name == test_name2
    assert org5.description == test_desc
    assert org5.org_id == org1.org_id
    assert org5.created_at <= org1.created_at
    assert org5.updated_at > org5.created_at

    # TODO: bypass for now since there was trasient leftover data
    # need to find the leak before enbalbing this test
    # orgs = org_manager.list_orgs()
    # assert len(orgs) == 3
    # assert orgs[0].name == context.settings.DEFAULT_ORG_NAME
    # assert orgs[1].name == org.name
    # assert orgs[2].name == test_name2
