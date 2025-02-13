import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from leettools.common import exceptions
from leettools.common.logging import get_logger
from leettools.common.utils import time_utils
from leettools.context_manager import Context
from leettools.core.consts.docsink_status import DocSinkStatus
from leettools.core.consts.docsource_status import DocSourceStatus
from leettools.core.consts.document_status import DocumentStatus
from leettools.core.consts.schedule_type import ScheduleType
from leettools.core.schemas.docsink import DocSink
from leettools.core.schemas.docsource import DocSource
from leettools.core.schemas.document import Document
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.schedule_config import ScheduleConfig
from leettools.eds.scheduler.schemas.program import (
    ConnectorProgramSpec,
    ConvertProgramSpec,
    EmbedProgramSpec,
    ProgramSpec,
    ProgramType,
    SplitProgramSpec,
)
from leettools.eds.scheduler.schemas.task import Task, TaskCreate, TaskStatus
from leettools.eds.scheduler.task_scanner import AbstractTaskScanner


def _get_docsource_log_sig(docsource: DocSource) -> str:
    return f"{docsource.docsource_uuid} [{docsource.display_name}]"


class TaskScannerKB(AbstractTaskScanner):
    """
    Check the DocSource / DocSink / Document stores for new tasks.
    """

    def __init__(self, context: Context):

        self.logger = get_logger(name="scheduler")

        self.repo_manager = context.get_repo_manager()
        self.task_manager = context.get_task_manager()
        self.taskstore = self.task_manager.get_taskstore()
        self.jobstore = self.task_manager.get_jobstore()
        self.org_manager = context.get_org_manager()
        self.kb_manager = context.get_kb_manager()
        self.docsource_store = self.repo_manager.get_docsource_store()
        self.docsink_store = self.repo_manager.get_docsink_store()
        self.document_store = self.repo_manager.get_document_store()
        self.segment_store = self.repo_manager.get_segment_store()

        # the keys are the org_id, kb_id, docsource_id, and the values are the last scan time
        self.last_scan_time: Dict[str, Dict[str, Dict[str, datetime]]] = {}

        self.docsource_retry_range_in_hours = (
            context.settings.DOCSOURCE_RETRY_RANGE_IN_HOURS
        )
        if (
            self.docsource_retry_range_in_hours is None
            or self.docsource_retry_range_in_hours < 1
        ):
            self.docsource_retry_range_in_hours = 24

    def _update_docsource_status(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> DocSourceStatus:
        tasks = self.taskstore.get_tasks_for_docsource(docsource.docsource_uuid)

        task_counts: Dict[TaskStatus, int] = {}
        total_tasks_count = 0
        for task_status in TaskStatus:
            task_counts[task_status] = 0

        for task in tasks:
            task_counts[task.task_status] += 1
            total_tasks_count += 1

        if task_counts[TaskStatus.COMPLETED] == total_tasks_count:
            docsource.docsource_status = DocSourceStatus.COMPLETED
        else:
            if (
                task_counts[TaskStatus.CREATED] > 0
                or task_counts[TaskStatus.PAUSED] > 0
                or task_counts[TaskStatus.RUNNING] > 0
                or task_counts[TaskStatus.PENDING] > 0
            ):
                docsource.docsource_status = DocSourceStatus.PROCESSING
            else:
                if task_counts[TaskStatus.COMPLETED] > 0:
                    docsource.docsource_status = DocSourceStatus.PARTIAL
                else:
                    docsource.docsource_status = DocSourceStatus.FAILED
        self.docsource_store.update_docsource(org, kb, docsource)
        return docsource.docsource_status

    def _update_docsink_status(
        self, org: Org, kb: KnowledgeBase, docsink: DocSink
    ) -> None:
        tasks = self.taskstore.get_tasks_for_docsink(docsink.docsink_uuid)
        docsink_completed = True
        for task in tasks:
            if task.task_status != TaskStatus.COMPLETED:
                docsink_completed = False
                break
        docsink_update = docsink
        if docsink_completed:
            docsink_update.docsink_status = DocSinkStatus.COMPLETED
        else:
            docsink_update.docsink_status = DocSinkStatus.PROCESSING
        self.docsink_store.update_docsink(org, kb, docsink_update)

    def _update_document_status(
        self, org: Org, kb: KnowledgeBase, doc: Document, task_type: ProgramType
    ) -> None:
        tasks = self.taskstore.get_tasks_for_document(doc.document_uuid)
        task_completed = True
        for task in tasks:
            if (
                task_type == ProgramType.SPLIT
                and task.program_spec.program_type == ProgramType.SPLIT
                and task.task_status != TaskStatus.COMPLETED
            ):
                task_completed = False
                break
            if (
                task_type == ProgramType.EMBED
                and task.program_spec.program_type == ProgramType.EMBED
                and task.task_status != TaskStatus.COMPLETED
            ):
                task_completed = False
                break
        document_update = doc
        if task_completed:
            if task_type == ProgramType.SPLIT:
                document_update.split_status = DocumentStatus.COMPLETED
            if task_type == ProgramType.EMBED:
                document_update.embed_status = DocumentStatus.COMPLETED
        else:
            if task_type == ProgramType.SPLIT:
                document_update.split_status = DocumentStatus.PROCESSING
            if task_type == ProgramType.EMBED:
                document_update.embed_status = DocumentStatus.PROCESSING
        self.document_store.update_document(org, kb, document_update)

    def _process_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[Task]:
        dssig = _get_docsource_log_sig(docsource)

        new_doc_source_tasks = self._add_tasks_for_docsource(org, kb, docsource)

        if new_doc_source_tasks:
            self.logger.debug(
                f"Found new doc source tasks {len(new_doc_source_tasks)}: {dssig}"
            )
        else:
            self.logger.debug(f"No new doc source tasks: {dssig}")

        new_docsink_tasks = []
        docsinks = self.docsink_store.get_docsinks_for_docsource(org, kb, docsource)
        for docsink in docsinks:
            new_tasks = self._add_tasks_for_docsink(org, kb, docsource, docsink)
            if new_tasks:
                new_docsink_tasks += new_tasks
                docsink.docsink_status = DocSinkStatus.PROCESSING
                self.docsink_store.update_docsink(org, kb, docsink)
            else:
                if docsink.docsink_status != DocSinkStatus.COMPLETED:
                    self._update_docsink_status(org, kb, docsink)

        if new_docsink_tasks:
            self.logger.debug(
                f"Found new docsink tasks {len(new_docsink_tasks)}: {dssig}"
            )
        else:
            self.logger.debug(f"No new docsink tasks: {dssig}")

        new_split_tasks = []
        documents = self.document_store.get_documents_for_docsource(org, kb, docsource)
        for doc in documents:
            new_tasks = self._add_tasks_for_document(
                org, kb, docsource, doc, ProgramType.SPLIT
            )
            if new_tasks:
                new_split_tasks += new_tasks
            if doc.split_status != DocumentStatus.COMPLETED:
                self._update_document_status(org, kb, doc, ProgramType.SPLIT)

        if new_split_tasks:
            self.logger.debug(f"Found new split tasks {len(new_split_tasks)}: {dssig}")
        else:
            self.logger.debug(f"No new split tasks: {dssig}")

        new_embed_tasks = []
        for doc in documents:
            # we only add the embed task if the split task is completed
            if doc.split_status == DocumentStatus.COMPLETED:
                new_tasks = self._add_tasks_for_document(
                    org, kb, docsource, doc, ProgramType.EMBED
                )
                if new_tasks:
                    new_embed_tasks += new_tasks
                if doc.embed_status != DocumentStatus.COMPLETED:
                    self._update_document_status(org, kb, doc, ProgramType.EMBED)

        if new_embed_tasks:
            self.logger.debug(f"Found new embed tasks {len(new_embed_tasks)}: {dssig}")
        else:
            self.logger.debug(f"No new embed tasks: {dssig}")

        all_new_tasks = (
            new_doc_source_tasks + new_docsink_tasks + new_split_tasks + new_embed_tasks
        )
        return all_new_tasks

    def _add_tasks_for_docsource(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource
    ) -> List[Task]:
        new_tasks = []

        if docsource.schedule_config is not None:
            if docsource.schedule_config.schedule_type == ScheduleType.MANUAL:
                self.logger.debug(
                    f"Docsource {docsource.docsource_uuid} is set to manual run."
                )
                return []

        program_dict: Dict[ProgramType, ProgramSpec] = {}

        program_dict[ProgramType.CONNECTOR] = ProgramSpec(
            program_type=ProgramType.CONNECTOR,
            real_program_spec=ConnectorProgramSpec(
                org_id=org.org_id, kb_id=kb.kb_id, source=docsource
            ),
        )

        current_tasks = self.taskstore.get_tasks_for_docsource(docsource.docsource_uuid)

        for program_type, program_spec in program_dict.items():

            task = None
            for t in current_tasks:
                if t.program_spec.program_type == program_type:
                    task = t
                    break

            # right now we only support simple run-to-finsh schedule
            if task is None:
                task_create = TaskCreate(
                    org_id=org.org_id,
                    kb_id=kb.kb_id,
                    docsource_uuid=docsource.docsource_uuid,
                    program_spec=program_spec,
                )
                self.logger.info(
                    f"Adding task for docsource {docsource.docsource_uuid} with type {program_type}."
                )
                task = self.taskstore.create_task(task_create)
                new_tasks.append(task)
            else:
                if (
                    task.task_status != TaskStatus.COMPLETED
                    and task.task_status != TaskStatus.ABORTED
                ):
                    new_tasks.append(task)
        return new_tasks

    def _add_tasks_for_docsink(
        self, org: Org, kb: KnowledgeBase, docsource: DocSource, docsink: DocSink
    ) -> List[Task]:
        new_tasks = []
        program_dict: Dict[ProgramType, ProgramSpec] = {}

        program_dict[ProgramType.CONVERT] = ProgramSpec(
            program_type=ProgramType.CONVERT,
            real_program_spec=ConvertProgramSpec(
                org_id=org.org_id, kb_id=kb.kb_id, source=docsink
            ),
        )

        current_tasks = self.taskstore.get_tasks_for_docsink(docsink.docsink_uuid)

        for program_type, program_spec in program_dict.items():
            task = None
            for t in current_tasks:
                if t.program_spec.program_type == program_type:
                    task = t
                    break
            if task is None:
                task_create = TaskCreate(
                    org_id=org.org_id,
                    kb_id=kb.kb_id,
                    docsource_uuid=docsource.docsource_uuid,
                    docsink_uuid=docsink.docsink_uuid,
                    program_spec=program_spec,
                )
                self.logger.info(
                    f"Adding task for docsink {docsink.docsink_uuid} with type {program_type}."
                )
                task = self.taskstore.create_task(task_create)
                new_tasks.append(task)
            else:
                if (
                    task.task_status != TaskStatus.COMPLETED
                    and task.task_status != TaskStatus.ABORTED
                ):
                    new_tasks.append(task)
        return new_tasks

    def _add_tasks_for_document(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        doc: Document,
        task_type: ProgramType,
    ) -> List[Task]:
        try:
            new_tasks = self._helper_add_tasks_for_document(
                org, kb, docsource, doc, task_type
            )
        except exceptions.UnrecoverableOperationException as e:
            self.logger.error(f"Unrecoverable operation failure for {doc.doc_uri}: {e}")
            if task_type == ProgramType.SPLIT:
                doc.split_status = DocumentStatus.FAILED
            if task_type == ProgramType.EMBED:
                doc.embed_status = DocumentStatus.FAILED
            self.document_store.update_document(org, kb, doc)
            new_tasks = []
        except Exception as e:
            self.logger.error(
                f"Error adding tasks for document {doc.doc_uri} "
                f"for docsource {docsource.docsource_uuid}: {e}"
            )
            new_tasks = []
        return new_tasks

    def _helper_add_tasks_for_document(
        self,
        org: Org,
        kb: KnowledgeBase,
        docsource: DocSource,
        doc: Document,
        task_type: ProgramType,
    ) -> List[Task]:
        new_tasks = []

        program_dict: Dict[ProgramType, ProgramSpec] = {}

        if task_type == ProgramType.SPLIT:
            program_dict[ProgramType.SPLIT] = ProgramSpec(
                program_type=ProgramType.SPLIT,
                real_program_spec=SplitProgramSpec(
                    org_id=org.org_id, kb_id=kb.kb_id, source=doc
                ),
            )

        # TODO: the problem is that we do not have the user information
        # in the document object (the task itself does not have the configs).
        # Ideally we should use a set of API-providers
        # in the orgnization object for the task specified for that org. Right
        # now we just use the system-default API-provider settings for the task.
        if task_type == ProgramType.EMBED:
            segments = self.segment_store.get_all_segments_for_document(
                org, kb, doc.document_uuid
            )
            program_dict[ProgramType.EMBED] = ProgramSpec(
                program_type=ProgramType.EMBED,
                real_program_spec=EmbedProgramSpec(
                    org_id=org.org_id, kb_id=kb.kb_id, source=segments
                ),
            )

        current_tasks = self.taskstore.get_tasks_for_document(doc.document_uuid)

        for program_type, program_spec in program_dict.items():
            task = None
            for t in current_tasks:
                if t.program_spec.program_type == program_type:
                    task = t
                    break

            if task is None:
                task_create = TaskCreate(
                    org_id=org.org_id,
                    kb_id=kb.kb_id,
                    docsource_uuid=docsource.docsource_uuid,
                    docsink_uuid=doc.docsink_uuid,
                    document_uuid=doc.document_uuid,
                    program_spec=program_spec,
                )
                self.logger.info(
                    f"Adding new task for document {doc.document_uuid} with type {program_type}."
                )
                task = self.taskstore.create_task(task_create)
                new_tasks.append(task)
            else:
                if (
                    task.task_status != TaskStatus.COMPLETED
                    and task.task_status != TaskStatus.ABORTED
                ):
                    self.logger.info(
                        f"Adding unfinished {program_type} task {task.task_uuid} for "
                        f"document {doc.document_uuid}, status: {task.task_status}."
                    )
                    new_tasks.append(task)
                else:
                    self.logger.debug(
                        f"Found completed {program_type} task {task.task_uuid} for "
                        f"document {doc.document_uuid}, status: {task.task_status}."
                    )
        return new_tasks

    def scan_kb_for_tasks(
        self,
        target_org: Optional[Org] = None,
        target_kb: Optional[KnowledgeBase] = None,
        target_docsources: Optional[List[DocSource]] = None,
    ) -> List[Task]:
        start_time = time.perf_counter()
        cur_tasks: Dict[str, Dict[str, Dict[str, List[Task]]]] = {}

        if target_docsources is not None:
            target_docsource_uuids: Set[str] = set()
            for ds in target_docsources:
                target_docsource_uuids.add(ds.docsource_uuid)
        else:
            target_docsource_uuids = None

        for cur_task in self.taskstore.get_incomplete_tasks():
            if target_org is not None and cur_task.org_id != target_org.org_id:
                continue
            if target_kb is not None and cur_task.kb_id != target_kb.kb_id:
                continue
            if (
                target_docsource_uuids is not None
                and cur_task.docsource_uuid not in target_docsource_uuids
            ):
                continue

            if cur_tasks.get(cur_task.org_id) is None:
                cur_tasks[cur_task.org_id] = {}
            if cur_tasks[cur_task.org_id].get(cur_task.kb_id) is None:
                cur_tasks[cur_task.org_id][cur_task.kb_id] = {}
            if (
                cur_tasks[cur_task.org_id][cur_task.kb_id].get(cur_task.docsource_uuid)
                is None
            ):
                cur_tasks[cur_task.org_id][cur_task.kb_id][cur_task.docsource_uuid] = []

            cur_tasks[cur_task.org_id][cur_task.kb_id][cur_task.docsource_uuid].append(
                cur_task
            )

        def _docsource_in_cur_tasks(
            org: Org, kb: KnowledgeBase, docsource: DocSource
        ) -> bool:
            return (
                cur_tasks.get(org.org_id) is not None
                and cur_tasks[org.org_id].get(kb.kb_id) is not None
                and cur_tasks[org.org_id][kb.kb_id].get(docsource.docsource_uuid)
                is not None
            )

        new_tasks = []
        orgs = self.org_manager.list_orgs()
        current_time = time_utils.current_datetime()
        docsource_retry_range = timedelta(hours=self.docsource_retry_range_in_hours)

        for org in orgs:
            if target_org is not None and org.org_id != target_org.org_id:
                continue

            if self.last_scan_time.get(org.org_id) is None:
                self.last_scan_time[org.org_id] = {}
            # adhoc KBs will not be in the scheduler since no retry will be performed
            kbs = self.kb_manager.get_all_kbs_for_org(org=org, list_adhoc=True)
            for kb in kbs:
                if target_kb is not None and kb.kb_id != target_kb.kb_id:
                    continue

                if kb.auto_schedule is False:
                    continue
                if self.last_scan_time[org.org_id].get(kb.kb_id) is None:
                    self.last_scan_time[org.org_id][kb.kb_id] = {}
                docsources = self.docsource_store.get_docsources_for_kb(org, kb)
                for docsource in docsources:
                    if (
                        target_docsource_uuids is not None
                        and docsource.docsource_uuid not in target_docsource_uuids
                    ):
                        continue
                    schedule_config = docsource.schedule_config
                    dssig = _get_docsource_log_sig(docsource)

                    if schedule_config is None:
                        schedule_config = ScheduleConfig(
                            scheduler_type=ScheduleType.ONCE,
                        )
                        # if no schedule config, we only scan the docsource if it is not
                        # older than the retry range
                        if current_time - docsource.updated_at > docsource_retry_range:
                            self.logger.noop(
                                f"Docsource is older than "
                                f"{self.docsource_retry_range_in_hours} hours: {dssig}",
                                noop_lvl=1,
                            )
                            continue
                    else:
                        if schedule_config.schedule_type == ScheduleType.MANUAL:
                            self.logger.noop(
                                f"Docsource is set to manual run: {dssig}", noop_lvl=2
                            )
                            continue

                    def _need_to_check_docsource() -> bool:

                        if schedule_config.schedule_type == ScheduleType.RECURRING:
                            self.logger.debug(
                                f"Found recurring docsource to be scanned: {dssig}"
                            )
                            return True
                        elif schedule_config.schedule_type == ScheduleType.MANUAL:
                            self.logger.debug(
                                f"Found manual docsource to be ignored: {dssig}"
                            )
                            return False

                        # now we deal with run-to-finish docsources
                        if not docsource.is_finished():
                            self.logger.debug(
                                f"Docsource is not finished [{docsource.docsource_status}]: {dssig}"
                            )
                            return True

                        # now the docsource is finished
                        if _docsource_in_cur_tasks(org, kb, docsource):
                            self.logger.debug(
                                f"Found finished docsource with unfinished tasks: {dssig}"
                            )
                            return True
                        else:
                            self.logger.noop(
                                f"Ignore finished docsource with no unfinished tasks: {dssig}",
                                noop_lvl=1,
                            )
                        return False

                    if _need_to_check_docsource() == False:
                        self.logger.noop(
                            f"No need to check the docsource: {dssig}", noop_lvl=1
                        )
                        continue

                    try:
                        all_new_tasks = self._process_docsource(org, kb, docsource)
                        self.logger.debug(
                            f"{len(all_new_tasks)} new tasks for docsource: {dssig}"
                        )
                        if len(all_new_tasks) > 0:
                            new_tasks += all_new_tasks
                            docsource.docsource_status = DocSourceStatus.PROCESSING
                            self.docsource_store.update_docsource(org, kb, docsource)
                        else:
                            if not docsource.is_finished():
                                self._update_docsource_status(org, kb, docsource)
                            else:
                                self.logger.debug(
                                    f"DocSource is already marked as {docsource.docsource_status}: {dssig}"
                                )
                        # last_scan_time is intended to compare the updated_at time of the docsource
                        # but right now the updated_at time is not updated when the status is changed
                        # so last_scan_time is not used currently.
                        self.last_scan_time[org.org_id][kb.kb_id][
                            docsource.docsource_uuid
                        ] = time_utils.current_datetime()
                    except Exception as e:
                        self.logger.error(
                            f"Error processing docsource for tasks {docsource.uri}: {e}"
                        )
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        self.logger.debug(f"Task scanning took {elapsed_time:.6f} seconds.")
        return new_tasks
