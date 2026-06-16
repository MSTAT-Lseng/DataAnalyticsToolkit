"""数据清洗 API — 表格数据清洗（去空值、去重、长度过滤）与结果导出。"""

import json as _json

import pandas as pd

from flask import Blueprint, current_app, jsonify, request

from utils.cleaning import clean_dataframe
from utils.file_helpers import ALLOWED_TABLE_EXTENSIONS, uploaded_dataframe, dataframe_preview, send_excel

cleaning_bp = Blueprint("cleaning", __name__, url_prefix="/api/cleaning")


def _validate_strategies(strategies: dict) -> bool:
    """检查策略配置中是否至少有一个有效策略。"""
    for col, config in strategies.items():
        if config.get("remove_null") or \
           config.get("remove_duplicates") in ("first", "last") or \
           (config.get("min_length") and config["min_length"] > 0):
            return True
    return False


@cleaning_bp.route("/preview", methods=["POST"])
def api_cleaning_preview():
    """接收表格文件，返回列名和预览数据。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            preview = dataframe_preview(df)
            current_app.logger.info(
                "Cleaning preview: %d columns, %d preview rows (total %d rows)",
                len(preview["columns"]), len(preview["rows"]), preview["total_rows"],
            )
            return jsonify({"success": True, **preview})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Cleaning preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@cleaning_bp.route("/process", methods=["POST"])
def api_cleaning_process():
    """接收表格文件 + 清洗策略，执行清洗并返回结果预览。"""
    try:
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "请上传表格文件"}), 400

        strategies_raw = (request.form.get("strategies") or "").strip()
        if not strategies_raw:
            return jsonify({"success": False, "error": "请至少为一列配置清洗策略"}), 400

        try:
            strategies = _json.loads(strategies_raw)
        except _json.JSONDecodeError:
            return jsonify({"success": False, "error": "策略配置格式错误"}), 400

        if not _validate_strategies(strategies):
            return jsonify({"success": False, "error": "请至少为一列配置清洗策略"}), 400

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            cleaned_df, stats = clean_dataframe(df, strategies)

            preview_rows = cleaned_df.head(20).fillna("").values.tolist()
            preview_rows = [[str(v) for v in row] for row in preview_rows]
            columns = [str(c) for c in cleaned_df.columns.tolist()]

            current_app.logger.info(
                "Cleaning done: %d → %d rows (%d removed), %d steps",
                stats["original_rows"], stats["cleaned_rows"],
                stats["removed_rows"], len(stats["steps"]),
            )

            return jsonify({
                "success": True,
                "columns": columns,
                "preview_rows": preview_rows,
                "stats": stats,
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Cleaning process API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@cleaning_bp.route("/export", methods=["POST"])
def api_cleaning_export():
    """接收表格文件 + 清洗策略，返回清洗后的 Excel 文件。"""
    try:
        import openpyxl

        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "请上传表格文件"}), 400

        strategies_raw = (request.form.get("strategies") or "").strip()
        strategies = _json.loads(strategies_raw) if strategies_raw else {}

        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            cleaned_df, stats = clean_dataframe(df, strategies)

            wb = openpyxl.Workbook()

            # Sheet 1: 清洗统计
            ws_stats = wb.active
            ws_stats.title = "清洗统计"
            ws_stats.append(["指标", "数值"])
            ws_stats.append(["原始行数", stats["original_rows"]])
            ws_stats.append(["清洗后行数", stats["cleaned_rows"]])
            ws_stats.append(["删除行数", stats["removed_rows"]])
            ws_stats.append([""])
            ws_stats.append(["清洗步骤", "列", "删除行数", "说明"])
            for step in stats["steps"]:
                ws_stats.append([
                    step["strategy"], step["column"],
                    step["removed"], step["reason"],
                ])
            ws_stats.column_dimensions["A"].width = 18
            ws_stats.column_dimensions["B"].width = 16
            ws_stats.column_dimensions["C"].width = 12
            ws_stats.column_dimensions["D"].width = 40

            # Sheet 2: 清洗后数据
            ws_data = wb.create_sheet(title="清洗后数据")
            ws_data.append([str(c) for c in cleaned_df.columns.tolist()])
            for _, row in cleaned_df.iterrows():
                ws_data.append([str(v) if pd.notna(v) else "" for v in row.tolist()])

            return send_excel(wb, "清洗后数据.xlsx")
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Cleaning export API error")
        return jsonify({"success": False, "error": str(exc)}), 500
