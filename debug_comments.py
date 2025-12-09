import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.schemas import Member, Doc, Repo, Comment, User, ChatSession, ChatMessage, Activity

async def init_db():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=[User, Repo, Doc, Member, Comment, ChatSession, ChatMessage, Activity],
        allow_index_dropping=True
    )

async def main():
    await init_db()
    
    print("--- Members ---")
    members = await Member.find_all().to_list()
    for m in members:
        print(f"Member: {m.name} (ID: {m.yuque_id})")
        
    print("\n--- Repos ---")
    repos = await Repo.find_all().to_list()
    for r in repos:
        print(f"Repo: {r.name} (ID: {r.yuque_id}, UserID: {r.user_id})")

    print("\n--- Docs (Sample 10) ---")
    docs = await Doc.find_all().limit(10).to_list()
    for d in docs:
        print(f"Doc: {d.title} (ID: {d.yuque_id}, RepoID: {d.repo_id}, UserID: {d.user_id})")

    print("\n--- Comments ---")
    comments = await Comment.find_all().to_list()
    for c in comments:
        print(f"Comment on Doc {c.doc_id} by User {c.user_id}: {c.body_html[:20]}...")

    if members:
        user = members[0]
        print(f"\n--- Simulation for User {user.name} ({user.yuque_id}) ---")
        
        my_docs = await Doc.find(Doc.user_id == user.yuque_id).project(Doc.yuque_id).to_list()
        my_doc_ids = set(d.yuque_id for d in my_docs if d.yuque_id)
        print(f"Directly owned docs: {len(my_doc_ids)}")
        
        my_repos = await Repo.find(Repo.user_id == user.yuque_id).project(Repo.yuque_id).to_list()
        my_repo_ids = [r.yuque_id for r in my_repos if r.yuque_id]
        print(f"Owned repos: {my_repo_ids}")
        
        if my_repo_ids:
            repo_docs = await Doc.find(Doc.repo_id << my_repo_ids).project(Doc.yuque_id).to_list()
            repo_doc_ids = [d.yuque_id for d in repo_docs if d.yuque_id]
            print(f"Docs in owned repos: {len(repo_doc_ids)}")
            my_doc_ids.update(repo_doc_ids)
            
        print(f"Total relevant doc IDs: {len(my_doc_ids)}")
        
        relevant_comments = await Comment.find({"doc_id": {"$in": list(my_doc_ids)}}).to_list()
        print(f"Found {len(relevant_comments)} comments for this user.")

if __name__ == "__main__":
    asyncio.run(main())
