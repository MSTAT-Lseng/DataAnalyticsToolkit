"""路由包 — 导入并注册所有 Flask Blueprint。"""

from flask import Flask

from routes.pages import pages_bp
from routes.segmentation import segmentation_bp
from routes.wordcloud import wordcloud_bp
from routes.sentiment import sentiment_bp
from routes.regression import regression_bp
from routes.cleaning import cleaning_bp
from routes.dimension_mining import dimension_mining_bp
from routes.social_network import social_network_bp


def register_routes(app: Flask) -> None:
    """向 Flask 应用注册所有蓝图。"""
    app.register_blueprint(pages_bp)
    app.register_blueprint(segmentation_bp)
    app.register_blueprint(wordcloud_bp)
    app.register_blueprint(sentiment_bp)
    app.register_blueprint(regression_bp)
    app.register_blueprint(cleaning_bp)
    app.register_blueprint(dimension_mining_bp)
    app.register_blueprint(social_network_bp)
