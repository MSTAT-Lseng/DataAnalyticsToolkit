"""Application configuration."""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "txt"}

    # matplotlib 后端（无 GUI）
    MPL_BACKEND = "Agg"

    # 停用词文件路径
    STOPWORDS_FILE = os.path.join(BASE_DIR, "utils", "stopwords.txt")

    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FILE = os.path.join(BASE_DIR, "logs", "app.log")
