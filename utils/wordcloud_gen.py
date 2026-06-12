"""词云生成模块。

接收文本或词频字典，使用 wordcloud 库生成词云图片，
返回 Base64 编码字符串以便直接嵌入 HTML。
"""

import base64
import io
import os
import tempfile
import hashlib
from typing import Dict
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # 无 GUI 后端，必须在 import pyplot 之前

import matplotlib.pyplot as plt  # noqa: E402
from wordcloud import WordCloud  # noqa: E402

from utils.segmentation import segment_text  # noqa: E402


# ============================================================
# 公共接口
# ============================================================

def generate_wordcloud(
    text: str | None = None,
    freq_dict: Dict[str, int] | None = None,
    width: int = 800,
    height: int = 500,
    background_color: str = "#ffffff",
    colormap: str = "viridis",
    max_words: int = 200,
    font_path: str | None = None,
) -> str:
    """生成词云图片并返回 Base64 编码字符串。

    Args:
        text: 输入文本（与 freq_dict 二选一）。
        freq_dict: 预先统计好的词频字典（与 text 二选一）。
        width: 图片宽度（像素）。
        height: 图片高度（像素）。
        background_color: 背景色。
        colormap: matplotlib 颜色映射名称。
        max_words: 最大显示词数。
        font_path: 字体路径（用于中文渲染，None 则尝试自动检测）。

    Returns:
        Base64 编码的 PNG 图片字符串，可直接用于 <img src="data:image/png;base64,...">。
    """
    # ---- 确定词频 ----
    if freq_dict is None and text is not None:
        freq_dict = segment_text(text, top_n=max_words)
    elif freq_dict is None:
        raise ValueError("必须提供 text 或 freq_dict 其中之一")

    if not freq_dict:
        raise ValueError("词频字典为空，无法生成词云")

    # ---- 字体检测 ----
    if font_path is None:
        font_path = _detect_cjk_font()

    # ---- 生成词云 ----
    wc = WordCloud(
        width=width,
        height=height,
        background_color=background_color,
        colormap=colormap,
        max_words=max_words,
        font_path=font_path,
        random_state=42,
    )
    wc.generate_from_frequencies(freq_dict)

    # ---- 转为 Base64 ----
    buf = io.BytesIO()
    plt.figure(figsize=(width / 100, height / 100), dpi=100)
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close()
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return b64


def save_wordcloud_to_file(
    text: str | None = None,
    freq_dict: Dict[str, int] | None = None,
    output_path: str | None = None,
    **kwargs,
) -> str:
    """生成词云并保存为 PNG 文件。

    Args:
        text: 输入文本。
        freq_dict: 词频字典。
        output_path: 输出路径（None 则使用临时文件，由调用方管理生命周期）。
        **kwargs: 传递给 generate_wordcloud 的其他参数。

    Returns:
        输出文件的绝对路径。
    """
    b64 = generate_wordcloud(text=text, freq_dict=freq_dict, **kwargs)
    img_data = base64.b64decode(b64)

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".png", prefix="wordcloud_")
        os.close(fd)

    with open(output_path, "wb") as f:
        f.write(img_data)

    return output_path


# ============================================================
# 内部辅助
# ============================================================

def _detect_cjk_font() -> str | None:
    """尝试自动检测系统可用的中文字体。"""
    candidates = [
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        # Windows (WSL)
        "/mnt/c/Windows/Fonts/msyh.ttc",
        "/mnt/c/Windows/Fonts/simsun.ttc",
        "/mnt/c/Windows/Fonts/simhei.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None
