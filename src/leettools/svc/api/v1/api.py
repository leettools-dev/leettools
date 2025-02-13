from fastapi import APIRouter

from leettools.svc.api.v1.routers import (
    article_router,
    chat_router,
    docsink_router,
    docsource_router,
    document_router,
    file_router,
    intention_router,
    job_router,
    kb_router,
    md_router,
    org_router,
    prompt_router,
    segment_router,
    settings_router,
    strategy_router,
    task_router,
    user_router,
)


class ServiceAPIRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.org_router = org_router.OrgRouter()
        super().include_router(self.org_router, prefix="/orgs", tags=["Organization"])

        self.user_router = user_router.UserRouter()
        super().include_router(self.user_router, prefix="/users", tags=["Users"])

        self.kb_router = kb_router.KnowledgeBaseRouter()
        super().include_router(self.kb_router, prefix=f"/kbs", tags=["KnowledgeBase"])

        self.chat_router = chat_router.ChatRouter()
        super().include_router(self.chat_router, prefix="/chat", tags=["ChatHistory"])

        self.article_router = article_router.ArticleRouter()
        super().include_router(
            self.article_router, prefix="/articles", tags=["Article"]
        )

        self.docsource_router = docsource_router.DocSourceRouter()
        super().include_router(
            self.docsource_router, prefix="/docsources", tags=["DocSource"]
        )

        self.docsink_router = docsink_router.DocSinkRouter()
        super().include_router(
            self.docsink_router, prefix="/docsinks", tags=["DocSink"]
        )

        self.document_router = document_router.DocumentRouter()
        super().include_router(
            self.document_router, prefix="/documents", tags=["Documents"]
        )

        self.segment_router = segment_router.SegmentRouter()
        super().include_router(
            self.segment_router, prefix="/segments", tags=["Segments"]
        )

        self.strategy_router = strategy_router.StrategyRouter()
        super().include_router(
            self.strategy_router, prefix="/new_strategies", tags=["Strategy"]
        )

        self.prompt_router = prompt_router.PromptRouter()
        super().include_router(self.prompt_router, prefix="/prompts", tags=["Prompts"])

        self.intention_router = intention_router.IntentionRouter()
        super().include_router(
            self.intention_router, prefix="/intentions", tags=["Intentions"]
        )

        self.md_router = md_router.MDRouter()
        super().include_router(self.md_router, prefix="/md", tags=["MDDocuments"])

        self.file_router = file_router.FileRouter()
        super().include_router(self.file_router, prefix="/files", tags=["Files"])

        self.task_router = task_router.TaskRouter()
        super().include_router(self.task_router, prefix="/tasks", tags=["Task"])

        self.job_router = job_router.JobRouter()
        super().include_router(self.job_router, prefix="/jobs", tags=["Job"])

        self.settings_router = settings_router.SettingsRouter()
        super().include_router(
            self.settings_router, prefix="/settings", tags=["Settings"]
        )
