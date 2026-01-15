import asyncio
import os
from app.services.sync_service import SyncService

# Mock env vars if needed
os.environ["MONGO_DB_NAME"] = "yuque_db"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
# Ensure we have the token
os.environ["YUQUE_TOKEN"] = "your_token_here_if_needed_locally" 
# In docker enviroment, these are already set.

async def trigger_sync():
    print("Initializing SyncService...")
    syncer = SyncService()
    
    # We found this ID earlier: 74417182
    repo_id = 74417182 
    
    print(f"Triggering sync for Repo ID: {repo_id}")
    
    # We need repo_data to call sync_repo. 
    # Let's fetch it first or mock it if we just want to test structure sync
    # But sync_repo implementation needs upsert_repo first.
    
    # Let's try to get repo info from Yuque Client
    try:
        # YuqueClient doesn't have get_repo_detail, use raw _get
        response = await syncer.client._get(f"/repos/{repo_id}")
        repo_detail = response.get('data')
        
        if not repo_detail:
             raise Exception("Repo detail is empty")

        print(f"Fetched Repo Detail: {repo_detail.get('name')}")
        
        await syncer.sync_repo(repo_detail)
        print("Sync completed successfully.")
        
    except Exception as e:
        print(f"Sync failed: {e}")
    finally:
        await syncer.client.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(trigger_sync())
