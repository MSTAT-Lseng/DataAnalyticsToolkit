"""词云制作 API — 文本分词生成词云、词频文件解析。"""

import os as _os

from flask import Blueprint, current_app, jsonify, request

from utils.file_helpers import ALLOWED_TABLE_EXTENSIONS, uploaded_dataframe
from utils.wordcloud_gen import generate_wordcloud

wordcloud_bp = Blueprint("wordcloud", __name__, url_prefix="/api/wordcloud")


def _parse_freq_file(df):
    """从词频 DataFrame 中自动识别词列和频次列，返回词频字典。"""
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
        return None, None, "无法识别词频文件的列结构，请确保包含「词语」和「频次」两列"

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
        return None, None, "未能从文件中解析到有效的词频数据"

    return freq_dict, word_col, None


# 延迟导入 pandas（在函数中使用时才需要）
import pandas as pd


@wordcloud_bp.route("/preview-freq", methods=["POST"])
def api_wordcloud_preview_freq():
    """接收词频 Excel 文件，返回解析后的词频预览数据。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            freq_dict, _word_col, error = _parse_freq_file(df)
            if error:
                return jsonify({"success": False, "error": error}), 400

            words = [{"word": w, "count": c} for w, c in freq_dict.items()]
            current_app.logger.info("Freq file preview: %d words parsed", len(words))

            return jsonify({
                "success": True,
                "words": words,
                "total": len(words),
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Wordcloud preview-freq API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@wordcloud_bp.route("", methods=["POST"])
def api_wordcloud():
    """接收表单 {text, max_words, colormap, bg_color}，返回 Base64 图片。"""
    try:
        text = (request.form.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "文本不能为空"}), 400

        max_words = int(request.form.get("max_words", 150))
        colormap = request.form.get("colormap", "viridis")
        bg_color = request.form.get("bg_color", "#ffffff")

        b64 = generate_wordcloud(
            text=text,
            max_words=max_words,
            colormap=colormap,
            background_color=bg_color,
        )

        current_app.logger.info("Wordcloud generated successfully")

        return jsonify({
            "success": True,
            "image_base64": b64,
        })
    except Exception as exc:
        current_app.logger.exception("Wordcloud API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@wordcloud_bp.route("/from-file", methods=["POST"])
def api_wordcloud_from_file():
    """接收词频 Excel 文件（分词统计导出），返回 Base64 词云图片。"""
    try:
        file = request.files.get("file")
        max_words = int(request.form.get("max_words", 150))
        colormap = request.form.get("colormap", "viridis")
        bg_color = request.form.get("bg_color", "#ffffff")

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            freq_dict, _word_col, error = _parse_freq_file(df)
            if error:
                return jsonify({"success": False, "error": error}), 400

            b64 = generate_wordcloud(
                freq_dict=freq_dict,
                max_words=max_words,
                colormap=colormap,
                background_color=bg_color,
            )

            current_app.logger.info(
                "Wordcloud (from-file) generated: %d unique words, top_n=%d",
                len(freq_dict), max_words,
            )

            return jsonify({
                "success": True,
                "image_base64": b64,
                "word_count": len(freq_dict),
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Wordcloud from-file API error")
        return jsonify({"success": False, "error": str(exc)}), 500
