"""回归分析 API — 一元线性回归分析（CSV 上传 / 手动输入）。"""

import os
import tempfile

from flask import Blueprint, current_app, jsonify, request

from utils.regression import linear_regression_from_csv, linear_regression_from_json

regression_bp = Blueprint("regression", __name__, url_prefix="/api/regression")


@regression_bp.route("", methods=["POST"])
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

        suffix = os.path.splitext(file.filename)[1] or ".csv"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            result = linear_regression_from_csv(tmp_path, x_column, y_column)

            current_app.logger.info(
                "Regression done: R²=%.4f, n=%d, equation=%s",
                result["r_squared"],
                result["sample_count"],
                result["equation"],
            )

            return jsonify({"success": True, "result": result})
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as exc:
        current_app.logger.exception("Regression API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@regression_bp.route("/manual", methods=["POST"])
def api_regression_manual():
    """接收 JSON {data: [{x, y}, ...]}，返回回归分析结果。"""
    try:
        data = request.get_json(force=True)
        points = data.get("data", [])

        if len(points) < 2:
            return jsonify({"success": False, "error": "至少需要 2 个数据点"}), 400

        result = linear_regression_from_json(points)

        current_app.logger.info(
            "Regression (manual) done: R²=%.4f, n=%d",
            result["r_squared"],
            result["sample_count"],
        )

        return jsonify({"success": True, "result": result})
    except Exception as exc:
        current_app.logger.exception("Regression manual API error")
        return jsonify({"success": False, "error": str(exc)}), 500
