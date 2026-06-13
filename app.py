"""DataAnalyticsToolkit — Flask 应用入口。

基于 AGENTS.md 设计方案，面向中文文本数据处理的 Web 应用。
提供分词统计、词云制作、情感分析、回归分析四大功能模块。

启动方式：
source venv/bin/activate
python app.py
访问 http://127.0.0.1:5000
"""

import os
import logging
from flask import Flask, render_template, request, jsonify

from config import Config

# ============================================================
# 应用工厂
# ============================================================


def create_app(config_class=Config) -> Flask:
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

    # ---- 注册路由 ----
    _register_routes(app)

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


def _register_routes(app: Flask) -> None:
    """注册所有路由和 API 端点。"""

    # ================================================================
    # 页面路由
    # ================================================================

    @app.route("/")
    def index():
        """首页：功能导航卡片。"""
        return render_template("index.html")

    @app.route("/segmentation")
    def segmentation():
        """分词统计页面。"""
        return render_template("segmentation.html")

    @app.route("/wordcloud")
    def wordcloud():
        """词云制作页面。"""
        return render_template("wordcloud.html")

    @app.route("/sentiment")
    def sentiment():
        """情感分析页面。"""
        return render_template("sentiment.html")

    @app.route("/regression")
    def regression():
        """回归分析页面。"""
        return render_template("regression.html")

    # ================================================================
    # API 端点
    # ================================================================

    # ---- 分词统计 API ----
    @app.route("/api/segmentation", methods=["POST"])
    def api_segmentation():
        """接收 JSON {text, top_n, remove_stopwords, extra_stopwords, extra_dict}，返回词频列表。"""
        try:
            data = request.get_json(force=True)
            text = (data.get("text") or "").strip()
            if not text:
                return jsonify({"success": False, "error": "文本不能为空"}), 400

            top_n = int(data.get("top_n", 20))
            remove_stopwords = data.get("remove_stopwords", True)

            # 自定义停用词
            extra_list = data.get("extra_stopwords")
            extra_stopwords: set[str] | None = None
            if extra_list and isinstance(extra_list, list):
                extra_stopwords = {str(w).strip() for w in extra_list if str(w).strip()}

            # 自定义词典
            dict_list = data.get("extra_dict")
            extra_dict: list[str] | None = None
            if dict_list and isinstance(dict_list, list):
                extra_dict = [str(w).strip() for w in dict_list if str(w).strip()]

            from utils.segmentation import segment_text

            freq_dict = segment_text(
                text,
                top_n=top_n,
                remove_stopwords=remove_stopwords,
                extra_stopwords=extra_stopwords,
                extra_dict=extra_dict,
            )
            words = list(freq_dict.items())  # [(word, count), ...], 已降序

            total_count = sum(v for _, v in words)

            app.logger.info(
                "Segmentation done: %d unique words, %d total tokens",
                len(words),
                total_count,
            )

            return jsonify({
                "success": True,
                "words": words,
                "unique_words": len(words),
                "total_count": total_count,
            })
        except Exception as exc:
            app.logger.exception("Segmentation API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 表格文件预览 API ----
    @app.route("/api/segmentation/preview", methods=["POST"])
    def api_segmentation_preview():
        """接收 Excel 文件，返回列名和预览数据。"""
        try:
            import pandas as pd
            import tempfile
            import os as _os

            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传表格文件"}), 400

            suffix = _os.path.splitext(file.filename)[1].lower()
            if suffix not in (".xls", ".xlsx", ".csv"):
                return jsonify({
                    "success": False,
                    "error": f"不支持的文件格式：{suffix}，请上传 .xls / .xlsx / .csv"
                }), 400

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name

            try:
                if suffix == ".csv":
                    df = pd.read_csv(tmp_path)
                else:
                    df = pd.read_excel(tmp_path, engine="openpyxl" if suffix == ".xlsx" else "xlrd")

                columns = [str(c) for c in df.columns.tolist()]
                # 取前 20 行作为预览
                preview_df = df.head(20).fillna("")
                rows = preview_df.values.tolist()
                # 将每行转为字符串列表
                rows = [[str(v) for v in row] for row in rows]

                app.logger.info(
                    "Excel preview: %d columns, %d preview rows (total %d rows)",
                    len(columns), len(rows), len(df),
                )

                return jsonify({
                    "success": True,
                    "columns": columns,
                    "rows": rows,
                    "total_rows": len(df),
                })
            finally:
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Segmentation preview API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 表格文件分词 API ----
    @app.route("/api/segmentation/file", methods=["POST"])
    def api_segmentation_file():
        """接收 Excel 文件 + 列名 + 可选自定义停用词/词典，对该列所有行进行分词统计。"""
        try:
            import pandas as pd
            import tempfile
            import os as _os

            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传表格文件"}), 400

            column = (request.form.get("column") or "").strip()
            if not column:
                return jsonify({"success": False, "error": "请选择要分词的列"}), 400

            top_n = int(request.form.get("top_n", 20))
            remove_stopwords = request.form.get("remove_stopwords", "true").lower() == "true"

            # 自定义停用词（换行分隔）
            extra_raw = (request.form.get("extra_stopwords") or "").strip()
            extra_stopwords: set[str] | None = None
            if extra_raw:
                extra_stopwords = {
                    w.strip() for w in extra_raw.split("\n") if w.strip()
                }

            # 自定义词典（换行分隔）
            dict_raw = (request.form.get("extra_dict") or "").strip()
            extra_dict: list[str] | None = None
            if dict_raw:
                extra_dict = [w.strip() for w in dict_raw.split("\n") if w.strip()]

            suffix = _os.path.splitext(file.filename)[1].lower()
            if suffix not in (".xls", ".xlsx", ".csv"):
                return jsonify({
                    "success": False,
                    "error": f"不支持的文件格式：{suffix}"
                }), 400

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name

            try:
                if suffix == ".csv":
                    df = pd.read_csv(tmp_path)
                else:
                    df = pd.read_excel(tmp_path, engine="openpyxl" if suffix == ".xlsx" else "xlrd")

                if column not in df.columns:
                    available = [str(c) for c in df.columns.tolist()]
                    return jsonify({
                        "success": False,
                        "error": f"列 '{column}' 不存在。可用列：{', '.join(available)}"
                    }), 400

                # 提取该列所有非空文本
                col_data = df[column].dropna().astype(str)
                combined_text = "\n".join(col_data.tolist())

                if not combined_text.strip():
                    return jsonify({"success": False, "error": f"列 '{column}' 中没有有效文本"}), 400

                from utils.segmentation import segment_text

                freq_dict = segment_text(
                    combined_text,
                    top_n=top_n,
                    remove_stopwords=remove_stopwords,
                    extra_stopwords=extra_stopwords,
                    extra_dict=extra_dict,
                )
                words = list(freq_dict.items())
                total_count = sum(v for _, v in words)

                app.logger.info(
                    "File segmentation done: column='%s', %d rows, %d unique words, %d total tokens",
                    column, len(col_data), len(words), total_count,
                )

                return jsonify({
                    "success": True,
                    "words": words,
                    "unique_words": len(words),
                    "total_count": total_count,
                    "source_column": column,
                    "source_rows": len(col_data),
                })
            finally:
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Segmentation file API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 词云生成 API ----
    @app.route("/api/wordcloud", methods=["POST"])
    def api_wordcloud():
        """接收表单 {text, max_words, colormap, bg_color}，返回 Base64 图片。"""
        try:
            text = (request.form.get("text") or "").strip()
            if not text:
                return jsonify({"success": False, "error": "文本不能为空"}), 400

            max_words = int(request.form.get("max_words", 150))
            colormap = request.form.get("colormap", "viridis")
            bg_color = request.form.get("bg_color", "#ffffff")

            from utils.wordcloud_gen import generate_wordcloud

            b64 = generate_wordcloud(
                text=text,
                max_words=max_words,
                colormap=colormap,
                background_color=bg_color,
            )

            app.logger.info("Wordcloud generated successfully")

            return jsonify({
                "success": True,
                "image_base64": b64,
            })
        except Exception as exc:
            app.logger.exception("Wordcloud API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 情感分析 API ----
    @app.route("/api/sentiment", methods=["POST"])
    def api_sentiment():
        """接收 JSON {text}，返回情感分析结果。"""
        try:
            data = request.get_json(force=True)
            text = (data.get("text") or "").strip()
            if not text:
                return jsonify({"success": False, "error": "文本不能为空"}), 400

            from utils.sentiment_analysis import analyze_sentiment

            result = analyze_sentiment(text)

            app.logger.info(
                "Sentiment analysis done: score=%.3f, label=%s, sentences=%d",
                result["score"],
                result["label"],
                result["sentence_count"],
            )

            return jsonify({"success": True, "result": result})
        except Exception as exc:
            app.logger.exception("Sentiment API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 回归分析 API（CSV 上传） ----
    @app.route("/api/regression", methods=["POST"])
    def api_regression():
        """接收 CSV 文件 + 列名，返回回归分析结果。"""
        try:
            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传 CSV 文件"}), 400

            x_column = (request.form.get("x_column") or "").strip()
            y_column = (request.form.get("y_column") or "").strip()

            if not x_column or not y_column:
                return jsonify({"success": False, "error": "请指定 X 和 Y 列名"}), 400

            # 保存到临时路径
            import tempfile
            suffix = os.path.splitext(file.filename)[1] or ".csv"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name

            try:
                from utils.regression import linear_regression_from_csv

                result = linear_regression_from_csv(tmp_path, x_column, y_column)

                app.logger.info(
                    "Regression done: R²=%.4f, n=%d, equation=%s",
                    result["r_squared"],
                    result["sample_count"],
                    result["equation"],
                )

                return jsonify({"success": True, "result": result})
            finally:
                # 用后即删
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Regression API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 回归分析 API（手动输入） ----
    @app.route("/api/regression/manual", methods=["POST"])
    def api_regression_manual():
        """接收 JSON {data: [{x, y}, ...]}，返回回归分析结果。"""
        try:
            data = request.get_json(force=True)
            points = data.get("data", [])

            if len(points) < 2:
                return jsonify({"success": False, "error": "至少需要 2 个数据点"}), 400

            from utils.regression import linear_regression_from_json

            result = linear_regression_from_json(points)

            app.logger.info(
                "Regression (manual) done: R²=%.4f, n=%d",
                result["r_squared"],
                result["sample_count"],
            )

            return jsonify({"success": True, "result": result})
        except Exception as exc:
            app.logger.exception("Regression manual API error")
            return jsonify({"success": False, "error": str(exc)}), 500


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    app = create_app()
    app.logger.info("DataAnalyticsToolkit starting on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
