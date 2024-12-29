from typing import Optional

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.logging.event_logger import EventLogger
from leettools.context_manager import Context
from leettools.core.consts.docsource_type import DocSourceType
from leettools.core.consts.return_code import ReturnCode
from leettools.core.schemas.user import User
from leettools.eds.pipeline.convert.converter import create_converter
from leettools.eds.pipeline.embed.segment_embedder import create_segment_embedder_for_kb
from leettools.eds.pipeline.ingest.connector import create_connector
from leettools.eds.pipeline.split.splitter import Splitter
from leettools.eds.scheduler.schemas.job import Job
from leettools.eds.scheduler.schemas.job_status import JobStatus
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ConvertProgramSpec,
    EmbedProgramSpec,
    ProgramType,
    SplitProgramSpec,
)
from leettools.eds.scheduler.task_runner import AbstractTaskRunner


class TaskRunnerEDS(AbstractTaskRunner):
    """
    The Executor is responsible for running a task and updating the job.
    """

    def __init__(self, context: Context, display_logger: Optional[EventLogger] = None):
        self.context = context
        self.repo_manager = context.get_repo_manager()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.user_store = context.get_user_store()

        self.docsinkstore = self.repo_manager.get_docsink_store()
        self.docstore = self.repo_manager.get_document_store()
        self.segstore = self.repo_manager.get_segment_store()
        self.graphstore = self.repo_manager.get_docgraph_store()

        self.jobstore = context.get_task_manager().get_jobstore()
        self.settings = context.settings

        if display_logger is None:
            self.display_logger = logger()
        else:
            self.display_logger = display_logger

    def _run_converter(
        self, convert_program: ConvertProgramSpec, job: Job
    ) -> ReturnCode:
        """
        Run the file convert program.
        """
        self.display_logger.info("Executor: converting documents to markdown")

        org = self.org_manager.get_org_by_id(convert_program.org_id)
        kb = self.kb_manager.get_kb_by_id(org, convert_program.kb_id)

        converter = create_converter(
            org=org,
            kb=kb,
            docsink=convert_program.source,
            docstore=self.docstore,
            settings=self.settings,
        )
        converter.set_log_location(job.log_location)
        rtn_code = converter.convert()
        if rtn_code == ReturnCode.SUCCESS:
            self.display_logger.info("Executor: converted document to markdown")
        else:
            self.display_logger.error(
                f"Executor: failed to convert document to markdown {rtn_code}"
            )
        return rtn_code

    def _run_connector(
        self, connector_program: ConnectorProgramSpec, job: Job
    ) -> ReturnCode:
        self.display_logger.info(
            f"Executor: Ingest docsource {connector_program.source.docsource_uuid} to docsinks"
        )

        org = self.org_manager.get_org_by_id(connector_program.org_id)
        kb = self.kb_manager.get_kb_by_id(org, connector_program.kb_id)

        source_type = connector_program.source.source_type
        if source_type == DocSourceType.NOTION:
            connector = create_connector(
                context=self.context,
                connector="connector_notion",
                org=org,
                kb=kb,
                docsource=connector_program.source,
                docsinkstore=self.docsinkstore,
                display_logger=self.display_logger,
            )
        else:
            # TODO: add support for other source types, right now SIMPLE handles
            # all other source types: LOCAL, FILE, URL, WEB, Search, etc
            connector = create_connector(
                context=self.context,
                connector="connector_simple",
                org=org,
                kb=kb,
                docsource=connector_program.source,
                docsinkstore=self.docsinkstore,
                display_logger=self.display_logger,
            )
        connector.set_log_location(job.log_location)
        rnt_code = connector.ingest()
        if rnt_code == ReturnCode.SUCCESS:
            self.display_logger.info("Executor: ingested docsource to docsinks")
        else:
            self.display_logger.error(
                f"Executor: failed to ingest docsource to docsinks, return code: {rnt_code}"
            )
        return rnt_code

    def _run_embedder(self, embed_program: EmbedProgramSpec, job: Job) -> ReturnCode:
        """
        Run the file convert program.
        """
        self.display_logger.debug("Executor: embed segments to vectorstore")

        org = self.org_manager.get_org_by_id(embed_program.org_id)
        kb = self.kb_manager.get_kb_by_id(org, embed_program.kb_id)

        user_uuid = kb.user_uuid
        if user_uuid is None:
            user = User.get_admin_user()
        else:
            user = self.user_store.get_user_by_uuid(user_uuid)
            if user is None:
                user = User.get_admin_user()

        embedder = create_segment_embedder_for_kb(
            org=org, kb=kb, user=user, context=self.context
        )

        job_logger = logger()
        log_handler = None
        if job.log_location:
            log_handler = job_logger.log_to_file(job.log_location)

        try:
            rtn_code = embedder.embed_segment_list(
                segments=embed_program.source, display_logger=job_logger
            )
            if rtn_code == ReturnCode.SUCCESS:
                self.display_logger.info(
                    "Executor: embed segments to vectorstore successfully"
                )
            else:
                self.display_logger.error(
                    f"Executor: failed to embed segments to vectorstore. {rtn_code}"
                )
            return rtn_code
        finally:
            if log_handler:
                job_logger.remove_file_handler()

    def _run_splitter(self, split_program: SplitProgramSpec, job: Job) -> ReturnCode:
        """
        Run the md load program.
        """
        self.display_logger.info("Executor: split documents to segments")

        org = self.org_manager.get_org_by_id(split_program.org_id)
        kb = self.kb_manager.get_kb_by_id(org, split_program.kb_id)

        document = split_program.source
        splitter = Splitter(context=self.context, org=org, kb=kb)
        rnt_code = splitter.split(doc=document, log_file_location=job.log_location)
        if rnt_code == ReturnCode.SUCCESS:
            self.display_logger.info(
                "Executor: split documents to segments successfully"
            )
        else:
            self.display_logger.error(
                f"Executor: failed to split documents to segments, return code: {rnt_code}."
            )
        return rnt_code

    def run_job(self, job: Job) -> Job:

        job.job_status = JobStatus.RUNNING
        job = self.jobstore.update_job_status(job.job_uuid, job.job_status)

        program_spec = job.program_spec
        if program_spec.program_type == ProgramType.CONVERT:
            convert_program = ConvertProgramSpec.model_validate(
                program_spec.real_program_spec
            )
            rnt_code = self._run_converter(convert_program, job)
        elif program_spec.program_type == ProgramType.CONNECTOR:
            connector_program = ConnectorProgramSpec.model_validate(
                program_spec.real_program_spec
            )
            rnt_code = self._run_connector(connector_program, job)
        elif program_spec.program_type == ProgramType.EMBED:
            embedder_program = EmbedProgramSpec.model_validate(
                program_spec.real_program_spec
            )
            rnt_code = self._run_embedder(embedder_program, job)
        elif program_spec.program_type == ProgramType.SPLIT:
            split_program = SplitProgramSpec.model_validate(
                program_spec.real_program_spec
            )
            rnt_code = self._run_splitter(split_program, job)
        else:
            raise exceptions.UnexpectedCaseException(
                f"Executor: unknown program type: {program_spec.program_type}"
            )

        if rnt_code == ReturnCode.SUCCESS:
            job.job_status = JobStatus.COMPLETED
        elif rnt_code == ReturnCode.FAILURE:
            job.job_status = JobStatus.FAILED
        elif rnt_code == ReturnCode.FAILURE_RETRY:
            job.job_status = JobStatus.FAILED
        elif rnt_code == ReturnCode.FAILURE_ABORT:
            job.job_status = JobStatus.ABORTED
        else:
            raise exceptions.UnexpectedCaseException(
                f"Executor: unknown return code: {rnt_code}"
            )

        return self.jobstore.update_job_status(job.job_uuid, job.job_status)
