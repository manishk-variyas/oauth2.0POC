from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Keycloak
    KEYCLOAK_URL: str = "http://localhost:8080"
    REALM: str = "notes-app"
    KEYCLOAK_CLIENT_ID: str = "notes-app-client"
    KEYCLOAK_CLIENT_SECRET: str = "xvbAvMEWemYMwSPr6YSzjdRGG706wyCC"

    # Session / JWT
    SECRET_KEY: str = "change-me-in-production-use-strong-random-key"
    ALGORITHM: str = "HS256"
    SESSION_EXPIRE_HOURS: int = 24

    # URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:5173"

    # Cookie
    COOKIE_SECURE: bool = False

    # Database
    DATABASE_URL: str = "postgresql://notes:notes123@localhost:5432/notes"
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def JWKS_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.REALM}/protocol/openid-connect/certs"

    @property
    def ISSUER_URL(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.REALM}"

    class Config:
        env_file = ".env"


settings = Settings()
