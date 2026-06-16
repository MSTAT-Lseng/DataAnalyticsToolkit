"""分词统计 API — 文本分词、词频统计与导出。"""

import os as _os

from flask import Blueprint, current_app, jsonify, request

from utils.file_helpers import ALLOWED_TABLE_EXTENSIONS, uploaded_dataframe, dataframe_preview, send_excel
from utils.segmentation import segment_text

segmentation_bp = Blueprint("segmentation", __name__, url_prefix="/api/segmentation")


@segmentation_bp.route("", methods=["POST"])
def api_segmentation():
    """接收 JSON {text, top_n, remove_stopwords, extra_stopwords, extra_dict}，返回词频列表。"""
    try:
        data = request.get_json(force=True)
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "文本不能为空"}), 400

        top_n = int(data.get("top_n", 20))
        remove_stopwords = data.get("remove_stopwords", True)

        extra_list = data.get("extra_stopwords")
        extra_stopwords: set[str] | None = None
        if extra_list and isinstance(extra_list, list):
            extra_stopwords = {str(w).strip() for w in extra_list if str(w).strip()}

        dict_list = data.get("extra_dict")
        extra_dict: list[str] | None = None
        if dict_list and isinstance(dict_list, list):
            extra_dict = [str(w).strip() for w in dict_list if str(w).strip()]

        freq_dict = segment_text(
            text,
            top_n=top_n,
            remove_stopwords=remove_stopwords,
            extra_stopwords=extra_stopwords,
            extra_dict=extra_dict,
        )
        words = list(freq_dict.items())
        total_count = sum(v for _, v in words)

        current_app.logger.info(
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
        current_app.logger.exception("Segmentation API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@segmentation_bp.route("/preview", methods=["POST"])
def api_segmentation_preview():
    """接收 Excel 文件，返回列名和预览数据。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            preview = dataframe_preview(df)
            current_app.logger.info(
                "Excel preview: %d columns, %d preview rows (total %d rows)",
                len(preview["columns"]), len(preview["rows"]), preview["total_rows"],
            )
            return jsonify({"success": True, **preview})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Segmentation preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@segmentation_bp.route("/file", methods=["POST"])
def api_segmentation_file():
    """接收 Excel 文件 + 列名 + 可选自定义停用词/词典，对该列所有行进行分词统计。"""
    try:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "请上传表格文件"}), 400

        column = (request.form.get("column") or "").strip()
        if not column:
            return jsonify({"success": False, "error": "请选择要分词的列"}), 400

        top_n = int(request.form.get("top_n", 20))
        remove_stopwords = request.form.get("remove_stopwords", "true").lower() == "true"

        extra_raw = (request.form.get("extra_stopwords") or "").strip()
        extra_stopwords: set[str] | None = None
        if extra_raw:
            extra_stopwords = {w.strip() for w in extra_raw.split("\n") if w.strip()}

        dict_raw = (request.form.get("extra_dict") or "").strip()
        extra_dict: list[str] | None = None
        if dict_raw:
            extra_dict = [w.strip() for w in dict_raw.split("\n") if w.strip()]

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            if column not in df.columns:
                available = [str(c) for c in df.columns.tolist()]
                return jsonify({
                    "success": False,
                    "error": f"列 '{column}' 不存在。可用列：{', '.join(available)}"
                }), 400

            col_data = df[column].dropna().astype(str)
            combined_text = "\n".join(col_data.tolist())

            if not combined_text.strip():
                return jsonify({"success": False, "error": f"列 '{column}' 中没有有效文本"}), 400

            freq_dict = segment_text(
                combined_text,
                top_n=top_n,
                remove_stopwords=remove_stopwords,
                extra_stopwords=extra_stopwords,
                extra_dict=extra_dict,
            )
            words = list(freq_dict.items())
            total_count = sum(v for _, v in words)

            current_app.logger.info(
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
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Segmentation file API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@segmentation_bp.route("/export", methods=["POST"])
def api_segmentation_export():
    """接收与分词相同的 JSON，返回所有词频的 Excel 文件。"""
    try:
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

        return send_excel(wb, "词频统计_全部.xlsx")
    except Exception as exc:
        current_app.logger.exception("Segmentation export API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@segmentation_bp.route("/file/export", methods=["POST"])
def api_segmentation_file_export():
    """接收 Excel 文件 + 列名，返回该列所有词频的 Excel 文件。"""
    try:
        import openpyxl

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

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            col_data = df[column].dropna().astype(str)
            combined = "\n".join(col_data.tolist())

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

            return send_excel(wb, f"词频统计_{column}.xlsx")
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Segmentation file export API error")
        return jsonify({"success": False, "error": str(exc)}), 500
