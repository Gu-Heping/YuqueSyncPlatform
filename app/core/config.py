from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 语雀配置
    YUQUE_TOKEN: str
    YUQUE_BASE_URL: str = "https://nova.yuque.com/api/v2"
    
    # MongoDB 配置
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "yuque_sync_db"

    # AI / RAG 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.chatanywhere.tech/v1" # 支持兼容接口
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "yuque_docs"

    # 读取 .env 文件
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
