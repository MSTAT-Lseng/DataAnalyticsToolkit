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

    # ---- 导出全部词频 API（文本） ----
    @app.route("/api/segmentation/export", methods=["POST"])
    def api_segmentation_export():
        """接收与分词相同的 JSON，返回所有词频的 Excel 文件。"""
        try:
            import io
            import openpyxl

            data = request.get_json(force=True)
            text = (data.get("text") or "").strip()
            if not text:
                return jsonify({"success": False, "error": "文本不能为空"}), 400

            remove_stopwords = data.get("remove_stopwords", True)
            extra_list = data.get("extra_stopwords")
            extra_stopwords: set[str] | None = None
            if extra_list and isinstance(extra_list, list):
                extra_stopwords = {str(w).strip() for w in extra_list if str(w).strip()}

            dict_list = data.get("extra_dict")
            extra_dict: list[str] | None = None
            if dict_list and isinstance(dict_list, list):
                extra_dict = [str(w).strip() for w in dict_list if str(w).strip()]

            from utils.segmentation import segment_text

            # top_n=0 返回全部
            freq_dict = segment_text(
                text, top_n=0,
                remove_stopwords=remove_stopwords,
                extra_stopwords=extra_stopwords,
                extra_dict=extra_dict,
            )
            words = list(freq_dict.items())

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "词频统计"
            ws.append(["排名", "词语", "频次"])
            for i, (word, count) in enumerate(words, 1):
                ws.append([i, word, count])

            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)

            from flask import send_file
            return send_file(
                buf,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="词频统计_全部.xlsx",
            )
        except Exception as exc:
            app.logger.exception("Segmentation export API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 导出全部词频 API（表格文件） ----
    @app.route("/api/segmentation/file/export", methods=["POST"])
    def api_segmentation_file_export():
        """接收 Excel 文件 + 列名，返回该列所有词频的 Excel 文件。"""
        try:
            import io
            import openpyxl
            import pandas as pd
            import tempfile
            import os as _os

            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传表格文件"}), 400

            column = (request.form.get("column") or "").strip()
            if not column:
                return jsonify({"success": False, "error": "请选择列"}), 400

            remove_stopwords = request.form.get("remove_stopwords", "true").lower() == "true"
            extra_raw = (request.form.get("extra_stopwords") or "").strip()
            extra_stopwords: set[str] | None = None
            if extra_raw:
                extra_stopwords = {w.strip() for w in extra_raw.split("\n") if w.strip()}
            dict_raw = (request.form.get("extra_dict") or "").strip()
            extra_dict: list[str] | None = None
            if dict_raw:
                extra_dict = [w.strip() for w in dict_raw.split("\n") if w.strip()]

            suffix = _os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name

            try:
                if suffix == ".csv":
                    df = pd.read_csv(tmp_path)
                else:
                    df = pd.read_excel(tmp_path, engine="openpyxl" if suffix == ".xlsx" else "xlrd")

                col_data = df[column].dropna().astype(str)
                combined = "\n".join(col_data.tolist())

                from utils.segmentation import segment_text

                freq_dict = segment_text(
                    combined, top_n=0,
                    remove_stopwords=remove_stopwords,
                    extra_stopwords=extra_stopwords,
                    extra_dict=extra_dict,
                )
                words = list(freq_dict.items())

                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "词频统计"
                ws.append(["排名", "词语", "频次"])
                for i, (word, count) in enumerate(words, 1):
                    ws.append([i, word, count])

                buf = io.BytesIO()
                wb.save(buf)
                buf.seek(0)

                from flask import send_file
                return send_file(
                    buf,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    as_attachment=True,
                    download_name=f"词频统计_{column}.xlsx",
                )
            finally:
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Segmentation file export API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 词频文件预览 API ----
    @app.route("/api/wordcloud/preview-freq", methods=["POST"])
    def api_wordcloud_preview_freq():
        """接收词频 Excel 文件，返回解析后的词频预览数据。"""
        try:
            import pandas as pd
            import tempfile
            import os as _os

            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传词频文件"}), 400

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

                cols = [str(c).strip() for c in df.columns.tolist()]
                word_col = None
                count_col = None

                for c in cols:
                    if c in ("词语", "word", "Word", "term", "Term"):
                        word_col = c
                    elif c in ("频次", "count", "Count", "freq", "Freq", "frequency", "Frequency"):
                        count_col = c

                if word_col is None:
                    word_col = cols[0]
                if count_col is None:
                    count_col = cols[1] if len(cols) > 1 else None

                if count_col is None:
                    return jsonify({
                        "success": False,
                        "error": "无法识别词频文件的列结构，请确保包含「词语」和「频次」两列"
                    }), 400

                words = []
                for _, row in df.iterrows():
                    word = str(row[word_col]).strip() if pd.notna(row[word_col]) else ""
                    try:
                        count = int(row[count_col])
                    except (ValueError, TypeError):
                        continue
                    if word and count > 0:
                        words.append({"word": word, "count": count})

                if not words:
                    return jsonify({
                        "success": False,
                        "error": "未能从文件中解析到有效的词频数据"
                    }), 400

                app.logger.info("Freq file preview: %d words parsed", len(words))

                return jsonify({
                    "success": True,
                    "words": words,
                    "total": len(words),
                })
            finally:
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Wordcloud preview-freq API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 词云生成 API（文本输入） ----
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

    # ---- 词云生成 API（词频文件上传） ----
    @app.route("/api/wordcloud/from-file", methods=["POST"])
    def api_wordcloud_from_file():
        """接收词频 Excel 文件（分词统计导出），返回 Base64 词云图片。

        请求格式：multipart/form-data
        - file: 词频 Excel 文件（.xls / .xlsx / .csv）
        - max_words: 最大词数（可选，默认 150）
        - colormap: 配色方案（可选，默认 dark2）
        - bg_color: 背景色（可选，默认 #ffffff）
        """
        try:
            import pandas as pd
            import tempfile
            import os as _os

            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传词频文件"}), 400

            suffix = _os.path.splitext(file.filename)[1].lower()
            if suffix not in (".xls", ".xlsx", ".csv"):
                return jsonify({
                    "success": False,
                    "error": f"不支持的文件格式：{suffix}，请上传 .xls / .xlsx / .csv"
                }), 400

            max_words = int(request.form.get("max_words", 150))
            colormap = request.form.get("colormap", "viridis")
            bg_color = request.form.get("bg_color", "#ffffff")

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name

            try:
                if suffix == ".csv":
                    df = pd.read_csv(tmp_path)
                else:
                    df = pd.read_excel(tmp_path, engine="openpyxl" if suffix == ".xlsx" else "xlrd")

                # 尝试匹配列名：支持 "词语"/"频次" 或 "word"/"count"/"freq" 等
                word_col = None
                count_col = None
                cols = [str(c).strip() for c in df.columns.tolist()]

                for c in cols:
                    if c in ("词语", "word", "Word", "term", "Term"):
                        word_col = c
                    elif c in ("频次", "count", "Count", "freq", "Freq", "frequency", "Frequency"):
                        count_col = c

                # 如果按名称找不到，回退：第一列为词，第二列为频次
                if word_col is None:
                    word_col = cols[0]
                if count_col is None:
                    count_col = cols[1] if len(cols) > 1 else None

                if count_col is None:
                    return jsonify({
                        "success": False,
                        "error": "无法识别词频文件的列结构，请确保包含「词语」和「频次」两列"
                    }), 400

                # 构建词频字典
                freq_dict = {}
                for _, row in df.iterrows():
                    word = str(row[word_col]).strip() if pd.notna(row[word_col]) else ""
                    try:
                        count = int(row[count_col])
                    except (ValueError, TypeError):
                        continue
                    if word and count > 0:
                        freq_dict[word] = count

                if not freq_dict:
                    return jsonify({
                        "success": False,
                        "error": "未能从文件中解析到有效的词频数据"
                    }), 400

                from utils.wordcloud_gen import generate_wordcloud

                b64 = generate_wordcloud(
                    freq_dict=freq_dict,
                    max_words=max_words,
                    colormap=colormap,
                    background_color=bg_color,
                )

                app.logger.info(
                    "Wordcloud (from-file) generated: %d unique words, top_n=%d",
                    len(freq_dict), max_words,
                )

                return jsonify({
                    "success": True,
                    "image_base64": b64,
                    "word_count": len(freq_dict),
                })
            finally:
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Wordcloud from-file API error")
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

    # ---- 情感分析表格预览 API ----
    @app.route("/api/sentiment/preview", methods=["POST"])
    def api_sentiment_preview():
        """接收 Excel/CSV 文件，返回列名和预览数据。"""
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
                preview_df = df.head(20).fillna("")
                rows = preview_df.values.tolist()
                rows = [[str(v) for v in row] for row in rows]

                app.logger.info(
                    "Sentiment preview: %d columns, %d preview rows (total %d rows)",
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
            app.logger.exception("Sentiment preview API error")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ---- 情感分析表格文件 API ----
    @app.route("/api/sentiment/file", methods=["POST"])
    def api_sentiment_file():
        """接收 Excel/CSV 文件 + 列名，对该列每行文本进行情感分析。"""
        try:
            import pandas as pd
            import tempfile
            import os as _os

            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"success": False, "error": "请上传表格文件"}), 400

            column = (request.form.get("column") or "").strip()
            if not column:
                return jsonify({"success": False, "error": "请选择要分析的列"}), 400

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

                col_data = df[column].dropna().astype(str)

                if len(col_data) == 0:
                    return jsonify({"success": False, "error": f"列 '{column}' 中没有有效文本"}), 400

                from utils.sentiment_analysis import analyze_sentiment, _score_to_label
                row_results = []
                all_scores = []
                pos_count = 0
                neg_count = 0
                neu_count = 0

                for text in col_data.tolist():
                    result = analyze_sentiment(text)
                    row_results.append({
                        "text": text,
                        "score": result["score"],
                        "label": result["label"],
                        "sentences": result["sentences"],
                    })
                    all_scores.append(result["score"])
                    if result["label"] == "积极":
                        pos_count += 1
                    elif result["label"] == "消极":
                        neg_count += 1
                    else:
                        neu_count += 1

                n = len(all_scores)
                avg_score = sum(all_scores) / n if n > 0 else 0.5

                app.logger.info(
                    "Sentiment file analysis done: column='%s', %d rows, avg_score=%.3f",
                    column, n, avg_score,
                )

                return jsonify({
                    "success": True,
                    "result": {
                        "score": round(avg_score, 4),
                        "label": _score_to_label(avg_score),
                        "positive_ratio": round(pos_count / n, 4) if n else 0.0,
                        "negative_ratio": round(neg_count / n, 4) if n else 0.0,
                        "neutral_ratio": round(neu_count / n, 4) if n else 0.0,
                        "row_count": n,
                        "source_column": column,
                        "rows": row_results,
                    },
                })
            finally:
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)

        except Exception as exc:
            app.logger.exception("Sentiment file API error")
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
