from leettools.context_manager import ContextManager
from leettools.core.config.performance_configurable import PerformanceConfigurable
from leettools.core.consts.segment_embedder_type import SegmentEmbedderType
from leettools.core.schemas.knowledgebase import KBCreate, KBPerfConfig


def test_record_perf_config():

    class MyTestClass(PerformanceConfigurable):
        PerfConfigIdStr: str = "KBPerfConfig"

    kb_create = KBCreate(
        name="test_kb",
        description="test_kb_description",
        embedder_type=SegmentEmbedderType.HYBRID,
        dense_embedder="test_dense_embedder",
        sparse_embedder="test_sparse_embedder",
        dense_embedder_params={"key1": "value1"},
        sparse_embedder_params={"key2": "value2"},
        enable_contextual_retrieval=True,
        share_to_public=True,
    )

    context = ContextManager().get_context()
    is_svc = context.is_svc

    try:
        context.is_svc = False

        kb_perf_config = KBPerfConfig.from_base_model(kb_create)
        MyTestClass.record_perf_config(kb_perf_config)

        config_manager = context.get_config_manager()
        perf_config = config_manager.get_config(MyTestClass.PerfConfigIdStr)

        assert perf_config is not None
        assert perf_config == kb_perf_config.model_dump()
        assert "name" not in perf_config
        assert "description" not in perf_config
        assert "embedder_type" in perf_config
    finally:
        context.is_svc = is_svc
