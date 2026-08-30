"""热力分析 API：表格上传、数值列识别与相关性热力图数据。"""

import json

from flask import Blueprint, current_app, jsonify, request

from utils.clustering import (
    clustering_column_details,
    cluster_documents,
    dataframe_column_texts,
    split_sentences,
)
from utils.file_helpers import dataframe_preview, send_excel, uploaded_dataframe
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


@heat_analysis_bp.route("/clustering/preview", methods=["POST"])
def api_heat_clustering_preview():
    """接收表格文件，返回可用于聚类的列。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            preview = dataframe_preview(df)
            details = clustering_column_details(df)
            current_app.logger.info(
                "Clustering preview: %d columns, %d eligible columns, %d rows",
                len(preview["columns"]),
                sum(detail["eligible"] for detail in details),
                preview["total_rows"],
            )
            return jsonify({
                "success": True,
                **preview,
                "column_details": details,
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Clustering preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@heat_analysis_bp.route("/clustering", methods=["POST"])
def api_heat_clustering():
    """接收文本或表格列，执行 TF-IDF + K-Means 聚类。"""
    try:
        mode = (request.form.get("mode") or "text").strip().lower()
        raw_clusters = (request.form.get("n_clusters") or "").strip()
        remove_stopwords = (request.form.get("remove_stopwords", "true").strip().lower()
                            not in {"false", "0", "no", "off"})
        extra_stopwords = {
            word.strip().lower()
            for word in (request.form.get("extra_stopwords") or "").splitlines()
            if word.strip()
        }
        if not raw_clusters:
            return jsonify({"success": False, "error": "请输入聚类数量"}), 400

        if mode == "text":
            sentences = split_sentences(request.form.get("text") or "")
            if len(sentences) < 2:
                return jsonify({"success": False, "error": "文本至少需要 2 个句子才能进行聚类"}), 400
            result = cluster_documents(
                sentences,
                raw_clusters,
                item_indices=list(range(1, len(sentences) + 1)),
                remove_stopwords=remove_stopwords,
                extra_stopwords=extra_stopwords,
            )
            result.update({
                "source_mode": "text",
                "source_label": "文本输入 · 按句子拆分",
                "remove_stopwords": remove_stopwords,
                "extra_stopword_count": len(extra_stopwords),
            })
        elif mode == "table":
            file = request.files.get("file")
            column = (request.form.get("column") or "").strip()
            if not column:
                return jsonify({"success": False, "error": "请选择要聚类的列"}), 400
            with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
                documents, row_numbers = dataframe_column_texts(df, column)
                result = cluster_documents(
                    documents,
                    raw_clusters,
                    row_numbers,
                    remove_stopwords=remove_stopwords,
                    extra_stopwords=extra_stopwords,
                )
                result.update({
                    "source_mode": "table",
                    "source_file": file.filename,
                    "source_column": column,
                    "source_label": f"{file.filename} · {column} 列",
                    "remove_stopwords": remove_stopwords,
                    "extra_stopword_count": len(extra_stopwords),
                })
        else:
            return jsonify({"success": False, "error": "不支持的聚类输入模式"}), 400

        current_app.logger.info(
            "Clustering done: mode=%s, documents=%d, clusters=%d",
            mode, result["document_count"], result["n_clusters"],
        )
        return jsonify({"success": True, "result": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Clustering API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@heat_analysis_bp.route("/clustering/export", methods=["POST"])
def api_heat_clustering_export():
    """接收聚类结果 JSON，生成包含摘要和样本归属的 Excel 文件。"""
    try:
        import openpyxl

        payload = request.get_json(force=True) or {}
        if not isinstance(payload, dict):
            raise ValueError("导出数据格式错误")
        result = payload.get("result", payload) or {}
        if not isinstance(result, dict):
            raise ValueError("聚类结果格式错误")
        clusters = result.get("clusters") or []
        items = result.get("items") or []
        if not clusters or not items:
            return jsonify({"success": False, "error": "没有可导出的聚类结果"}), 400

        workbook = openpyxl.Workbook()

        summary_sheet = workbook.active
        summary_sheet.title = "聚类摘要"
        summary_sheet.append(["指标", "数值"])
        summary_sheet.append(["分析方法", result.get("method", "TF-IDF + K-Means")])
        summary_sheet.append(["数据来源", result.get("source_label", "")])
        summary_sheet.append(["过滤停用词", "是" if result.get("remove_stopwords", True) else "否"])
        summary_sheet.append(["自定义停用词数", result.get("extra_stopword_count", 0)])
        summary_sheet.append(["样本数", result.get("document_count", len(items))])
        summary_sheet.append(["聚类数", result.get("n_clusters", len(clusters))])
        summary_sheet.append(["TF-IDF 特征数", result.get("feature_count", "")])
        summary_sheet.append([])
        summary_sheet.append(["聚类编号", "聚类名称", "样本数", "关键词"])
        for cluster in clusters:
            summary_sheet.append([
                cluster.get("id", ""),
                cluster.get("label", ""),
                cluster.get("size", 0),
                ", ".join(str(keyword) for keyword in (cluster.get("keywords") or [])),
            ])
        summary_sheet.column_dimensions["A"].width = 18
        summary_sheet.column_dimensions["B"].width = 28
        summary_sheet.column_dimensions["C"].width = 12
        summary_sheet.column_dimensions["D"].width = 46

        detail_sheet = workbook.create_sheet(title="样本归属")
        detail_sheet.append([
            "序号", "聚类编号", "聚类名称", "文本", "中心距离",
            "TF-IDF 维度 1", "TF-IDF 维度 2",
        ])
        for item in items:
            detail_sheet.append([
                item.get("index", ""),
                item.get("cluster", ""),
                item.get("cluster_label", ""),
                item.get("text", ""),
                item.get("distance", ""),
                item.get("x", ""),
                item.get("y", ""),
            ])
        detail_sheet.column_dimensions["A"].width = 10
        detail_sheet.column_dimensions["B"].width = 12
        detail_sheet.column_dimensions["C"].width = 18
        detail_sheet.column_dimensions["D"].width = 60
        detail_sheet.column_dimensions["E"].width = 14
        detail_sheet.column_dimensions["F"].width = 18
        detail_sheet.column_dimensions["G"].width = 18
        detail_sheet.freeze_panes = "A2"

        return send_excel(workbook, "聚类分析结果.xlsx")
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Clustering export API error")
        return jsonify({"success": False, "error": str(exc)}), 500
