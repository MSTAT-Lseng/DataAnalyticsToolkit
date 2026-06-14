"""数据清洗模块。

接收 DataFrame 和清洗策略配置，按列依次执行清洗操作。
支持：删除空值行、去重（保留首行/末行）、最小字数过滤。
"""

from typing import Dict, List, Any, Optional
import pandas as pd


# ============================================================
# 公共接口
# ============================================================

def clean_dataframe(
    df: pd.DataFrame,
    strategies: Dict[str, Dict[str, Any]],
) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """对 DataFrame 按列依次应用清洗策略。

    Args:
        df: 输入 DataFrame。
        strategies: 清洗策略配置，格式：
            {
                "列名": {
                    "remove_null": bool,          # 删除该列为空的行
                    "remove_duplicates": str|None, # "first" | "last" | None（不处理）
                    "min_length": int|None,        # 最小字数（None 或 0 表示不处理）
                },
                ...
            }

    Returns:
        (cleaned_df, stats) — 清洗后的 DataFrame 和统计信息。
        stats:
            {
                "original_rows": int,
                "cleaned_rows": int,
                "removed_rows": int,
                "steps": [
                    {"column": str, "strategy": str, "removed": int, "reason": str},
                    ...
                ],
            }
    """
    cleaned = df.copy()
    original_rows = len(cleaned)
    steps: List[Dict[str, Any]] = []

    for col, config in strategies.items():
        if col not in cleaned.columns:
            continue

        before = len(cleaned)

        # 1. 删除空值行
        if config.get("remove_null"):
            cleaned = _remove_null_rows(cleaned, col)
            after = len(cleaned)
            removed = before - after
            if removed > 0:
                steps.append({
                    "column": col,
                    "strategy": "删除空值",
                    "removed": removed,
                    "reason": f"列「{col}」中值为空的行",
                })
                before = after

        # 2. 去重
        dup_mode = config.get("remove_duplicates")
        if dup_mode in ("first", "last"):
            cleaned = _remove_duplicate_rows(cleaned, col, keep=dup_mode)
            after = len(cleaned)
            removed = before - after
            if removed > 0:
                label = "保留首行" if dup_mode == "first" else "保留末行"
                steps.append({
                    "column": col,
                    "strategy": f"去重（{label}）",
                    "removed": removed,
                    "reason": f"列「{col}」中重复的行（{label}）",
                })
                before = after

        # 3. 最小字数过滤
        min_len = config.get("min_length")
        if min_len and min_len > 0:
            cleaned = _remove_short_rows(cleaned, col, min_len)
            after = len(cleaned)
            removed = before - after
            if removed > 0:
                steps.append({
                    "column": col,
                    "strategy": f"最小字数 ≥ {min_len}",
                    "removed": removed,
                    "reason": f"列「{col}」中字数少于 {min_len} 的行",
                })

    total_removed = original_rows - len(cleaned)

    stats = {
        "original_rows": original_rows,
        "cleaned_rows": len(cleaned),
        "removed_rows": total_removed,
        "steps": steps,
    }

    return cleaned, stats


# ============================================================
# 内部辅助
# ============================================================

def _remove_null_rows(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """删除指定列中值为空（NaN、空字符串、仅空白）的行。"""
    mask = df[col].notna() & (df[col].astype(str).str.strip() != "")
    return df.loc[mask].copy()


def _remove_duplicate_rows(
    df: pd.DataFrame,
    col: str,
    keep: str = "first",
) -> pd.DataFrame:
    """删除指定列中重复的行。

    Args:
        df: DataFrame。
        col: 列名。
        keep: "first" 保留首次出现，"last" 保留末次出现。

    Returns:
        去重后的 DataFrame。
    """
    return df.drop_duplicates(subset=[col], keep=keep).copy()


def _remove_short_rows(
    df: pd.DataFrame,
    col: str,
    min_length: int,
) -> pd.DataFrame:
    """删除指定列中文本字数少于 min_length 的行。"""
    mask = df[col].astype(str).str.len() >= min_length
    return df.loc[mask].copy()
