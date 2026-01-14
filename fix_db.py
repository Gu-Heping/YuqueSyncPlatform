import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import pymongo

async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db["members"]
    
    print(f"Connected to {settings.MONGO_DB_NAME}.members")
    
    # 1. Dedup Member Documents
    cursor = collection.find({})
    members = await cursor.to_list(length=10000)
    
    yuque_ids = {}
    for m in members:
        yid = m.get("yuque_id")
        if yid is None: continue
        if yid in yuque_ids:
            yuque_ids[yid].append(m)
        else:
            yuque_ids[yid] = [m]
            
    duplicates = {k: v for k, v in yuque_ids.items() if len(v) > 1}
    
    print(f"Found {len(duplicates)} duplicate groups.")
    
    for yid, docs in duplicates.items():
        print(f"Fixing duplicates for Yuque ID {yid}...")
        # Sort by updated_at desc, keep the first one
        docs.sort(key=lambda x: x.get("updated_at") or x.get("_id").generation_time, reverse=True)
        keep = docs[0]
        to_delete = docs[1:]
        
        for d in to_delete:
            print(f"  Deleting duplicate doc {d['_id']} (Name: {d.get('name')})")
            await collection.delete_one({"_id": d["_id"]})
            
    # 2. Dedup Followers list in each document
    print("Deduplicating followers lists...")
    async for m in collection.find({}):
        followers = m.get("followers")
        if followers:
            unique_followers = list(set(followers))
            if len(unique_followers) != len(followers):
                print(f"  Fixing followers for {m.get('name')} ({len(followers)} -> {len(unique_followers)})")
                await collection.update_one(
                    {"_id": m["_id"]},
                    {"$set": {"followers": unique_followers}}
                )
    
    # 3. Ensure Index
    print("Ensuring unique index on yuque_id...")
    try:
        await collection.create_index([("yuque_id", pymongo.ASCENDING)], unique=True)
        print("Index created/verified.")
    except Exception as e:
        print(f"Index creation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
