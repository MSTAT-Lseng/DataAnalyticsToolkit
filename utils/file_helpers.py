"""文件上传/读取/导出的通用辅助函数。

提取 app.py 中反复出现的模式：
- 上传文件验证 + 临时存储 + DataFrame 读取
- 表格预览数据提取
- Excel 导出响应
"""

import io
import os
import tempfile
from contextlib import contextmanager
from typing import Optional

import pandas as pd
from flask import send_file, Response

ALLOWED_TABLE_EXTENSIONS = {".xls", ".xlsx", ".csv"}


@contextmanager
def uploaded_dataframe(file, allowed_extensions: Optional[set[str]] = None):
    """上下文管理器：从 Flask 上传文件中读取 DataFrame，退出时自动清理临时文件。

    用法:
        with uploaded_dataframe(file) as (df, suffix, tmp_path):
            # 使用 df
            ...

    参数:
        file: Flask request.files 中的文件对象
        allowed_extensions: 允许的扩展名集合，默认 {.xls, .xlsx, .csv}

    Yields:
        (df, suffix, tmp_path) 三元组

    Raises:
        ValueError: 文件无效或格式不支持
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_TABLE_EXTENSIONS

    if not file or file.filename == "":
        raise ValueError("请上传表格文件")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_extensions:
        raise ValueError(
            f"不支持的文件格式：{suffix}，"
            f"请上传 {', '.join(sorted(allowed_extensions))}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        if suffix == ".csv":
            df = pd.read_csv(tmp_path)
        else:
            df = pd.read_excel(
                tmp_path,
                engine="openpyxl" if suffix == ".xlsx" else "xlrd",
            )
        yield df, suffix, tmp_path
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def dataframe_preview(df: pd.DataFrame, max_rows: int = 20) -> dict:
    """从 DataFrame 提取列名和预览行。

    返回:
        {"columns": [...], "rows": [...], "total_rows": N}
    """
    columns = [str(c) for c in df.columns.tolist()]
    preview_df = df.head(max_rows).fillna("")
    rows = [[str(v) for v in row] for row in preview_df.values.tolist()]
    return {
        "columns": columns,
        "rows": rows,
        "total_rows": len(df),
    }


def send_excel(workbook, filename: str = "export.xlsx") -> Response:
    """将 openpyxl Workbook 转为 Flask 文件下载响应。"""
    # 延迟导入避免循环依赖
    import openpyxl  # noqa: F811

    buf = io.BytesIO()
    workbook.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
