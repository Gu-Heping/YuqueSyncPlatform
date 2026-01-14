import pytest
from app.models.schemas import Member, User
from app.core.security import get_password_hash

@pytest.mark.asyncio
async def test_login_success(client, mock_db):
    # Setup user
    password = "password123"
    hashed = get_password_hash(password)
    user = Member(yuque_id=1, login="testuser", name="Test User", hashed_password=hashed)
    await user.insert()
    
    # Test login
    response = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_failure(client, mock_db):
    response = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": "wrongpassword"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_profile(client, mock_db):
    # Setup user and token
    password = "password123"
    hashed = get_password_hash(password)
    user = Member(yuque_id=1, login="testuser", name="Test User", hashed_password=hashed)
    await user.insert()
    
    # Login to get token
    login_res = await client.post("/api/v1/auth/login", data={"username": "testuser", "password": password})
    token = login_res.json()["access_token"]
    
    # Update profile
    headers = {"Authorization": f"Bearer {token}"}
    update_data = {"email": "new@example.com"}
    response = await client.put("/api/v1/auth/users/me", json=update_data, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"
    
    # Verify in DB
    updated_user = await Member.find_one(Member.login == "testuser")
    assert updated_user.email == "new@example.com"
