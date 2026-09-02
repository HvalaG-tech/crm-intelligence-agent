from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    data_dir: str = "data/processed"
    max_tool_iterations: int = 5
    max_conversation_tokens: int = 8000
    log_level: str = "INFO"

    # --- Démonstration publique -------------------------------------------
    # Vrai par défaut : un dépôt cloné, ou déployé sans variable d'environnement,
    # doit être consultable sans clé et sans facturer personne. Passer à faux
    # sur une instance privée où l'on veut l'agent complet d'emblée.
    demo_mode: bool = True

    # Plafond de questions libres par session de navigation. Le visiteur paie
    # avec sa propre clé, mais un plafond le protège d'une boucle accidentelle
    # autant qu'il protège la démonstration.
    max_questions_session: int = 10


settings = Settings()
