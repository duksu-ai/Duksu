import json
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session
from duksu.logging_config import logger
from duksu_exec.storage.db import get_db_session
from duksu_exec.storage.enums import WorkflowRunStatus
from duksu_exec.storage.model import WorkflowRunHistory


async def run_workflow_with_history(command_name: str, input_data: dict, workflow_func: Callable[[], Any]):
    run_id = None
    try:
        with get_db_session() as session:
            workflow_run = WorkflowRunHistory(
                workflow_name=command_name,
                input_data=json.dumps(input_data),
                status=WorkflowRunStatus.STARTED
            )
            session.add(workflow_run)
            session.flush()  # Get the ID
            run_id = workflow_run.id

            logger.info(f"Started workflow run ID: {run_id}")
    
            result = await workflow_func()
            run_status = WorkflowRunStatus.COMPLETED if result.get("error_message") is None else WorkflowRunStatus.FAILED

            workflow_run = session.query(WorkflowRunHistory).filter(
                WorkflowRunHistory.id == run_id
            ).first()
            if workflow_run:
                workflow_run.status = run_status # type: ignore
                workflow_run.output_data = json.dumps(result, default=str) # type: ignore
                workflow_run.completed_at = datetime.now() # type: ignore

            logger.info("Workflow result:")
            logger.info(json.dumps(result, indent=2, default=str))
            logger.info(f"Workflow completed with status: {run_status.value}")

            return result

    except Exception as e:
        logger.error(f"❌ Unhandled error: {e}")
        if run_id is not None:
            with get_db_session() as session:
                workflow_run = session.query(WorkflowRunHistory).filter(
                    WorkflowRunHistory.id == run_id
                ).first()
                if workflow_run:
                    workflow_run.status = WorkflowRunStatus.ERROR # type: ignore
                    workflow_run.output_data = json.dumps({"error_message": str(e)}, default=str) # type: ignore
                    workflow_run.completed_at = datetime.now() # type: ignore