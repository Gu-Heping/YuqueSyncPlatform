import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    collection = db["members"]
    
    print(f"Connected to {settings.MONGO_DB_NAME}.members")
    
    cursor = collection.find({})
    members = await cursor.to_list(length=1000)
    
    print(f"Total members: {len(members)}")
    
    yuque_ids = {}
    for m in members:
        yid = m.get("yuque_id")
        name = m.get("name")
        login = m.get("login")
        followers = m.get("followers", [])
        
        print(f"ID: {yid}, Name: {name}, Login: {login}, Followers: {followers}")
        
        if yid in yuque_ids:
            print(f"!!! DUPLICATE FOUND !!! ID: {yid}, Name: {name}")
            yuque_ids[yid].append(m)
        else:
            yuque_ids[yid] = [m]

    duplicates = {k: v for k, v in yuque_ids.items() if len(v) > 1}
    
    if duplicates:
        print("\n--- Summary of Duplicates ---")
        for k, v in duplicates.items():
            print(f"Yuque ID {k}: {len(v)} occurrences")
    else:
        print("\nNo duplicates found by yuque_id.")

    # Check for duplicate followers in a single member
    print("\n--- Checking for duplicate followers ---")
    for m in members:
        followers = m.get("followers")
        if followers and len(followers) != len(set(followers)):
            print(f"Duplicate followers in member {m['name']} ({m['yuque_id']}): {followers}")

if __name__ == "__main__":
    asyncio.run(main())
