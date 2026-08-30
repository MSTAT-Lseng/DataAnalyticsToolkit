"""回归分析业务模块。

回归分析只接受表格文件中的数值列。合格列的表头来自文件第一行，
其余每一行都必须是 1 到 10（含边界）的数字，支持小数。
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


REGRESSION_MIN_VALUE = 1.0
REGRESSION_MAX_VALUE = 10.0


def _column_name(value: Any) -> str:
    """将 pandas 表头转换成前后端统一使用的字符串。"""
    return str(value)


def _validate_headers(df: pd.DataFrame) -> list[str]:
    """校验表头，避免重复列名导致列选择含义不明确。"""
    names = [_column_name(column) for column in df.columns.tolist()]
    if len(names) != len(set(names)):
        raise ValueError("表格的标题列名不能重复，请修改第一行标题后重新上传")
    return names


def _numeric_column(series: pd.Series) -> pd.Series:
    """将一列转换为数值，同时保留无效值为 NaN 供校验使用。"""
    return pd.to_numeric(series, errors="coerce")


def regression_column_details(df: pd.DataFrame) -> list[dict[str, Any]]:
    """返回每一列是否符合回归分析要求的详细信息。"""
    names = _validate_headers(df)
    details: list[dict[str, Any]] = []

    for position, name in enumerate(names):
        series = df.iloc[:, position]
        numeric = _numeric_column(series)
        numeric_values = numeric.to_numpy(dtype=float)
        finite = np.isfinite(numeric_values)
        invalid_numeric = numeric.isna() | ~finite
        if pd.api.types.is_bool_dtype(series):
            invalid_numeric = pd.Series(True, index=series.index)
        out_of_range = (~invalid_numeric) & (
            (numeric < REGRESSION_MIN_VALUE) | (numeric > REGRESSION_MAX_VALUE)
        )
        valid_values = numeric[~invalid_numeric]

        if len(series) < 2:
            reason = "至少需要 2 行数据"
        elif invalid_numeric.any():
            reason = "包含空值或非数字"
        elif out_of_range.any():
            reason = "存在不在 1-10 范围内的数值"
        else:
            reason = "可用于回归"

        eligible = (
            len(series) >= 2
            and not invalid_numeric.any()
            and not out_of_range.any()
        )
        details.append({
            "name": name,
            "eligible": eligible,
            "sample_count": int(len(valid_values)),
            "min": float(valid_values.min()) if len(valid_values) else None,
            "max": float(valid_values.max()) if len(valid_values) else None,
            "reason": reason,
        })

    return details


def eligible_regression_columns(df: pd.DataFrame) -> list[str]:
    """返回所有符合回归要求的列名。"""
    return [
        detail["name"]
        for detail in regression_column_details(df)
        if detail["eligible"]
    ]


def _selected_numeric_columns(
    df: pd.DataFrame,
    columns: list[str],
) -> dict[str, np.ndarray]:
    """验证用户选择的列，并返回可建模的数值数组。"""
    names = _validate_headers(df)
    if len(columns) < 2:
        raise ValueError("请至少选择 2 列进行回归分析")

    selected = [str(column) for column in columns]
    if len(selected) != len(set(selected)):
        raise ValueError("不能重复选择同一列")

    missing = [column for column in selected if column not in names]
    if missing:
        raise ValueError(f"选择的列不存在：{', '.join(missing)}")

    details = {
        detail["name"]: detail
        for detail in regression_column_details(df)
    }
    invalid = [
        column for column in selected
        if not details[column]["eligible"]
    ]
    if invalid:
        raise ValueError(
            f"以下列不符合要求，只能选择全部为 1-10 数值的列：{', '.join(invalid)}"
        )

    return {
        column: _numeric_column(df.iloc[:, names.index(column)]).to_numpy(dtype=float)
        for column in selected
    }


def pairwise_regression(
    df: pd.DataFrame,
    columns: list[str],
) -> list[Dict[str, Any]]:
    """对所选列按顺序进行两两组合回归。

    每个组合的前一列作为自变量 X，后一列作为因变量 Y。例如选择
    A、B、C 会生成 A→B、A→C、B→C 三张图。
    """
    numeric_columns = _selected_numeric_columns(df, columns)
    results: list[Dict[str, Any]] = []

    for x_column, y_column in combinations(columns, 2):
        result = linear_regression(
            numeric_columns[x_column],
            numeric_columns[y_column],
            x_label=x_column,
            y_label=y_column,
        )
        result["x_column"] = x_column
        result["y_column"] = y_column
        results.append(result)

    return results


def linear_regression_from_csv(
    filepath: str,
    x_column: str,
    y_column: str,
) -> Dict[str, Any]:
    """兼容旧的单对 CSV 调用，同时沿用新的数值列校验。"""
    df = pd.read_csv(filepath)
    return pairwise_regression(df, [x_column, y_column])[0]


def linear_regression(
    x: np.ndarray | List[float],
    y: np.ndarray | List[float],
    x_label: str = "X",
    y_label: str = "Y",
) -> Dict[str, Any]:
    """执行一元线性回归并返回前端绘图所需的数据。"""
    x_arr = np.asarray(x, dtype=float).reshape(-1, 1)
    y_arr = np.asarray(y, dtype=float).reshape(-1)

    if len(x_arr) != len(y_arr):
        raise ValueError("X 和 Y 的有效数据行数必须一致")
    if len(x_arr) < 2:
        raise ValueError("至少需要 2 个样本点才能进行回归分析")
    if not np.isfinite(x_arr).all() or not np.isfinite(y_arr).all():
        raise ValueError("回归数据必须是有限数值")

    model = LinearRegression()
    model.fit(x_arr, y_arr)
    y_pred = model.predict(x_arr)

    intercept = float(model.intercept_)
    slope = float(model.coef_[0])
    r_squared = float(r2_score(y_arr, y_pred))
    mse = float(mean_squared_error(y_arr, y_pred))
    sign = "+" if slope >= 0 else "-"
    equation = f"{y_label} = {intercept:.4f} {sign} {abs(slope):.4f}·{x_label}"

    x_line = [float(np.min(x_arr)), float(np.max(x_arr))]
    y_line = [
        float(value)
        for value in model.predict(np.asarray(x_line).reshape(-1, 1))
    ]

    return {
        "coefficients": [intercept, slope],
        "intercept": intercept,
        "slope": slope,
        "r_squared": round(r_squared, 6),
        "mse": round(mse, 6),
        "equation": equation,
        "x_values": x_arr.flatten().tolist(),
        "y_true": y_arr.tolist(),
        "y_pred": y_pred.tolist(),
        "x_line": x_line,
        "y_line": y_line,
        "x_label": x_label,
        "y_label": y_label,
        "sample_count": len(x_arr),
    }
