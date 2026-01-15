import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.schemas import User, Repo, Doc, Member, Comment, ChatSession, ChatMessage, Activity
from beanie import init_beanie
import pymongo

async def fix_duplicate_members():
    print(">>> Checking for duplicate members...")
    db = Member.get_pymongo_collection()
    
    # 查找所有重复的 yuque_id
    pipeline = [
        {"$group": {"_id": "$yuque_id", "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    duplicates = await db.aggregate(pipeline).to_list(None)
    
    if not duplicates:
        print("No duplicate members found.")
        return

    print(f"Found {len(duplicates)} duplicate sets.")
    
    for item in duplicates:
        yuque_id = item["_id"]
        ids = item["ids"]
        print(f"Fixing duplicates for yuque_id {yuque_id}, found {len(ids)} copies.")
        
        # 保留 id 最大的（通常是最后插入的，或者也可以按 updated_at 排序）
        # 这里我们按 _id 排序，保留最后一个
        ids.sort()
        to_delete = ids[:-1]
        
        result = await db.delete_many({"_id": {"$in": to_delete}})
        print(f"Deleted {result.deleted_count} duplicate records.")

async def fix_doc_repo_ids():
    print("\n>>> Checking Doc repo_id types...")
    # UpdateMany with aggregation pipeline is only supported in MongoDB 4.2+
    # Here we iterate and update for safety and compatibility
    
    count = 0
    async for doc in Doc.find(Doc.repo_id != None):
        if not isinstance(doc.repo_id, int):
            try:
                fixed_id = int(doc.repo_id)
                doc.repo_id = fixed_id
                await doc.save()
                count += 1
            except Exception as e:
                print(f"Failed to convert repo_id {doc.repo_id} for doc {doc.uuid}: {e}")
                
    if count > 0:
        print(f"Fixed {count} documents with non-int repo_id.")
    else:
        print("All documents have valid integer repo_ids.")

async def main():
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=[User, Repo, Doc, Member, Comment, ChatSession, ChatMessage, Activity],
        allow_index_dropping=True
    )
    print("Connected.")

    await fix_duplicate_members()
    await fix_doc_repo_ids()
    
    print("\n>>> DB Fix Complete.")

if __name__ == "__main__":
    asyncio.run(main())
