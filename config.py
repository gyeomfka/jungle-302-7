import os
from dotenv import load_dotenv

load_dotenv(verbose=True)


class BaseConfig:
    # 공통
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")
    MONGO_USERNAME = os.environ.get("MONGO_USERNAME")
    MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
    # authSource는 보통 admin
    MONGO_AUTH_SOURCE = os.environ.get("MONGO_AUTH_SOURCE")

    # 카카오 OAuth
    KAKAO_CLIENT_ID = os.environ.get("KAKAO_CLIENT_ID")
    KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET")
    KAKAO_REDIRECT_URI = os.environ.get("KAKAO_REDIRECT_URI")

    # SMTP
    GMAIL_USER = os.environ.get("GMAIL_USER")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


class DevConfig(BaseConfig):
    """개발: AWS EC2의 원격 MongoDB로 접속"""
    # 예) EC2 퍼블릭 IP 또는 도메인
    EC2_PORT = 27017
    EC2_HOST = os.environ.get("EC2_HOST")

    # mongodb://admin:비번@EC2_IP:27017/?authSource=admin
    MONGO_URI = (
        f"mongodb://{BaseConfig.MONGO_USERNAME}:{BaseConfig.MONGO_PASSWORD}"
        f"@{EC2_HOST}:{EC2_PORT}/?authSource={BaseConfig.MONGO_AUTH_SOURCE}"
    )


# TODO: 추후 작동하는지 확인 필요
class ProdConfig(BaseConfig):
    """운영: 로컬 MongoDB로 접속"""
    # 1) TCP(기본): localhost:27017
    LOCAL_HOST = os.environ.get("LOCAL_HOST", "127.0.0.1")
    LOCAL_PORT = 27017
    EC2_HOST = os.environ.get("EC2_HOST")

    @property
    def MONGO_URI(self):
        return (
            f"mongodb://{self.MONGO_USERNAME}:{self.MONGO_PASSWORD}"
            f"@{self.LOCAL_HOST}:{self.LOCAL_PORT}/"
            f"?authSource={self.MONGO_AUTH_SOURCE}"
        )


def get_config():
    env = os.environ.get("APP_ENV", "development").lower()
    if env in ("prod", "production"):
        return ProdConfig()
    return DevConfig()
