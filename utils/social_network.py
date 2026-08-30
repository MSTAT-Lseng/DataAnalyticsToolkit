"""社会网络关系图的数据准备与共现关系计算。

关系图使用滑动窗口统计词语共现：同一条文本记录内，窗口距离以内的两个
词语视为共同出现。文本模式按句子切分，表格模式按行切分，避免把无关的
文本边界连接起来。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Iterable

import jieba
import pandas as pd

from utils.segmentation import tokenize_text


WORD_COLUMN_NAMES = {"词语", "词", "word", "term", "token"}
COUNT_COLUMN_NAMES = {"频次", "词频", "count", "freq", "frequency"}


def _normalise_column_name(value: Any) -> str:
    return str(value).strip().lower()


def parse_frequency_rows(rows: Iterable[dict[str, Any]]) -> list[str]:
    """从分词统计导出的行记录中提取词语。

    该函数供路由层在 DataFrame 转换后调用，词频本身不参与图的节点权重，
    因为关系图会根据当前原始文本重新计算词频。
    """
    values: list[str] = []
    for row in rows:
        word = row.get("word")
        count = row.get("count")
        if word is None:
            continue
        word = str(word).strip()
        try:
            count_value = float(count)
        except (TypeError, ValueError):
            continue
        if word and math.isfinite(count_value) and count_value > 0:
            values.append(word)
    return list(dict.fromkeys(values))


def frequency_columns(columns: Iterable[Any]) -> tuple[Any | None, Any | None]:
    """识别分词统计 Excel 中的词语列和频次列。"""
    columns = list(columns)
    word_column = None
    count_column = None
    for column in columns:
        normalised = _normalise_column_name(column)
        if normalised in {_normalise_column_name(name) for name in WORD_COLUMN_NAMES}:
            word_column = column
        elif normalised in {_normalise_column_name(name) for name in COUNT_COLUMN_NAMES}:
            count_column = column

    # 分词统计功能的标准导出格式为“排名、词语、频次”。允许列名被用户改动，
    # 但至少要求两列且第二列必须能解释为词频数据。
    if word_column is None and len(columns) >= 2:
        word_column = columns[1] if len(columns) >= 3 else columns[0]
    if count_column is None:
        candidates = [column for column in columns if column != word_column]
        if candidates:
            count_column = candidates[-1]
    return word_column, count_column


def parse_frequency_dataframe(df) -> tuple[list[str], str | None]:
    """解析“分词统计”导出的 DataFrame，返回词条和识别说明。"""
    word_column, count_column = frequency_columns(df.columns)
    if word_column is None or count_column is None:
        raise ValueError("无法识别分词结果表，请上传包含「词语」和「频次」列的 Excel 文件")

    imported: list[str] = []
    for _, row in df.iterrows():
        raw_word = row[word_column]
        word = "" if pd.isna(raw_word) else str(raw_word).strip()
        try:
            count = float(row[count_column])
        except (TypeError, ValueError):
            continue
        if word and math.isfinite(count) and count > 0:
            imported.append(word)

    imported = list(dict.fromkeys(imported))
    if not imported:
        raise ValueError("分词结果表中没有有效词条，请确认「频次」列为正数")
    return imported, str(word_column)


def split_documents(text: str) -> list[str]:
    """把文本按常见句末标点切分为共现计算单元。"""
    return [part.strip() for part in re.split(r"[。！？!?；;\n\r]+", text) if part.strip()]


def build_token_documents(
    documents: Iterable[str],
    segmentation_words: Iterable[str] | None = None,
) -> list[list[str]]:
    """使用导入的分词结果词表，将文本记录转换为词语序列。"""
    segmentation_word_list = list(dict.fromkeys(
        str(word).strip()
        for word in (segmentation_words or [])
        if str(word).strip()
    ))

    # The imported table can contain thousands of words. Register each missing
    # rule once per process, then reuse the prepared jieba dictionary for every
    # document in this request.
    for word in segmentation_word_list:
        if jieba.dt.FREQ.get(word, 0) <= 0:
            jieba.add_word(word)

    allowed_words = set(segmentation_word_list) or None
    token_documents: list[list[str]] = []
    for document in documents:
        if not str(document).strip():
            continue
        tokens = tokenize_text(
            str(document),
            remove_stopwords=True,
        )
        if allowed_words is not None:
            tokens = [token for token in tokens if token in allowed_words]
        token_documents.append(tokens)
    return token_documents


def prepare_network_data(
    documents: Iterable[str],
    segmentation_words: Iterable[str] | None = None,
) -> dict[str, Any]:
    """完成分词并返回预览统计。"""
    summary, _token_documents = _prepare_network_data(
        documents,
        segmentation_words=segmentation_words,
    )
    return summary


def _prepare_network_data(
    documents: Iterable[str],
    segmentation_words: Iterable[str] | None = None,
) -> tuple[dict[str, Any], list[list[str]]]:
    """返回摘要和内部使用的分词序列。"""
    segmentation_word_list = list(dict.fromkeys(
        str(word).strip()
        for word in (segmentation_words or [])
        if str(word).strip()
    ))
    token_documents = build_token_documents(
        documents,
        segmentation_words=segmentation_word_list,
    )
    frequencies = Counter(token for document in token_documents for token in document)
    return {
        "document_count": len(token_documents),
        "token_count": sum(frequencies.values()),
        "unique_words": len(frequencies),
        "top_words": [
            {"word": word, "count": count}
            for word, count in frequencies.most_common(20)
        ],
        "segmentation_word_count": len(segmentation_word_list),
    }, token_documents


def build_cooccurrence_graph(
    documents: Iterable[str],
    segmentation_words: Iterable[str] | None = None,
    window_size: int = 4,
    min_frequency: int = 1,
    max_nodes: int = 60,
    max_edges: int = 180,
) -> dict[str, Any]:
    """计算词语共现关系并返回 Plotly 可直接消费的节点和边。"""
    if window_size < 2 or window_size > 10:
        raise ValueError("共现窗口需要设置为 2 到 10")
    if min_frequency < 1:
        raise ValueError("最小词频需要至少为 1")
    if max_nodes < 1 or max_nodes > 200:
        raise ValueError("最多节点数需要设置为 1 到 200")
    if max_edges < 1 or max_edges > 1000:
        raise ValueError("最多关系数需要设置为 1 到 1000")

    prepared, token_documents = _prepare_network_data(
        documents,
        segmentation_words=segmentation_words,
    )
    frequencies = Counter(token for document in token_documents for token in document)
    if not frequencies:
        raise ValueError("当前停用词配置下没有可绘制的词语")
    eligible = {
        word for word, count in frequencies.items() if count >= min_frequency
    }
    ranked_words = [word for word, _ in frequencies.most_common() if word in eligible]
    ranked_words = ranked_words[:max_nodes]
    if not ranked_words:
        raise ValueError("没有词语达到最小词频，请降低最小词频")
    node_words = set(ranked_words)

    edge_counts: Counter[tuple[str, str]] = Counter()
    for document in token_documents:
        filtered = [token for token in document if token in node_words]
        for index, source in enumerate(filtered):
            seen: set[str] = set()
            for target in filtered[index + 1:index + window_size]:
                if target == source or target in seen:
                    continue
                seen.add(target)
                pair = tuple(sorted((source, target)))
                edge_counts[pair] += 1

    selected_edges = edge_counts.most_common(max_edges)
    nodes = [
        {
            "id": word,
            "label": word,
            "count": frequencies[word],
            "rank": index + 1,
        }
        for index, word in enumerate(ranked_words)
    ]
    links = [
        {"source": source, "target": target, "weight": weight}
        for (source, target), weight in selected_edges
    ]
    return {
        **prepared,
        "nodes": nodes,
        "links": links,
        "node_count": len(nodes),
        "edge_count": len(links),
        "window_size": window_size,
        "min_frequency": min_frequency,
        "max_nodes": max_nodes,
        "max_edges": max_edges,
    }
