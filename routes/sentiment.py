"""情感分析 API — 文本情感分析、自定义情感词、表格批量分析。"""

import pandas as pd

from flask import Blueprint, current_app, jsonify, request

from utils.file_helpers import ALLOWED_TABLE_EXTENSIONS, uploaded_dataframe, dataframe_preview, send_excel
from utils.sentiment_analysis import analyze_sentiment, parse_custom_sentiment, _score_to_label

sentiment_bp = Blueprint("sentiment", __name__, url_prefix="/api/sentiment")


def _parse_custom_sentiment_from_json(custom_raw):
    """从 JSON 数据中解析自定义情感词字典。"""
    if not custom_raw:
        return None

    custom_sentiment = None
    if isinstance(custom_raw, dict):
        custom_sentiment = {
            str(k).strip(): float(v)
            for k, v in custom_raw.items()
            if str(k).strip() and 0 <= float(v) <= 1
        }
    elif isinstance(custom_raw, list):
        custom_sentiment = {}
        for item in custom_raw:
            if isinstance(item, dict):
                w = str(item.get("word", "")).strip()
                s = float(item.get("score", 0.5))
                if w and 0 <= s <= 1:
                    custom_sentiment[w] = s

    return custom_sentiment or None


@sentiment_bp.route("", methods=["POST"])
def api_sentiment():
    """接收 JSON {text, custom_sentiment?}，返回情感分析结果。"""
    try:
        data = request.get_json(force=True)
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "文本不能为空"}), 400

        custom_sentiment = _parse_custom_sentiment_from_json(data.get("custom_sentiment"))

        result = analyze_sentiment(text, custom_sentiment=custom_sentiment)

        custom_count = len(custom_sentiment) if custom_sentiment else 0
        current_app.logger.info(
            "Sentiment analysis done: score=%.3f, label=%s, sentences=%d, custom_words=%d",
            result["score"],
            result["label"],
            result["sentence_count"],
            custom_count,
        )

        return jsonify({"success": True, "result": result})
    except Exception as exc:
        current_app.logger.exception("Sentiment API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@sentiment_bp.route("/export", methods=["POST"])
def api_sentiment_export():
    """接收分析结果 JSON，生成 Excel 文件并返回下载。"""
    try:
        import openpyxl

        data = request.get_json(force=True)
        rows = data.get("rows") or data.get("results") or []
        mode = data.get("mode", "text")
        summary = data.get("summary") or {}
        source_info = data.get("source_info", "")

        if not rows:
            return jsonify({"success": False, "error": "没有可导出的数据"}), 400

        wb = openpyxl.Workbook()

        # ---- Sheet 1: 详细结果 ----
        ws_detail = wb.active
        ws_detail.title = "详细分析结果"
        has_custom = any(
            (r.get("custom_words") and len(r["custom_words"]) > 0)
            for r in rows
        )
        headers = ["#", "文本", "得分", "情感"]
        if has_custom:
            headers.append("微调词")
        ws_detail.append(headers)

        for i, row in enumerate(rows, 1):
            text = str(row.get("text", ""))
            score = round(float(row.get("score", 0.5)), 4)
            label = str(row.get("label", "--"))
            row_data = [i, text, score, label]
            if has_custom:
                cw = row.get("custom_words", [])
                row_data.append(", ".join(cw) if cw else "")
            ws_detail.append(row_data)

        ws_detail.column_dimensions["A"].width = 6
        ws_detail.column_dimensions["B"].width = 60
        ws_detail.column_dimensions["C"].width = 10
        ws_detail.column_dimensions["D"].width = 10
        if has_custom:
            ws_detail.column_dimensions["E"].width = 24

        # ---- Sheet 2: 整体摘要 ----
        ws_summary = wb.create_sheet(title="情感分析摘要")
        ws_summary.append(["指标", "数值"])
        ws_summary.append(["整体情感得分", round(summary.get("score", 0), 4)])
        ws_summary.append(["整体情感标签", summary.get("label", "--")])
        ws_summary.append(["积极占比", f"{round(summary.get('positive_ratio', 0) * 100, 1)}%"])
        ws_summary.append(["中性占比", f"{round(summary.get('neutral_ratio', 0) * 100, 1)}%"])
        ws_summary.append(["消极占比", f"{round(summary.get('negative_ratio', 0) * 100, 1)}%"])
        ws_summary.append(["分析条目数", summary.get("count", len(rows))])
        if source_info:
            ws_summary.append(["数据来源", source_info])
        ws_summary.column_dimensions["A"].width = 20
        ws_summary.column_dimensions["B"].width = 20

        return send_excel(wb, "情感分析结果.xlsx")
    except Exception as exc:
        current_app.logger.exception("Sentiment export API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@sentiment_bp.route("/preview", methods=["POST"])
def api_sentiment_preview():
    """接收 Excel/CSV 文件，返回列名和预览数据。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            preview = dataframe_preview(df)
            current_app.logger.info(
                "Sentiment preview: %d columns, %d preview rows (total %d rows)",
                len(preview["columns"]), len(preview["rows"]), preview["total_rows"],
            )
            return jsonify({"success": True, **preview})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Sentiment preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@sentiment_bp.route("/file", methods=["POST"])
def api_sentiment_file():
    """接收 Excel/CSV 文件 + 列名 + 可选自定义情感词，对该列每行文本进行情感分析。"""
    try:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "请上传表格文件"}), 400

        column = (request.form.get("column") or "").strip()
        if not column:
            return jsonify({"success": False, "error": "请选择要分析的列"}), 400

        custom_raw = (request.form.get("custom_sentiment") or "").strip()
        custom_sentiment = None
        if custom_raw:
            custom_sentiment = parse_custom_sentiment(custom_raw)

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            if column not in df.columns:
                available = [str(c) for c in df.columns.tolist()]
                return jsonify({
                    "success": False,
                    "error": f"列 '{column}' 不存在。可用列：{', '.join(available)}"
                }), 400

            col_data = df[column].dropna().astype(str)

            if len(col_data) == 0:
                return jsonify({"success": False, "error": f"列 '{column}' 中没有有效文本"}), 400

            row_results = []
            all_scores = []
            pos_count = 0
            neg_count = 0
            neu_count = 0

            for text in col_data.tolist():
                result = analyze_sentiment(text, custom_sentiment=custom_sentiment)
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

            custom_count = len(custom_sentiment) if custom_sentiment else 0
            current_app.logger.info(
                "Sentiment file analysis done: column='%s', %d rows, avg_score=%.3f, custom_words=%d",
                column, n, avg_score, custom_count,
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
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Sentiment file API error")
        return jsonify({"success": False, "error": str(exc)}), 500
