"""社会网络关系图 API — 分词准备、分词结果表导入与共现关系图。"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from utils.file_helpers import dataframe_preview, uploaded_dataframe
from utils.social_network import (
    MAX_SEGMENTATION_WORDS,
    build_cooccurrence_graph,
    parse_frequency_dataframe,
    prepare_network_data,
    split_documents,
)


social_network_bp = Blueprint(
    "social_network",
    __name__,
    url_prefix="/api/social-network",
)


def _parse_word_list(raw: Any, field_name: str) -> list[str]:
    """解析前端传来的词条 JSON 数组。"""
    if not raw:
        return []
    if isinstance(raw, list):
        values = raw
    else:
        try:
            values = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name}格式错误") from exc
    if not isinstance(values, list):
        raise ValueError(f"{field_name}必须是词条数组")
    return list(dict.fromkeys(
        str(value).strip() for value in values if str(value).strip()
    ))


def _parse_int(raw: str | None, default: int, field_name: str) -> int:
    try:
        return int(raw) if raw not in (None, "") else default
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name}必须是整数") from exc


def _json_payload() -> dict[str, Any]:
    if not request.is_json:
        return {}
    payload = request.get_json(silent=True)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("请求 JSON 必须是对象")
    return payload


def _request_value(name: str, default: Any = None) -> Any:
    payload = _json_payload()
    if payload:
        return payload.get(name, default)
    return request.form.get(name, default)


@contextmanager
def _request_documents():
    """读取当前请求中的文本或表格列，并在离开上下文后清理临时文件。"""
    raw_mode = _request_value("mode", "text")
    mode = str(raw_mode or "text").strip().lower()
    if mode == "text":
        text = str(_request_value("text", "") or "").strip()
        if not text:
            raise ValueError("文本不能为空")
        documents = split_documents(text)
        if not documents:
            raise ValueError("文本中没有可分析的内容")
        yield documents, {"mode": "text", "source_column": ""}
        return

    if mode != "table":
        raise ValueError("输入模式必须是 text 或 table")

    file = request.files.get("file")
    column = str(_request_value("column", "") or "").strip()
    if not column:
        raise ValueError("请选择要分词的列")

    with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
        if column not in df.columns:
            available = ", ".join(str(value) for value in df.columns.tolist())
            raise ValueError(f"列 '{column}' 不存在。可用列：{available}")
        documents = df[column].dropna().astype(str).tolist()
        documents = [document.strip() for document in documents if document.strip()]
        if not documents:
            raise ValueError(f"列 '{column}' 中没有有效文本")
        yield documents, {
            "mode": "table",
            "source_column": column,
            "source_file": file.filename,
        }


@social_network_bp.route("/preview", methods=["POST"])
def api_social_network_preview():
    """预览表格列，供用户选择社会网络关系图的文本来源。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            return jsonify({"success": True, **dataframe_preview(df)})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Social network preview API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@social_network_bp.route("/import-frequency", methods=["POST"])
def api_social_network_import_frequency():
    """导入分词统计功能导出的词频表，返回可用于配置的词条列表。"""
    try:
        file = request.files.get("file")
        with uploaded_dataframe(file) as (df, _suffix, _tmp_path):
            words, word_column = parse_frequency_dataframe(df)
            current_app.logger.info(
                "Social network frequency table imported: %d words, column='%s'",
                len(words), word_column,
            )
            return jsonify({
                "success": True,
                "words": words,
                "count": len(words),
                "max_words": MAX_SEGMENTATION_WORDS,
                "word_column": word_column,
                "source_file": file.filename,
            })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Social network frequency import API error")
        return jsonify({"success": False, "error": str(exc)}), 500


def _network_options() -> dict[str, Any]:
    return {
        "segmentation_words": _parse_word_list(
            _request_value("segmentation_words"), "分词规则词表"
        ),
        "window_size": _parse_int(
            _request_value("window_size"), 4, "共现窗口"
        ),
        "min_frequency": _parse_int(
            _request_value("min_frequency"), 1, "最小词频"
        ),
        "max_nodes": _parse_int(
            _request_value("max_nodes"), 60, "最多节点数"
        ),
        "max_edges": _parse_int(
            _request_value("max_edges"), 180, "最多关系数"
        ),
    }


@social_network_bp.route("/prepare", methods=["POST"])
def api_social_network_prepare():
    """按当前来源和导入词表完成分词，返回绘图前的数据摘要。"""
    try:
        options = _network_options()
        with _request_documents() as (documents, source):
            result = prepare_network_data(
                documents,
                segmentation_words=options["segmentation_words"],
            )
            result.update(source)
            current_app.logger.info(
                "Social network data prepared: mode=%s, documents=%d, tokens=%d",
                source["mode"], result["document_count"], result["token_count"],
            )
            return jsonify({"success": True, "result": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Social network prepare API error")
        return jsonify({"success": False, "error": str(exc)}), 500


@social_network_bp.route("", methods=["POST"])
@social_network_bp.route("/graph", methods=["POST"])
@social_network_bp.route("/analyze", methods=["POST"])
def api_social_network_graph():
    """根据原始文本、导入词表和共现参数生成关系图数据。"""
    try:
        options = _network_options()
        with _request_documents() as (documents, source):
            result = build_cooccurrence_graph(
                documents,
                segmentation_words=options["segmentation_words"],
                window_size=options["window_size"],
                min_frequency=options["min_frequency"],
                max_nodes=options["max_nodes"],
                max_edges=options["max_edges"],
            )
            result.update(source)
            current_app.logger.info(
                "Social network graph generated: nodes=%d, edges=%d",
                result["node_count"], result["edge_count"],
            )
            return jsonify({"success": True, "result": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Social network graph API error")
        return jsonify({"success": False, "error": str(exc)}), 500
