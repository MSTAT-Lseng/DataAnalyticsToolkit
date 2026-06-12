"""情感分析模块。

使用 SnowNLP 进行中文情感倾向评分。
支持对单句文本、长文本（按句拆分取平均）、批量文本的情感分析。
"""

from typing import Dict, List

from snownlp import SnowNLP


# ============================================================
# 公共接口
# ============================================================

def analyze_sentiment(text: str) -> Dict:
    """对文本进行情感分析，返回综合结果。

    SnowNLP 得分范围 0~1：
        > 0.6  积极
        0.4~0.6 中性
        < 0.4  消极

    Args:
        text: 输入文本。

    Returns:
        {
            "score": float,           # 整体情感得分（按句平均）
            "label": str,             # "积极" / "中性" / "消极"
            "positive_ratio": float,  # 积极句子占比
            "negative_ratio": float,  # 消极句子占比
            "neutral_ratio": float,   # 中性句子占比
            "sentence_count": int,    # 有效句子数
            "sentences": [            # 逐句详情
                {"text": str, "score": float, "label": str},
                ...
            ],
        }
    """
    if not text or not text.strip():
        return {
            "score": 0.5,
            "label": "中性",
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "neutral_ratio": 0.0,
            "sentence_count": 0,
            "sentences": [],
        }

    # ---- 分句 ----
    raw_sentences = _split_sentences(text)

    if not raw_sentences:
        return {
            "score": 0.5,
            "label": "中性",
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "neutral_ratio": 0.0,
            "sentence_count": 0,
            "sentences": [],
        }

    # ---- 逐句评分 ----
    sentence_results: List[Dict] = []
    scores: List[float] = []

    for s in raw_sentences:
        s = s.strip()
        if not s or len(s) < 2:
            continue
        try:
            score = SnowNLP(s).sentiments
        except Exception:
            score = 0.5  # 异常时视为中性
        label = _score_to_label(score)
        sentence_results.append({"text": s, "score": round(score, 4), "label": label})
        scores.append(score)

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


def analyze_batch(texts: List[str]) -> List[Dict]:
    """批量分析多条文本的情感。

    Args:
        texts: 文本列表。

    Returns:
        每条文本的分析结果列表。
    """
    return [analyze_sentiment(t) for t in texts]


# ============================================================
# 内部辅助
# ============================================================

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
