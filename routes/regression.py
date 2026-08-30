"""回归分析 API：表格上传、数值列识别与多列两两回归。"""

import json

from flask import Blueprint, current_app, jsonify, request

from utils.file_helpers import dataframe_preview, uploaded_dataframe
from utils.regression import pairwise_regression, regression_column_details


regression_bp = Blueprint("regression", __name__, url_prefix="/api/regression")


def _selected_columns() -> list[str]:
    """解析 FormData 中的列名 JSON 数组。"""
    raw = (request.form.get("columns") or "").strip()
    if not raw:
        raise ValueError("请选择至少 2 列")
    try:
        columns = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("列选择格式错误") from exc
    if not isinstance(columns, list) or not all(isinstance(column, str) for column in columns):
        raise ValueError("列选择必须是列名数组")
    return [column.strip() for column in columns if column.strip()]


@regression_bp.route("/preview", methods=["POST"])
def api_regression_preview():
    """接收表格文件，返回预览数据和可用于回归的列。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            preview = dataframe_preview(df)
            column_details = regression_column_details(df)
            eligible_columns = [
                detail["name"]
                for detail in column_details
                if detail["eligible"]
            ]

            current_app.logger.info(
                "Regression preview: %d columns, %d eligible columns, %d rows",
                len(preview["columns"]), len(eligible_columns), preview["total_rows"],
            )
            return jsonify({
                "success": True,
                **preview,
                "column_details": column_details,
                "eligible_columns": eligible_columns,
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Regression preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@regression_bp.route("", methods=["POST"])
def api_regression():
    """接收表格文件和所选列，返回所有两两组合的回归结果。"""
    try:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "请上传表格文件"}), 400

        columns = _selected_columns()
        if len(columns) < 2:
            return jsonify({"success": False, "error": "请至少选择 2 列"}), 400

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            results = pairwise_regression(df, columns)
            result = {
                "selected_columns": columns,
                "pair_count": len(results),
                "results": results,
                "source_file": file.filename,
            }

            current_app.logger.info(
                "Regression done: %d pairs from %d selected columns",
                len(results), len(columns),
            )
            return jsonify({"success": True, "result": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Regression API error")
        return jsonify({"success": False, "error": str(exc)}), 500
