#
import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, ClassVar
from functools import lru_cache


class BaseConfig(BaseSettings):
    ENV_STATE: Optional[str] = None

    # class Config:
    #     env_file: str = ".env"
    #     extra = "allow"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class GlobalConfig(BaseConfig):
    DATABASE_URL: Optional[str] = None
    DB_FORCE_ROLL_BACK: bool = False
    ALGORITHM: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    LOGIN_URL: Optional[str] = None

    OKTA_DOMAIN: Optional[str] = None
    OKTA_CLIENT_ID: Optional[str] = None
    OKTA_CLIENT_SECRET: Optional[str] = None
    OKTA_REDIRECT_URI: Optional[str] = None
    OKTA_APP_ID: Optional[str] = None
    OKTA_API_TOKEN: Optional[str] = None
    FRONTEND_LOGOUT_REDIRECT_URI: Optional[str] = None
    LOGOUT_REDIRECT_URI: Optional[str]=None
    OKTA_ISSUER: Optional[str] = None
    DEFAULT_ROLE_ID: int = 1
    BASE_DIR: ClassVar[str] = os.path.dirname(os.path.abspath(__file__))




class DevConfig(GlobalConfig):
    # class Config:
    #     env_prefix: str = "DEV_"
    model_config = SettingsConfigDict(env_prefix="DEV_", extra="ignore")

class ProdConfig(GlobalConfig):
    # class Config:
    #     env_prefix: str = "PROD_"
    model_config = SettingsConfigDict(env_prefix="PROD_", extra="ignore")


class TestConfig(GlobalConfig):
    DATABASE_URL: str = "sqlite:///test.db"
    DB_FORCE_ROLL_BACK: bool = True

    # class Config:
    #     env_prefix: str = "TEST_"
    model_config = SettingsConfigDict(env_prefix="TEST_", extra="ignore")


# @lru_cache()
def get_config(env_state: str):
    configs = {"dev": DevConfig, "prod": ProdConfig, "test": TestConfig}
    return configs[env_state]()


base_config = BaseConfig()

config = get_config(base_config.ENV_STATE)
print("ENV_STATE:", base_config.ENV_STATE)
