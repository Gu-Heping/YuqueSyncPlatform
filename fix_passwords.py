import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models.schemas import Member
from app.core.security import get_password_hash

async def main():
    # Hardcode connection details to match docker-compose environment
    # Host is localhost because port 27017 is exposed
    mongo_uri = "mongodb://localhost:27017"
    db_name = "yuque_db" 
    
    print(f"Connecting to {mongo_uri} (DB: {db_name})...")
    client = AsyncIOMotorClient(mongo_uri)
    await init_beanie(database=client[db_name], document_models=[Member])

    users = await Member.find_all().to_list()
    print(f"Found {len(users)} users.")
    
    count = 0
    default_hash = get_password_hash("123456")
    
    for user in users:
        if not user.hashed_password:
            user.hashed_password = default_hash
            # Ensure email field exists
            if not hasattr(user, 'email') or user.email is None:
                user.email = None
                
            await user.save()
            count += 1
            print(f"Updated user: {user.name} ({user.login})")
            
    print(f"Successfully fixed {count} users.")

if __name__ == "__main__":
    asyncio.run(main())
