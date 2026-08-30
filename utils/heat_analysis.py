"""热力分析业务模块。

对表格中用户选中的 1-10 数值列计算 Pearson 相关系数矩阵，
供前端绘制带数值标注的热力图。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from utils.regression import regression_column_details


def heatmap_values(
    df: pd.DataFrame,
    columns: list[str],
) -> dict[str, Any]:
    """计算所选列之间的 Pearson 相关系数热力矩阵。"""
    if not isinstance(columns, list):
        raise ValueError("列选择必须是列名数组")

    selected = [str(column).strip() for column in columns if str(column).strip()]
    if len(selected) < 2:
        raise ValueError("请至少选择 2 列进行热力分析")
    if len(selected) != len(set(selected)):
        raise ValueError("不能重复选择同一列")

    details = regression_column_details(df)
    detail_map = {detail["name"]: detail for detail in details}
    missing = [column for column in selected if column not in detail_map]
    if missing:
        raise ValueError(f"选择的列不存在：{', '.join(missing)}")

    invalid = [
        column for column in selected
        if not detail_map[column]["eligible"]
    ]
    if invalid:
        raise ValueError(
            f"以下列不符合要求，只能选择全部为 1-10 数值的列：{', '.join(invalid)}"
        )

    names = [detail["name"] for detail in details]
    data = pd.DataFrame({
        column: pd.to_numeric(df.iloc[:, names.index(column)], errors="coerce")
        for column in selected
    })
    matrix = data.corr(method="pearson").to_numpy(dtype=float)
    # Pearson correlation is undefined for a constant column. Keep the
    # diagonal meaningful and make undefined cross-column values neutral.
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(matrix, 1.0)

    values = [[round(float(value), 6) for value in row] for row in matrix]
    return {
        "columns": selected,
        "values": values,
        "method": "Pearson 相关系数",
        "sample_count": len(data),
        "value_min": min(value for row in values for value in row),
        "value_max": max(value for row in values for value in row),
    }
