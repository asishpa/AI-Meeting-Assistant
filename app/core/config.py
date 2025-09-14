from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ELEVENLABS_API_KEY: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False  # Default to False if not set
    ASSEMBLYAI_API_KEY: str
    model_config = {
        "env_file": ".env",
    }

settings = Settings()
