# -*- coding: utf-8 -*-
"""
TF-IDF相似度计算模块
计算文献与种子文本的相似度，用于筛选和排序
"""

from typing import List

import numpy as np
import pandas as pd

from core.data_loader import safe_str


class TFIDFScorerError(Exception):
    """TF-IDF评分器异常"""
    pass


def tfidf_scoring(
    df: pd.DataFrame, 
    seed_texts: List[str]
) -> pd.DataFrame:
    """
    TF-IDF相似度计算
    添加列 tfidf_score
    """
    df = df.copy()
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        print("[WARN] scikit-learn 未安装，跳过 TF-IDF 排序层。可通过 pip install scikit-learn 安装。")
        df["tfidf_score"] = 0.5
        return df
    
    # 准备语料
    corpus_texts = []
    for _, row in df.iterrows():
        t = " ".join([
            safe_str(row.get("title", "")),
            safe_str(row.get("abstract", "")),
            safe_str(row.get("keywords", "")),
        ])
        corpus_texts.append(t)
    
    # 如果没有种子文本，使用默认值
    if not seed_texts:
        seed_texts = ["literature review"]
    
    all_texts = seed_texts + corpus_texts
    n_seeds = len(seed_texts)
    
    # 计算TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    
    seed_vectors = tfidf_matrix[:n_seeds]
    doc_vectors = tfidf_matrix[n_seeds:]
    
    # 计算相似度
    sim_matrix = cosine_similarity(doc_vectors, seed_vectors)
    avg_scores = np.mean(sim_matrix, axis=1)
    
    df["tfidf_score"] = avg_scores.tolist()
    return df


def apply_tfidf_threshold(
    df: pd.DataFrame, 
    low_threshold: float = 0.02, 
    high_threshold: float = 0.3
) -> pd.DataFrame:
    """
    应用TF-IDF阈值筛选
    标记高相关和低相关文献
    """
    df = df.copy()
    
    # 初始化筛选结果列
    if "screening_level" not in df.columns:
        df["screening_level"] = ""
    if "evidence_type" not in df.columns:
        df["evidence_type"] = ""
    if "reason" not in df.columns:
        df["reason"] = ""
    if "screening_method" not in df.columns:
        df["screening_method"] = ""
    
    # 只对还未判定的记录进行筛选
    mask_undecided = df["screening_level"].isna() | (df["screening_level"] == "")
    
    # 相似度低于阈值的标记为低相关
    if not pd.isna(low_threshold):
        mask_low = df["tfidf_score"] < low_threshold
        df.loc[mask_low & mask_undecided, "screening_level"] = "低相关"
        df.loc[mask_low & mask_undecided, "evidence_type"] = "low_similarity"
        df.loc[mask_low & mask_undecided, "reason"] = f"TF-IDF相似度低于阈值 {low_threshold}"
        df.loc[mask_low & mask_undecided, "screening_method"] = "tfidf_threshold"
    
    # 相似度高于阈值的标记为高相关
    if not pd.isna(high_threshold):
        mask_high = df["tfidf_score"] >= high_threshold
        df.loc[mask_high & mask_undecided, "screening_level"] = "高相关"
        df.loc[mask_high & mask_undecided, "evidence_type"] = "high_similarity"
        df.loc[mask_high & mask_undecided, "reason"] = f"TF-IDF相似度高于阈值 {high_threshold}"
        df.loc[mask_high & mask_undecided, "screening_method"] = "tfidf_threshold"
    
    return df


def get_tfidf_statistics(df: pd.DataFrame) -> dict:
    """
    获取TF-IDF筛选统计信息
    """
    if "tfidf_score" not in df.columns:
        return {
            "error": "TF-IDF score column not found",
        }
    
    stats = {
        "total_records": len(df),
        "tfidf_min": float(df["tfidf_score"].min()),
        "tfidf_max": float(df["tfidf_score"].max()),
        "tfidf_mean": float(df["tfidf_score"].mean()),
        "tfidf_median": float(df["tfidf_score"].median()),
        "tfidf_std": float(df["tfidf_score"].std()),
    }
    
    # 计算各区间分布
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    bin_labels = ["0-0.1", "0.1-0.2", "0.2-0.3", "0.3-0.4", "0.4-0.5", 
                 "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
    
    bin_counts = pd.cut(df["tfidf_score"], bins=bins, labels=bin_labels, include_lowest=True).value_counts()
    stats["tfidf_distribution"] = {str(k): int(v) for k, v in bin_counts.to_dict().items()}
    
    # 计算TF-IDF阈值筛选结果
    mask_tfidf_high = (df["screening_method"] == "tfidf_threshold") & (df["screening_level"] == "高相关")
    mask_tfidf_low = (df["screening_method"] == "tfidf_threshold") & (df["screening_level"] == "低相关")
    
    stats["tfidf_high_count"] = int(mask_tfidf_high.sum())
    stats["tfidf_low_count"] = int(mask_tfidf_low.sum())
    
    return stats


def print_tfidf_statistics(df: pd.DataFrame) -> None:
    """
    打印TF-IDF筛选统计信息
    """
    stats = get_tfidf_statistics(df)
    
    if "error" in stats:
        print(f"[ERROR] {stats['error']}")
        return
    
    print("=== TF-IDF相似度统计信息 ===")
    print(f"总记录数: {stats['total_records']}")
    print(f"相似度范围: {stats['tfidf_min']:.4f} - {stats['tfidf_max']:.4f}")
    print(f"平均相似度: {stats['tfidf_mean']:.4f}")
    print(f"中位数相似度: {stats['tfidf_median']:.4f}")
    print(f"标准差: {stats['tfidf_std']:.4f}")
    
    print("\n相似度分布:")
    for bin_label, count in sorted(stats['tfidf_distribution'].items()):
        percentage = count / stats['total_records'] * 100
        print(f"  {bin_label}: {count} ({percentage:.1f}%)")
    
    if "tfidf_high_count" in stats:
        high_percentage = stats['tfidf_high_count'] / stats['total_records'] * 100
        print(f"\nTF-IDF高相关: {stats['tfidf_high_count']} ({high_percentage:.1f}%)")
    if "tfidf_low_count" in stats:
        low_percentage = stats['tfidf_low_count'] / stats['total_records'] * 100
        print(f"TF-IDF低相关: {stats['tfidf_low_count']} ({low_percentage:.1f}%)")
