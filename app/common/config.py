from dataclasses import dataclass
from os import path, environ
base_dir = path.dirname(path.dirname(path.dirname((path.abspath(__file__)))))


@dataclass
class Config:
    """
    기본 Configuration
    """
    BASE_DIR = base_dir
    DB_POO_RECYCLE:int = 900
    DB_ECHO: bool = True
    DEBUG: bool = True
    TEST_MODE: bool = False

@dataclass
class LocalConfig(Config):
    PROJ_RELOAD: bool = True
    TRUSTED_HOSTS = ["*"]
    ALLOW_SITE = ["*"]
    DEBUG = True

    DB_ID = "travis"
    DB_PASSWORD = "skfgnxh1"
    DB_HOST = "localhost"
    DB_DATABASE = "notification_api"
    DB_URL: str = f"mysql+pymysql://{DB_ID}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?charset=utf8mb4"

@dataclass
class ProdConfig(Config):
    PROJ_RELOAD: bool = False
    TRUSTED_HOSTS = ["*"]
    ALLOW_SITE = ["*"]
    DEBUG = False

    DB_ID = "travis"
    DB_PASSWORD = "skfgnxh1"
    DB_HOST = "localhost"
    DB_DATABASE = "notification_api"
    DB_URL: str = f"mysql+pymysql://{DB_ID}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?charset=utf8mb4"
@dataclass
class TestConfig(Config):

    DB_ID = "travis"
    DB_PASSWORD = "skfgnxh1"
    DB_HOST = "localhost"
    DB_DATABASE = "notification_test"
    DB_URL: str = f"mysql+pymysql://{DB_ID}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}?charset=utf8mb4"

    TRUSTED_HOSTS = ["*"]
    ALLOW_SITE = ["*"]
    TEST_MODE: bool = True



# dataclass
# asdict 사용시, 객체 -> Dict로 변경 가능

def conf():
    """
    환경 불러오기
    :return:
    """
    config = dict(prod=ProdConfig, local=LocalConfig, test=TestConfig)
    return config[environ.get("API_ENV", "local")]()



