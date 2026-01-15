from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.models.schemas import Member
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.config import settings
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdate(BaseModel):
    password: Optional[str] = None
    email: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    user_id: int

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await Member.find_one(Member.login == username)
    if user is None:
        raise credentials_exception
    return user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 尝试通过 login 字段查找
    user = await Member.find_one(Member.login == form_data.username)
    if not user:
        # 尝试通过 name 查找 (虽然 login 更唯一，但为了方便也可以支持 name)
        user = await Member.find_one(Member.name == form_data.username)
    
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.login})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=Member)
async def read_users_me(current_user: Member = Depends(get_current_user)):
    return current_user

@router.put("/users/me", response_model=Member)
async def update_user_me(update_data: UserUpdate, current_user: Member = Depends(get_current_user)):
    if update_data.password:
        current_user.hashed_password = get_password_hash(update_data.password)
    # 允许 email 传空字符串或 None 时清空邮箱字段
    if update_data.email is not None:
        current_user.email = update_data.email
    await current_user.save()
    return current_user

@router.post("/admin/reset-password")
async def reset_password(request: ResetPasswordRequest, current_user: Member = Depends(get_current_user)):
    # 简单的管理员检查：role=1 (Admin) 或 role=0 (Owner)
    if current_user.role not in [0, 1]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    target_user = await Member.find_one(Member.yuque_id == request.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    target_user.hashed_password = get_password_hash("123456")
    await target_user.save()
    return {"message": "Password reset successfully"}

@router.post("/admin/migrate-credentials")
async def migrate_credentials(
    secret_key: str = Query(..., description="Admin secret key for migration"),
    force_reset: bool = Query(False, description="Force reset all users to default password")
):
    """
    批量初始化/重置用户凭证 (用于旧数据迁移)
    需要提供 SECRET_KEY 进行验证
    """
    if secret_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    count = 0
    default_hash = get_password_hash("123456")
    
    # 获取所有成员
    users = await Member.find_all().to_list()
    
    for user in users:
        # 如果强制重置，或者用户没有密码哈希
        if force_reset or not user.hashed_password:
            user.hashed_password = default_hash
            # 确保 email 字段存在 (如果为 None 则保持 None)
            if not hasattr(user, 'email'):
                user.email = None
            
            await user.save()
            count += 1
            
    return {
        "message": f"Successfully migrated credentials for {count} users", 
        "updated_count": count,
        "total_scanned": len(users)
    }

class UserSearchResult(BaseModel):
    name: str
    login: str
    avatar_url: Optional[str] = None

@router.get("/users/search", response_model=list[UserSearchResult], summary="公开搜索用户(用于登录联想)")
async def search_users_public(q: str = Query(..., min_length=1, max_length=50)):
    """
    公开的用户搜索接口，用于登录页面的自动联想。
    支持按 name 或 login 模糊匹配 (不区分大小写)。
    最多返回 10 条结果。
    """
    # 构造正则表达式进行模糊匹配
    regex_pattern = {"$regex": q, "$options": "i"}
    query = {
        "$or": [
            {"name": regex_pattern},
            {"login": regex_pattern}
        ]
    }
    
    # 查找并限制返回数量
    members = await Member.find(query).limit(10).to_list()
    
    # 转换为结果模型
    results = []
    for m in members:
        results.append(UserSearchResult(
            name=m.name,
            login=m.login,
            avatar_url=m.avatar_url
        ))
        
    return results
