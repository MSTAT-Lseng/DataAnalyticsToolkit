"""文本与表格聚类业务模块。

使用 jieba/正则分词生成 TF-IDF 特征，再使用 K-Means 完成聚类。
"""

from __future__ import annotations

import re
from typing import Any, Sequence

import jieba
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?")
_SENTENCE_RE = re.compile(r"(?<=[。！？!?；;])\s*|\n+")


def split_sentences(text: str) -> list[str]:
    """按中文/英文句末标点和换行拆分文本，过滤空句子。"""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    sentences = []
    for part in _SENTENCE_RE.split(normalized):
        sentence = re.sub(r"\s+", " ", part).strip()
        if sentence:
            sentences.append(sentence)
    return sentences


def _tokenize(text: str) -> list[str]:
    """提取中英文词语和数字，避免默认 TF-IDF 将中文整句视为一个词。"""
    tokens: list[str] = []
    for fragment in _TOKEN_RE.findall(text.lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", fragment):
            tokens.extend(token.strip() for token in jieba.lcut(fragment) if token.strip())
        else:
            tokens.append(fragment)
    return tokens


def clustering_column_details(df: pd.DataFrame) -> list[dict[str, Any]]:
    """返回表格列的可聚类状态，聚类列可以是任意文本或混合类型。"""
    names = [str(column) for column in df.columns.tolist()]
    if len(names) != len(set(names)):
        raise ValueError("表格的标题列名不能重复，请修改第一行标题后重新上传")

    details = []
    for position, name in enumerate(names):
        series = df.iloc[:, position]
        values = [
            str(value).strip()
            for value in series.tolist()
            if not pd.isna(value) and str(value).strip()
        ]
        details.append({
            "name": name,
            "eligible": len(values) >= 2,
            "sample_count": len(values),
            "reason": "可用于聚类" if len(values) >= 2 else "至少需要 2 个非空值",
        })
    return details


def dataframe_column_texts(
    df: pd.DataFrame,
    column: str,
) -> tuple[list[str], list[int]]:
    """读取指定表格列中的非空文本，同时返回 1-based 数据行号。"""
    names = [str(value) for value in df.columns.tolist()]
    if len(names) != len(set(names)):
        raise ValueError("表格的标题列名不能重复，请修改第一行标题后重新上传")
    if column not in names:
        raise ValueError(f"选择的列不存在：{column}")

    position = names.index(column)
    documents: list[str] = []
    row_numbers: list[int] = []
    for row_position, value in enumerate(df.iloc[:, position].tolist(), start=2):
        if pd.isna(value):
            continue
        document = str(value).strip()
        if document:
            documents.append(document)
            row_numbers.append(row_position)
    if len(documents) < 2:
        raise ValueError("所选列至少需要 2 个非空值才能进行聚类")
    return documents, row_numbers


def _parse_cluster_count(value: int | str, document_count: int) -> int:
    """验证聚类数量，要求至少 2 类且不超过待聚类样本数。"""
    if isinstance(value, bool):
        raise ValueError("聚类数量必须是整数")
    try:
        cluster_count = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("聚类数量必须是整数") from exc
    if cluster_count < 2:
        raise ValueError("聚类数量至少为 2")
    if cluster_count > document_count:
        raise ValueError(f"聚类数量不能超过样本数（当前为 {document_count}）")
    return cluster_count


def _project_features(matrix) -> np.ndarray:
    """将稀疏 TF-IDF 特征投影到二维，仅用于前端散点图展示。"""
    component_count = min(2, matrix.shape[1])
    if component_count == 0:
        return np.zeros((matrix.shape[0], 2))
    projected = TruncatedSVD(
        n_components=component_count,
        random_state=42,
    ).fit_transform(matrix)
    if component_count == 1:
        projected = np.column_stack([projected[:, 0], np.zeros(len(projected))])
    return projected[:, :2]


def cluster_documents(
    documents: Sequence[str],
    n_clusters: int | str,
    item_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """对文档执行 TF-IDF + K-Means，并返回摘要、关键词和可视化数据。"""
    raw_documents = list(documents)
    if item_indices is not None and len(item_indices) != len(raw_documents):
        raise ValueError("样本索引数量与文本数量不一致")

    pairs = [
        (str(document).strip(), index)
        for index, document in zip(
            item_indices if item_indices is not None else range(1, len(raw_documents) + 1),
            raw_documents,
        )
        if str(document).strip()
    ]
    cleaned_documents = [document for document, _ in pairs]
    if len(cleaned_documents) < 2:
        raise ValueError("至少需要 2 条非空文本才能进行聚类")
    indices = [int(index) for _, index in pairs]

    cluster_count = _parse_cluster_count(n_clusters, len(cleaned_documents))
    vectorizer = TfidfVectorizer(
        tokenizer=_tokenize,
        token_pattern=None,
        lowercase=False,
        min_df=1,
        sublinear_tf=True,
    )
    try:
        matrix = vectorizer.fit_transform(cleaned_documents)
    except ValueError as exc:
        raise ValueError("文本中没有可提取的词语，无法进行聚类") from exc
    if matrix.shape[1] == 0:
        raise ValueError("文本中没有可提取的词语，无法进行聚类")

    model = KMeans(n_clusters=cluster_count, n_init=10, random_state=42)
    labels = model.fit_predict(matrix)
    distances = model.transform(matrix)
    projection = _project_features(matrix)
    feature_names = vectorizer.get_feature_names_out()

    clusters = []
    for cluster_id in range(cluster_count):
        center = model.cluster_centers_[cluster_id]
        ranked = np.argsort(center)[::-1]
        keywords = [
            str(feature_names[position])
            for position in ranked
            if center[position] > 0
        ][:5]
        clusters.append({
            "id": cluster_id + 1,
            "label": f"聚类 {cluster_id + 1}",
            "size": int(np.sum(labels == cluster_id)),
            "keywords": keywords,
        })

    items = []
    for position, document in enumerate(cleaned_documents):
        cluster_id = int(labels[position])
        items.append({
            "index": int(indices[position]),
            "text": document,
            "cluster": cluster_id + 1,
            "cluster_label": f"聚类 {cluster_id + 1}",
            "distance": round(float(distances[position, cluster_id]), 6),
            "x": round(float(projection[position, 0]), 6),
            "y": round(float(projection[position, 1]), 6),
        })

    return {
        "n_clusters": cluster_count,
        "document_count": len(cleaned_documents),
        "feature_count": int(matrix.shape[1]),
        "method": "TF-IDF + K-Means",
        "clusters": clusters,
        "items": items,
    }
