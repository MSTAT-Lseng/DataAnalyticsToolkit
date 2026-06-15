"""维度挖掘 — 基于关键词匹配的文本维度评分引擎。

根据用户定义的维度（名称 + 关键词/正则 + 分数），对文本数据逐行打分，
输出每个维度在每条文本上的评分（0–100 百分制）及整体统计。

算法：
- 每行文本对每个维度的每个关键词进行匹配（支持正则表达式）
- 匹配到关键词时取各关键词分数的最大值作为该行该维度的得分
- 未匹配到任何关键词时该行该维度得分为 0
- 整体维度得分 = 所有行该维度得分的均值
"""

import re
from typing import Any


def _compile_pattern(keyword: dict[str, Any]) -> tuple[re.Pattern, int, str]:
    """将关键词配置编译为正则对象。

    Args:
        keyword: {"pattern": str, "score": int, "is_regex": bool}

    Returns:
        (compiled_pattern, score, original_pattern_string)
    """
    pattern_str = str(keyword.get("pattern", "")).strip()
    score = int(keyword.get("score", 0))
    is_regex = bool(keyword.get("is_regex", False))

    if not pattern_str:
        raise ValueError("关键词模式不能为空")

    # 限制分数范围
    score = max(0, min(100, score))

    if is_regex:
        # 用户提供了正则表达式，直接编译
        try:
            compiled = re.compile(pattern_str, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f"正则表达式语法错误「{pattern_str}」: {exc}") from exc
    else:
        # 普通关键词 → 转义后作为子串匹配
        escaped = re.escape(pattern_str)
        compiled = re.compile(escaped, re.IGNORECASE)

    return compiled, score, pattern_str


def mine_dimensions(
    texts: list[str],
    dimensions: list[dict[str, Any]],
) -> dict[str, Any]:
    """对文本列表执行维度挖掘分析。

    Args:
        texts: 文本字符串列表（每行一条）
        dimensions: 维度配置列表，每项格式：
            {
                "name": "维度名称",
                "keywords": [
                    {"pattern": "关键词或正则", "score": 80, "is_regex": false},
                    ...
                ]
            }

    Returns:
        {
            "dimensions": [
                {
                    "name": "维度名称",
                    "overall_score": 65.2,
                    "match_count": 45,
                    "match_rate": 0.75,
                    "keywords_matched": {"关键词A": 12, "关键词B": 33},
                }
            ],
            "row_results": [
                {
                    "index": 0,
                    "text": "原始文本",
                    "scores": {"维度A": 80, "维度B": 0},
                    "matches": {"维度A": ["匹配词A"], "维度B": []},
                }
            ],
            "total_rows": 60,
            "dimension_count": 3,
        }
    """
    if not texts:
        raise ValueError("文本数据不能为空")

    if not dimensions:
        raise ValueError("至少需要定义一个维度")

    # ---- 预编译所有关键词模式 ----
    dim_configs: list[dict[str, Any]] = []
    for dim in dimensions:
        name = str(dim.get("name", "")).strip()
        if not name:
            raise ValueError("维度名称不能为空")

        keywords_raw = dim.get("keywords", [])
        if not keywords_raw or not isinstance(keywords_raw, list):
            raise ValueError(f"维度「{name}」至少需要一个关键词")

        compiled_keywords: list[tuple[re.Pattern, int, str]] = []
        for kw in keywords_raw:
            compiled, score, original = _compile_pattern(kw)
            compiled_keywords.append((compiled, score, original))

        dim_configs.append({
            "name": name,
            "keywords": compiled_keywords,
        })

    # ---- 逐行打分 ----
    row_results: list[dict[str, Any]] = []
    # 累计统计
    dim_scores_sum: dict[str, float] = {d["name"]: 0.0 for d in dim_configs}
    dim_match_counts: dict[str, int] = {d["name"]: 0 for d in dim_configs}
    # 关键词级别统计
    dim_kw_counts: dict[str, dict[str, int]] = {
        d["name"]: {} for d in dim_configs
    }

    for idx, text in enumerate(texts):
        text = str(text).strip()
        if not text:
            # 空文本全部打 0 分
            row_scores = {d["name"]: 0 for d in dim_configs}
            row_matches = {d["name"]: [] for d in dim_configs}
            row_results.append({
                "index": idx,
                "text": text or "(空)",
                "scores": row_scores,
                "matches": row_matches,
            })
            continue

        row_scores: dict[str, int] = {}
        row_matches: dict[str, list[str]] = {}

        for dc in dim_configs:
            dim_name = dc["name"]
            best_score = 0
            matched_keywords: list[str] = []

            for compiled, score, original in dc["keywords"]:
                if compiled.search(text):
                    if score > best_score:
                        best_score = score
                    matched_keywords.append(original)
                    # 关键词级别统计
                    dim_kw_counts[dim_name][original] = \
                        dim_kw_counts[dim_name].get(original, 0) + 1

            row_scores[dim_name] = best_score
            row_matches[dim_name] = matched_keywords

            dim_scores_sum[dim_name] += best_score
            if best_score > 0:
                dim_match_counts[dim_name] += 1

        row_results.append({
            "index": idx,
            "text": text,
            "scores": row_scores,
            "matches": row_matches,
        })

    # ---- 汇总维度统计 ----
    n = len(texts)
    dim_summary: list[dict[str, Any]] = []
    for dc in dim_configs:
        dim_name = dc["name"]
        overall = round(dim_scores_sum[dim_name] / n, 2) if n > 0 else 0.0
        match_count = dim_match_counts[dim_name]
        match_rate = round(match_count / n, 4) if n > 0 else 0.0

        # 关键词匹配次数（按频次降序）
        kw_counts = dim_kw_counts.get(dim_name, {})
        kw_sorted = sorted(kw_counts.items(), key=lambda x: -x[1])

        dim_summary.append({
            "name": dim_name,
            "overall_score": overall,
            "match_count": match_count,
            "match_rate": match_rate,
            "keywords_matched": dict(kw_sorted),
        })

    return {
        "dimensions": dim_summary,
        "row_results": row_results,
        "total_rows": n,
        "dimension_count": len(dim_configs),
    }
