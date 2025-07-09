import asyncio
import json
import sys
import argparse
from typing import Any, List, Dict

from duksu_exec.controller import run_workflow_with_history
from .workflows.create_news_feed import execute_news_feed_workflow
from .workflows.populate_feed import execute_populate_feed_workflow
from .storage.db import get_db, get_db_session
from .storage.model import User, NewsFeed


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
    
    populate_all_feeds_parser = subparsers.add_parser("populate-all-feeds", help="Populate all feeds in the database with latest articles")
    
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


async def populate_all_feeds() -> dict:
    """Populate all feeds in the database with latest articles."""
    # Get all feeds from database
    db = get_db()
    all_feeds = db.query(NewsFeed).all()
    response = {
        "total_feeds": 0,
        "successful_feeds": [],
        "failed_feeds": [],
        "error_message": None
    }
        
    if not all_feeds:
        response["error_message"] = "No feeds found in database"
        return response
    
    print(f"Found {len(all_feeds)} feeds to populate")
    
    successful_feeds: List[Dict[str, Any]] = []
    failed_feeds: List[Dict[str, Any]] = []
    
    # Process each feed
    for feed in all_feeds:
        feed_id = feed.id
        feed_info = {
            "feed_id": feed_id,
            "feed_query_prompt": feed.query_prompt,
        }
        
        try:
            print(f"Populating feed ID {feed_id}")
            
            result = await execute_populate_feed_workflow(feed.id) # type: ignore
            
            if result.get("error_message") is None:
                feed_info["result"] = result
                successful_feeds.append(feed_info)
                print(f"✅ Successfully populated feed ID {feed_id}")
            else:
                feed_info["error"] = result.get("error_message")
                failed_feeds.append(feed_info)
                print(f"❌ Failed to populate feed ID {feed_id}: {result.get('error_message')}")
                
        except Exception as e:
            feed_info["error"] = str(e)
            failed_feeds.append(feed_info)
            print(f"❌ Exception while populating feed ID {feed_id}: {str(e)}")
            continue
    
    if successful_feeds:
        print(f"\n✅ Successful feeds:")
        for feed in successful_feeds:
            print(f"  - Feed ID {feed['feed_id']}")
    
    if failed_feeds:
        print(f"\n❌ Failed feeds:")
        for feed in failed_feeds:
            print(f"  - Feed ID {feed['feed_id']} - Error: {feed['error']}")
    
    response["total_feeds"] = len(all_feeds)
    response["successful_feeds"] = successful_feeds
    response["failed_feeds"] = failed_feeds
    response["error_message"] = None if len(failed_feeds) == 0 else f"{len(failed_feeds)} feeds failed to populate"
    
    return response


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
    
    elif args.command == "populate-all-feeds":
        input_data = {}
        
        asyncio.run(run_workflow_with_history(
            command_name="populate-all-feeds",
            input_data=input_data,
            workflow_func=lambda: populate_all_feeds(),
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
