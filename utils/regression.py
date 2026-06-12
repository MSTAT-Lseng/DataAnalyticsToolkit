"""回归分析模块。

支持从 CSV 文件或 JSON 数据中进行线性回归分析，
使用 scikit-learn 建模并返回可用于 Plotly 前端绘图的结构化数据。
"""

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error


# ============================================================
# 公共接口
# ============================================================

def linear_regression_from_csv(
    filepath: str,
    x_column: str,
    y_column: str,
) -> Dict:
    """从 CSV 文件读取数据并进行线性回归。

    Args:
        filepath: CSV 文件路径。
        x_column: 自变量列名。
        y_column: 因变量列名。

    Returns:
        包含回归结果的字典（结构见 linear_regression 函数）。
    """
    df = pd.read_csv(filepath)

    if x_column not in df.columns or y_column not in df.columns:
        available = list(df.columns)
        raise ValueError(
            f"列名不存在。需要 '{x_column}' 和 '{y_column}'，文件包含: {available}"
        )

    # 删除缺失值
    df_clean = df[[x_column, y_column]].dropna()

    x = df_clean[x_column].values.astype(float)
    y = df_clean[y_column].values.astype(float)

    return linear_regression(x, y, x_label=x_column, y_label=y_column)


def linear_regression(
    x: np.ndarray | List[float],
    y: np.ndarray | List[float],
    x_label: str = "X",
    y_label: str = "Y",
) -> Dict:
    """执行线性回归分析。

    Args:
        x: 自变量数组。
        y: 因变量数组。
        x_label: X 轴标签。
        y_label: Y 轴标签。

    Returns:
        {
            "coefficients": [b0, b1],     # 截距 + 斜率
            "intercept": float,            # 截距 b0
            "slope": float,                # 斜率 b1
            "r_squared": float,            # R² 决定系数
            "mse": float,                  # 均方误差
            "equation": str,               # 方程字符串（如 "Y = 2.50 + 1.30·X"）
            "x_values": [...],             # 原始 X 值
            "y_true": [...],               # 原始 Y 值
            "y_pred": [...],               # 预测 Y 值
            "x_label": str,                # X 轴标签
            "y_label": str,                # Y 轴标签
            "sample_count": int,           # 有效样本数
        }
    """
    # ---- 数据准备 ----
    x_arr = np.asarray(x, dtype=float).reshape(-1, 1)
    y_arr = np.asarray(y, dtype=float)

    if len(x_arr) < 2:
        raise ValueError("至少需要 2 个样本点才能进行回归分析")

    # ---- 建模 ----
    model = LinearRegression()
    model.fit(x_arr, y_arr)

    y_pred = model.predict(x_arr)

    b0 = float(model.intercept_)
    b1 = float(model.coef_[0])
    r2 = float(r2_score(y_arr, y_pred))
    mse = float(mean_squared_error(y_arr, y_pred))

    # 构造方程
    sign = "+" if b1 >= 0 else "-"
    equation = f"{y_label} = {b0:.4f} {sign} {abs(b1):.4f}·{x_label}"

    return {
        "coefficients": [b0, b1],
        "intercept": b0,
        "slope": b1,
        "r_squared": round(r2, 6),
        "mse": round(mse, 6),
        "equation": equation,
        "x_values": x_arr.flatten().tolist(),
        "y_true": y_arr.tolist(),
        "y_pred": y_pred.tolist(),
        "x_label": x_label,
        "y_label": y_label,
        "sample_count": len(x_arr),
    }


def linear_regression_from_json(
    data: List[Dict],
    x_key: str = "x",
    y_key: str = "y",
) -> Dict:
    """从 JSON 数据中进行线性回归。

    Args:
        data: [{"x": 1, "y": 2}, ...] 格式的数据列表。
        x_key: 自变量键名。
        y_key: 因变量键名。

    Returns:
        包含回归结果的字典。
    """
    x = [float(row[x_key]) for row in data]
    y = [float(row[y_key]) for row in data]
    return linear_regression(x, y, x_label=x_key, y_label=y_key)
