"""DataAnalyticsToolkit — Flask 应用入口。

基于 AGENTS.md 设计方案，面向中文文本数据处理的 Web 应用。
提供分词统计、词云制作、情感分析、社会网络关系图、回归分析、数据清洗、热力分析和聚类分析八大功能模块。

启动方式：
    source venv/bin/activate
    python app.py
    访问 http://127.0.0.1:5000
"""

import os
import logging
import sys
import argparse

from flask import Flask

from config import Config


def create_app(config_class=Config) -> Flask:
    """应用工厂函数。"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ---- 确保必要目录存在 ----
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.dirname(app.config.get("LOG_FILE", "logs/app.log")), exist_ok=True)

    # ---- 配置 matplotlib 后端 ----
    import matplotlib
    matplotlib.use(app.config["MPL_BACKEND"])

    # ---- 日志 ----
    _setup_logging(app)

    # ---- 注册路由（蓝图） ----
    from routes import register_routes
    register_routes(app)

    return app


def _setup_logging(app: Flask) -> None:
    """配置日志输出。"""
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    log_file = app.config.get("LOG_FILE")

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file) if log_file else logging.NullHandler(),
        ],
    )
    app.logger.setLevel(log_level)


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    app = create_app()
    app.logger.info(f"DataAnalyticsToolkit starting on http://127.0.0.1:{args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=True)
