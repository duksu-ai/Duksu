import asyncio
import json
import sys
import argparse
from datetime import datetime
from typing import Any, Callable
from .workflows.create_news_feed import execute_news_feed_workflow
from .workflows.populate_feed import execute_populate_feed_workflow
from .storage.db import get_db, get_db_session
from .storage.model import WorkflowRunHistory, User
from .storage.enums import WorkflowRunStatus


def setup_argparser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Duksu CLI for news feed workflows")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    add_user_parser = subparsers.add_parser("add-user", help="Add a new user")
    add_user_parser.add_argument("--user_id", help="User ID to add")

    create_news_feed_parser = subparsers.add_parser("create-news-feed", help="Create news feed workflow")
    create_news_feed_parser.add_argument("--user_id", help="User ID")
    create_news_feed_parser.add_argument("--query_prompt", help="Query prompt for news search")
    
    populate_feed_parser = subparsers.add_parser("populate-feed", help="Populate existing feed with latest articles")
    populate_feed_parser.add_argument("--feed_id", type=int, help="Feed ID to populate")
    
    return parser


async def add_user(user_id: str) -> dict:
    """Add a new user to the database."""
    try:
        # Check if user already exists
        db = get_db()
        existing_user = db.query(User).filter(User.user_id == user_id).first()
        if existing_user:
            return {
                "error_message": f"User with ID '{user_id}' already exists",
                "user_id": user_id
            }
        
        # Create new user
        new_user = User(user_id=user_id)
        db.add(new_user)
        db.flush()
        
        return {
            "user_id": user_id,
            "message": f"User '{user_id}' created successfully",
            "error_message": None
        }
            
    except Exception as e:
        return {
            "error_message": f"Failed to create user: {str(e)}",
            "user_id": user_id
        }
        

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
        
            print(f"Started workflow run ID: {run_id}")
 
            result = await workflow_func()
            run_status = WorkflowRunStatus.COMPLETED if result.get("error_message") is None else WorkflowRunStatus.FAILED
     
            workflow_run = session.query(WorkflowRunHistory).filter(
                WorkflowRunHistory.id == run_id
            ).first()
            if workflow_run:
                workflow_run.status = run_status # type: ignore
                workflow_run.output_data = json.dumps(result, default=str) # type: ignore
                workflow_run.completed_at = datetime.now() # type: ignore
        
            print("Workflow result:")
            print(json.dumps(result, indent=2, default=str))
            print(f"Workflow completed with status: {run_status.value}")

            return result
                
    except Exception as e:
        # Update workflow run history with error status
        print(f"❌ Unexpected error: {e}")
        if run_id is not None:
            try:
                with get_db_session() as session:
                    workflow_run = session.query(WorkflowRunHistory).filter(
                        WorkflowRunHistory.id == run_id
                    ).first()
                    if workflow_run:
                        workflow_run.status = WorkflowRunStatus.ERROR # type: ignore
                        workflow_run.output_data = json.dumps({"error_message": str(e)}, default=str) # type: ignore
                        workflow_run.completed_at = datetime.now() # type: ignore
            except Exception as db_error:
                print(f"❌ Failed to update workflow history: {db_error}")
        
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
        ))
    
    elif args.command == "populate-feed":
        input_data = {"feed_id": args.feed_id}
        
        asyncio.run(run_workflow_with_history(
            command_name="populate-feed",
            input_data=input_data,
            workflow_func=lambda: execute_populate_feed_workflow(args.feed_id),
        ))
    
    elif args.command == "add-user":
        print(args)
        input_data = {"user_id": args.user_id}
        
        asyncio.run(run_workflow_with_history(
            command_name="add-user",
            input_data=input_data,
            workflow_func=lambda: add_user(args.user_id),
        ))
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
