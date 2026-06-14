"""情感分析模块。

使用 SnowNLP 进行中文情感倾向评分。
支持对单句文本、长文本（按句拆分取平均）、批量文本的情感分析。
支持自定义情感词微调：用户可手动指定特定词汇的情感值以修正模型偏差。
"""

from typing import Dict, List, Optional

from snownlp import SnowNLP


# ============================================================
# 公共接口
# ============================================================

def analyze_sentiment(
    text: str,
    custom_sentiment: Optional[Dict[str, float]] = None,
    custom_weight: float = 0.6,
) -> Dict:
    """对文本进行情感分析，返回综合结果。

    SnowNLP 得分范围 0~1：
        > 0.6  积极
        0.4~0.6 中性
        < 0.4  消极

    Args:
        text: 输入文本。
        custom_sentiment: 自定义情感词字典 {词: 情感值(0~1)}。
                         情感值 > 0.6 为积极倾向，< 0.4 为消极倾向。
        custom_weight: 自定义词汇权重（0~1），默认 0.6。
                       值越大，自定义词汇对最终得分的影响越大。

    Returns:
        {
            "score": float,           # 整体情感得分（按句平均）
            "label": str,             # "积极" / "中性" / "消极"
            "positive_ratio": float,  # 积极句子占比
            "negative_ratio": float,  # 消极句子占比
            "neutral_ratio": float,   # 中性句子占比
            "sentence_count": int,    # 有效句子数
            "sentences": [            # 逐句详情
                {"text": str, "score": float, "label": str,
                 "custom_words": [str]},  # 该句中匹配到的自定义词
                ...
            ],
        }
    """
    if not text or not text.strip():
        return _empty_result()

    # ---- 分句 ----
    raw_sentences = _split_sentences(text)

    if not raw_sentences:
        return _empty_result()

    # ---- 逐句评分 ----
    sentence_results: List[Dict] = []
    scores: List[float] = []

    for s in raw_sentences:
        s = s.strip()
        if not s or len(s) < 2:
            continue
        try:
            snownlp_score = SnowNLP(s).sentiments
        except Exception:
            snownlp_score = 0.5

        # 应用自定义情感词微调
        adjusted_score, matched_words = _apply_custom_sentiment(
            s, snownlp_score, custom_sentiment, custom_weight
        )

        label = _score_to_label(adjusted_score)
        sentence_results.append({
            "text": s,
            "score": round(adjusted_score, 4),
            "label": label,
            "custom_words": matched_words,
        })
        scores.append(adjusted_score)

    # ---- 整体统计 ----
    n = len(scores)
    avg_score = sum(scores) / n if n > 0 else 0.5

    pos_count = sum(1 for s in scores if s > 0.6)
    neg_count = sum(1 for s in scores if s < 0.4)
    neu_count = n - pos_count - neg_count

    return {
        "score": round(avg_score, 4),
        "label": _score_to_label(avg_score),
        "positive_ratio": round(pos_count / n, 4) if n else 0.0,
        "negative_ratio": round(neg_count / n, 4) if n else 0.0,
        "neutral_ratio": round(neu_count / n, 4) if n else 0.0,
        "sentence_count": n,
        "sentences": sentence_results,
    }


def analyze_batch(
    texts: List[str],
    custom_sentiment: Optional[Dict[str, float]] = None,
    custom_weight: float = 0.6,
) -> List[Dict]:
    """批量分析多条文本的情感。

    Args:
        texts: 文本列表。
        custom_sentiment: 自定义情感词字典。
        custom_weight: 自定义词汇权重。

    Returns:
        每条文本的分析结果列表。
    """
    return [analyze_sentiment(t, custom_sentiment=custom_sentiment, custom_weight=custom_weight) for t in texts]


def parse_custom_sentiment(raw: str) -> Optional[Dict[str, float]]:
    """解析用户输入的自定义情感词文本。

    支持的格式（每行一个）：
        词:情感值    例如  优秀:0.9
        词 情感值    例如  优秀 0.9
        词=情感值    例如  优秀=0.9

    Args:
        raw: 用户输入的原始文本。

    Returns:
        {词: 情感值} 字典；若无有效条目则返回 None。
    """
    import re

    if not raw or not raw.strip():
        return None

    result: Dict[str, float] = {}
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 支持 : = 空格 作为分隔符
        parts = re.split(r"[:=]+|\s+", line.strip(), maxsplit=1)
        if len(parts) == 2:
            word = parts[0].strip()
            try:
                score = float(parts[1].strip())
            except ValueError:
                continue
            if word and 0 <= score <= 1:
                result[word] = score

    return result if result else None


# ============================================================
# 内部辅助
# ============================================================

def _empty_result() -> Dict:
    """返回空文本的分析结果。"""
    return {
        "score": 0.5,
        "label": "中性",
        "positive_ratio": 0.0,
        "negative_ratio": 0.0,
        "neutral_ratio": 0.0,
        "sentence_count": 0,
        "sentences": [],
    }


def _apply_custom_sentiment(
    sentence: str,
    snownlp_score: float,
    custom_sentiment: Optional[Dict[str, float]],
    custom_weight: float,
) -> tuple[float, list[str]]:
    """将自定义情感词微调应用到单个句子的得分上。

    对句子中的每个自定义情感词，将其情感值与 SnowNLP 得分加权融合：
        adjusted = snownlp * (1 - w) + avg_custom * w

    Args:
        sentence: 句子文本。
        snownlp_score: SnowNLP 原始得分。
        custom_sentiment: 自定义情感词字典。
        custom_weight: 自定义词汇权重。

    Returns:
        (调整后的得分, 匹配到的自定义词列表)
    """
    if not custom_sentiment:
        return snownlp_score, []

    # 查找句子中出现的所有自定义词
    matched: list[tuple[str, float]] = []
    for word, sentiment_score in custom_sentiment.items():
        if word in sentence:
            matched.append((word, sentiment_score))

    if not matched:
        return snownlp_score, []

    # 计算匹配词的平均情感值
    avg_custom = sum(s for _, s in matched) / len(matched)

    # 加权融合
    adjusted = snownlp_score * (1 - custom_weight) + avg_custom * custom_weight
    matched_words = [w for w, _ in matched]

    return round(adjusted, 4), matched_words


def _split_sentences(text: str) -> list[str]:
    """将中文文本按句号、问号、感叹号、换行等拆分。"""
    import re

    # 按中文标点和换行拆分
    parts = re.split(r"[。！？!?\n\r；;]+", text)
    return [p.strip() for p in parts if p.strip()]


def _score_to_label(score: float) -> str:
    """将 SnowNLP 得分转为中文标签。"""
    if score > 0.6:
        return "积极"
    elif score < 0.4:
        return "消极"
    return "中性"
