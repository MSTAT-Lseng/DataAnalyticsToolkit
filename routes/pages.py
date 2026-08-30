"""页面路由 — 渲染各功能模块的 HTML 页面。"""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    """首页：功能导航卡片。"""
    return render_template("index.html")


@pages_bp.route("/segmentation")
def segmentation():
    """分词统计页面。"""
    return render_template("segmentation.html")


@pages_bp.route("/wordcloud")
def wordcloud():
    """词云制作页面。"""
    return render_template("wordcloud.html")


@pages_bp.route("/sentiment")
def sentiment():
    """情感分析页面。"""
    return render_template("sentiment.html")


@pages_bp.route("/social-network")
def social_network():
    """社会网络关系图页面。"""
    return render_template("social_network.html")


@pages_bp.route("/regression")
def regression():
    """回归分析页面。"""
    return render_template("regression.html")


@pages_bp.route("/cleaning")
def cleaning():
    """数据清洗页面。"""
    return render_template("cleaning.html")


@pages_bp.route("/dimension-mining")
def dimension_mining():
    """维度挖掘页面。"""
    return render_template("dimension_mining.html")
