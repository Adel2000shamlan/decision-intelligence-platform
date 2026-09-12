from dataclasses import dataclass
import os
@dataclass(frozen=True)
class Settings:
    environment: str=os.getenv("APP_ENV","development")
    database_url: str=os.getenv("DATABASE_URL","sqlite:///./decision_intelligence.db")
    redis_url: str=os.getenv("REDIS_URL","redis://localhost:6379/0")
    api_prefix: str=os.getenv("API_PREFIX","/api/v1")
    access_token_ttl_seconds: int=int(os.getenv("ACCESS_TOKEN_TTL", "900"))
    refresh_token_ttl_seconds: int=int(os.getenv("REFRESH_TOKEN_TTL", "2592000"))
settings=Settings()
