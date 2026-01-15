import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from app.api.routes import get_members
from app.models.schemas import Doc, Member, Activity

# Mock env vars if needed
os.environ["MONGO_DB_NAME"] = "yuque_db"
os.environ["MONGO_URI"] = "mongodb://mongo:27017"

async def inspect_db():
    print("Connecting to DB...")
    client = AsyncIOMotorClient("mongodb://mongo:27017")
    db = client["yuque_db"]
    
    # 1. Check Doc repo_id type
    print("\n--- Checking Doc repo_id types ---")
    sample_doc = await db.docs.find_one({})
    if sample_doc:
        print(f"Sample Doc Repo ID: {sample_doc.get('repo_id')} (Type: {type(sample_doc.get('repo_id'))})")
        print(f"Sample Doc User ID: {sample_doc.get('user_id')} (Type: {type(sample_doc.get('user_id'))})")
    else:
        print("No docs found.")

    # 2. Check Activity repo_id type
    print("\n--- Checking Activity repo_id types ---")
    sample_activity = await db.activities.find_one({})
    if sample_activity:
        print(f"Sample Activity Repo ID: {sample_activity.get('repo_id')} (Type: {type(sample_activity.get('repo_id'))})")
    else:
        print("No activities found.")

    # 2.5 Find a valid repo_id
    print("\n--- Finding valid repo_id ---")
    repo_id = 74417182 # Default fallback
    valid_doc = await db.docs.find_one({"repo_id": {"$ne": None}})
    if valid_doc:
         repo_id = valid_doc["repo_id"]
         print(f"Found Repo ID with docs: {repo_id}")
    else:
         print("No docs with repo_id found. Using default.")

    # 3. Check specific repo filtering logic (simulating get_members)
    print(f"\n--- Testing Filter Logic for Repo {repo_id} ---")
    
    # Logic from routes.py
    contributor_ids = await db.docs.distinct("user_id", {"repo_id": repo_id})
    print(f"Contributor IDs found in Docs: {len(contributor_ids)}")
    print(f"First 5 IDs: {contributor_ids[:5]}")
    
    if contributor_ids:
        # Check if Members exist with these IDs
        count = await db.users.count_documents({"yuque_id": {"$in": contributor_ids}})
        print(f"Members matching these IDs: {count}")

    # 4. Check Dashboard Overview logic basics
    print(f"\n--- Testing Dashboard Counts for Repo {repo_id} ---")
    doc_count = await db.docs.count_documents({"repo_id": repo_id})
    print(f"Docs count: {doc_count}")
    
    # 5. Check if repo actually exists in 'repos' collection
    repo_info = await db.repos.find_one({"yuque_id": repo_id})
    if repo_info:
        print(f"Repo Info: {repo_info.get('name')}")
    else:
        print("Repo info NOT found in 'repos' collection!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(inspect_db())
