"""热力分析 API：表格上传、数值列识别与相关性热力图数据。"""

import json

from flask import Blueprint, current_app, jsonify, request

from utils.file_helpers import dataframe_preview, uploaded_dataframe
from utils.heat_analysis import heatmap_values
from utils.regression import regression_column_details


heat_analysis_bp = Blueprint(
    "heat_analysis",
    __name__,
    url_prefix="/api/heat-analysis",
)


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


@heat_analysis_bp.route("/preview", methods=["POST"])
def api_heat_analysis_preview():
    """接收表格文件，返回预览数据和可用于热力分析的列。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            preview = dataframe_preview(df)
            details = regression_column_details(df)
            eligible_columns = [
                detail["name"] for detail in details if detail["eligible"]
            ]
            current_app.logger.info(
                "Heat analysis preview: %d columns, %d eligible columns, %d rows",
                len(preview["columns"]), len(eligible_columns), preview["total_rows"],
            )
            return jsonify({
                "success": True,
                **preview,
                "column_details": details,
                "eligible_columns": eligible_columns,
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Heat analysis preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@heat_analysis_bp.route("", methods=["POST"])
def api_heat_analysis():
    """接收表格文件和所选列，返回列间热力值矩阵。"""
    try:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "请上传表格文件"}), 400

        columns = _selected_columns()
        if len(columns) < 2:
            return jsonify({"success": False, "error": "请至少选择 2 列"}), 400

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            result = heatmap_values(df, columns)
            result["source_file"] = file.filename
            current_app.logger.info(
                "Heat analysis done: %d columns, %d rows",
                len(result["columns"]), result["sample_count"],
            )
            return jsonify({"success": True, "result": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Heat analysis API error")
        return jsonify({"success": False, "error": str(exc)}), 500
