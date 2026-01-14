import pytest
from app.models.schemas import Member
from app.api.auth import get_current_user

@pytest.mark.asyncio
async def test_follow_all(client, mock_db, app):
    # Setup users
    user1 = Member(yuque_id=1, login="u1", name="User 1")
    user2 = Member(yuque_id=2, login="u2", name="User 2")
    user3 = Member(yuque_id=3, login="u3", name="User 3")
    
    await user1.insert()
    await user2.insert()
    await user3.insert()
    
    # 强制覆盖 Dependency，让 API 认为当前登录的是 user1
    # 注意：这需要 app fixture 能访问到 FastAPI 实例
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_current_user] = lambda: user1
    
    try:
        # Call Follow All
        response = await client.post("/api/v1/members/follow/all")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        
        # Verify DB
        u2 = await Member.find_one(Member.yuque_id == 2)
        u3 = await Member.find_one(Member.yuque_id == 3)
        
        assert 1 in u2.followers
        assert 1 in u3.followers
    finally:
        # 清理 dependency overrides
        fastapi_app.dependency_overrides = {}
