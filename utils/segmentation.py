"""中文分词与词频统计模块。

支持中英文混合文本，使用 jieba 进行中文分词，
对英文按空格分割，并过滤停用词。
"""

import re
import os
from collections import Counter
from typing import Dict, List, Tuple

import jieba

# ============================================================
# 停用词加载
# ============================================================

# 内置基础停用词表（常见中文停用词）
_BUILTIN_STOPWORDS: set[str] = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "所", "为", "所以", "因为", "但是", "然而", "虽然", "如果", "可以",
    "这个", "那个", "哪个", "什么", "怎么", "怎样", "如何", "为何",
    "啊", "吧", "呢", "吗", "哦", "嗯", "哈", "呀", "哇",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "than", "too",
    "very", "just", "about", "above", "after", "again", "against",
    "between", "down", "further", "here", "now", "off", "once", "out",
    "over", "under", "up", "when", "where", "why", "how", "who", "whom",
    "which", "what", "that", "this", "these", "those", "it", "its",
    "he", "him", "his", "she", "her", "they", "them", "their", "we", "us",
}


def _load_custom_stopwords(filepath: str | None = None) -> set[str]:
    """从文件加载自定义停用词（一行一个词）。"""
    custom: set[str] = set()
    if filepath and os.path.isfile(filepath):
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    custom.add(word)
    return custom


# 合并内置 + 自定义停用词（若文件存在）
_STOPWORDS_FILE = os.path.join(os.path.dirname(__file__), "stopwords.txt")
STOPWORDS: set[str] = _BUILTIN_STOPWORDS | _load_custom_stopwords(_STOPWORDS_FILE)


# ============================================================
# 公共接口
# ============================================================

def segment_text(
    text: str,
    top_n: int = 50,
    remove_stopwords: bool = True,
    extra_stopwords: set[str] | None = None,
    extra_dict: list[str] | None = None,
) -> Dict[str, int]:
    """对文本进行分词并返回词频字典。

    Args:
        text: 输入文本（中文 / 英文 / 混合）。
        top_n: 仅返回频率最高的前 N 个词（0 或负数表示全部返回）。
        remove_stopwords: 是否过滤停用词。
        extra_stopwords: 额外的自定义停用词集合，会与内置停用词合并。
        extra_dict: 自定义词典词条列表，每个词会被 jieba 视为一个整体。

    Returns:
        {词语: 频次} 字典，按频次降序排列。
    """
    if not text or not text.strip():
        return {}

    # ---- 加载自定义词典 ----
    if extra_dict:
        for word in extra_dict:
            w = word.strip()
            if w:
                jieba.add_word(w)

    # ---- 中文分词 ----
    words = jieba.lcut(text)

    # ---- 清洗：去除空白、纯标点、纯数字 ----
    cleaned: list[str] = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if re.fullmatch(r"[\W\d_]+", w):
            continue
        cleaned.append(w)

    # ---- 停用词过滤 ----
    if remove_stopwords:
        stopwords = STOPWORDS
        if extra_stopwords:
            stopwords = STOPWORDS | {w.lower() for w in extra_stopwords}
        cleaned = [w for w in cleaned if w.lower() not in stopwords and len(w) > 1]

    # ---- 统计 ----
    counter = Counter(cleaned)

    if top_n and top_n > 0:
        return dict(counter.most_common(top_n))

    return dict(counter.most_common())


def get_top_words(
    text: str,
    top_n: int = 20,
) -> List[Tuple[str, int]]:
    """获取高频词列表（用于绘图）。

    Returns:
        按频次降序排列的 [(词语, 频次), ...] 列表。
    """
    freq_dict = segment_text(text, top_n=top_n)
    return list(freq_dict.items())


def segment_file(
    filepath: str,
    top_n: int = 50,
    encoding: str = "utf-8",
) -> Dict[str, int]:
    """从文件读取文本并分词。

    Args:
        filepath: 文本文件路径。
        top_n: 返回前 N 个高频词。
        encoding: 文件编码。

    Returns:
        {词语: 频次} 字典。
    """
    with open(filepath, encoding=encoding) as f:
        text = f.read()
    return segment_text(text, top_n=top_n)
