from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    data_dir: str = "data/processed"
    max_tool_iterations: int = 5
    max_conversation_tokens: int = 8000
    log_level: str = "INFO"


settings = Settings()
