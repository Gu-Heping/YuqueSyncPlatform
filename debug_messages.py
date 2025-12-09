import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.schemas import Member, Doc, Repo, Comment, User, ChatSession, ChatMessage, Activity

async def main():
    # Initialize DB
    client = AsyncIOMotorClient(settings.MONGO_URI)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=[User, Repo, Doc, Member, Comment, ChatSession, ChatMessage, Activity],
        allow_index_dropping=True
    )

    print("--- Debugging Messages Logic ---")
    
    # 1. List all Members (Potential Current Users)
    members = await Member.find_all().to_list()
    print(f"Total Members: {len(members)}")
    for m in members:
        print(f"Member: {m.name} (ID: {m.yuque_id}, Login: {m.login})")

    # 2. List all Comments
    comments = await Comment.find_all().sort("-created_at").limit(5).to_list()
    print(f"\nTotal Comments: {await Comment.count()}")
    print("Recent 5 Comments:")
    for c in comments:
        print(f"  - Comment ID: {c.yuque_id}, Doc ID: {c.doc_id}, User ID: {c.user_id}, Body: {c.body_html[:30]}...")
        
        # Check Doc for this comment
        doc = await Doc.find_one(Doc.yuque_id == c.doc_id)
        if doc:
            print(f"    -> Related Doc: '{doc.title}' (ID: {doc.yuque_id}), Owner ID: {doc.user_id}, Repo ID: {doc.repo_id}")
        else:
            print(f"    -> Related Doc NOT FOUND in DB (ID: {c.doc_id})")

    # 3. Simulate 'My Messages' for each member
    print("\n--- Simulating Filter 'me' ---")
    for m in members:
        print(f"\nChecking for Member: {m.name} ({m.yuque_id})")
        
        # Logic from api/comments.py
        # 查找我拥有的文档 ID
        my_docs = await Doc.find(Doc.user_id == m.yuque_id).to_list()
        my_doc_ids = set(d.yuque_id for d in my_docs if d.yuque_id)
        print(f"  - Owns {len(my_doc_ids)} docs directly.")
        
        # 查找我拥有的知识库 ID
        my_repos = await Repo.find(Repo.user_id == m.yuque_id).to_list()
        my_repo_ids = [r.yuque_id for r in my_repos if r.yuque_id]
        print(f"  - Owns {len(my_repo_ids)} repos.")
        
        if my_repo_ids:
            # 查找这些知识库下的所有文档
            repo_docs = await Doc.find(Doc.repo_id << my_repo_ids).to_list()
            count_before = len(my_doc_ids)
            my_doc_ids.update(d.yuque_id for d in repo_docs if d.yuque_id)
            print(f"  - Added {len(my_doc_ids) - count_before} docs from owned repos.")
            
        # Query
        or_conditions = []
        if my_doc_ids:
            or_conditions.append({"doc_id": {"$in": list(my_doc_ids)}})
        
        # ADDED: Also include comments made BY the user
        or_conditions.append({"user_id": m.yuque_id})
        
        query = {"$or": or_conditions}
        
        found_comments = await Comment.find(query).count()
        print(f"  - Filter would return {found_comments} comments.")
        
        if found_comments > 0:
             comments_list = await Comment.find(query).limit(5).to_list()
             for c in comments_list:
                 print(f"    * Found Comment {c.yuque_id} by {c.user_id} on Doc {c.doc_id}")

if __name__ == "__main__":
    asyncio.run(main())
