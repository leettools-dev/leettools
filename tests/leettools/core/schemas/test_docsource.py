from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.schemas.docsource import (
    DocSourceCreate,
    DocSourceInDB,
    IngestConfig,
)


def test_docsource_create():
    retriever_type = "google"
    query = "test"
    days_limit = 0
    max_results = 10
    timestamp = "2022-01-01-00-00-00"
    flow_options = {
        "retriever_type": retriever_type,
        "days_limit": days_limit,
        "max_results": max_results,
    }

    docsource_create = DocSourceCreate(
        kb_id="111",
        source_type=DocSourceType.SEARCH,
        uri=(
            f"search://{retriever_type}?q={query}&date_range={days_limit}"
            f"&max_results={max_results}&ts={timestamp}"
        ),
        display_name=query,
        ingest_config=IngestConfig(
            flow_options=flow_options,
        ),
    )

    dcsource_in_db = DocSourceInDB.from_docsource_create(docsource_create)

    assert dcsource_in_db.kb_id == "111"
    assert dcsource_in_db.source_type == DocSourceType.SEARCH
    assert dcsource_in_db.uri == (
        f"search://{retriever_type}?q={query}&date_range={days_limit}"
        f"&max_results={max_results}&ts={timestamp}"
    )
    assert dcsource_in_db.display_name == query
    assert isinstance(dcsource_in_db.ingest_config, IngestConfig)
