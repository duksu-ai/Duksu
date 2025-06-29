import asyncio
import json
import sys
import argparse
from datetime import datetime
from typing import Any, Callable
from .workflows.create_news_feed import execute_news_feed_workflow
from .storage.db import get_db_session
from .storage.model import WorkflowRunHistory
from .storage.enums import WorkflowRunStatus


def setup_argparser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Doeksu-exec CLI for news feed workflows")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    create_news_feed_parser = subparsers.add_parser("create-news-feed", help="Create news feed workflow")
    create_news_feed_parser.add_argument("user_id", help="User ID")
    create_news_feed_parser.add_argument("query_prompt", help="Query prompt for news search")
    
    return parser


async def run_workflow_with_history(command_name: str, input_data: dict, workflow_func: Callable[[], Any], determine_status_func: Callable[[dict], WorkflowRunStatus]):
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
        
        print(f"Started workflow run ID: {run_id}")
        
        result = await workflow_func()
        
        final_status = determine_status_func(result)
        
        # Update workflow run history
        with get_db_session() as session:
            workflow_run = session.query(WorkflowRunHistory).filter(
                WorkflowRunHistory.id == run_id
            ).first()
            if workflow_run:
                workflow_run.status = final_status
                workflow_run.output_data = json.dumps(result, default=str)
                workflow_run.completed_at = datetime.now()
        
        print("Workflow result:")
        print(json.dumps(result, indent=2, default=str))
        print(f"Workflow completed with status: {final_status.value}")
        
        return result
                
    except Exception as e:
        # Update workflow run history with error status
        if run_id:
            try:
                with get_db_session() as session:
                    workflow_run = session.query(WorkflowRunHistory).filter(
                        WorkflowRunHistory.id == run_id
                    ).first()
                    if workflow_run:
                        workflow_run.status = WorkflowRunStatus.ERROR
                        workflow_run.completed_at = datetime.now()
            except Exception as db_error:
                print(f"Failed to update workflow history: {db_error}")
        
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = setup_argparser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "create-news-feed":
        input_data = {"user_id": args.user_id, "query_prompt": args.query_prompt}
        
        asyncio.run(run_workflow_with_history(
            command_name="create-news-feed",
            input_data=input_data,
            workflow_func=lambda: execute_news_feed_workflow(args.user_id, args.query_prompt),
            determine_status_func=lambda result: WorkflowRunStatus.FAILED if result.get("error_message") is not None else WorkflowRunStatus.COMPLETED
        ))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
