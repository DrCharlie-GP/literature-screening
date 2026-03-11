# -*- coding: utf-8 -*-
"""
Rank25百分位筛选模块
基于综合得分进行百分位筛选
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


class RankFilterError(Exception):
    """Rank筛选器异常"""
    pass


def calculate_rank_score(
    df: pd.DataFrame,
    rule_weight: float = 0.4,
    tfidf_weight: float = 0.6
) -> pd.DataFrame:
    """
    计算综合排名得分
    结合规则得分和TF-IDF得分
    
    Args:
        df: 包含rule_score和tfidf_score的DataFrame
        rule_weight: 规则得分权重
        tfidf_weight: TF-IDF得分权重
        
    Returns:
        添加了rank_score列的DataFrame
    """
    df = df.copy()
    
    # 确保权重和为1
    total_weight = rule_weight + tfidf_weight
    if total_weight != 1.0:
        rule_weight /= total_weight
        tfidf_weight /= total_weight
    
    # 初始化rank_score
    df["rank_score"] = 0.0
    
    # 计算综合得分
    if "rule_score" in df.columns and "tfidf_score" in df.columns:
        df["rank_score"] = (df["rule_score"] * rule_weight + 
                           df["tfidf_score"] * tfidf_weight)
    elif "rule_score" in df.columns:
        df["rank_score"] = df["rule_score"]
    elif "tfidf_score" in df.columns:
        df["rank_score"] = df["tfidf_score"]
    
    return df


def rank25_filter(
    df: pd.DataFrame,
    percentile: float = 25.0
) -> pd.DataFrame:
    """
    Rank25百分位筛选
    保留前N%的文献
    
    Args:
        df: 包含rank_score的DataFrame
        percentile: 保留的百分位（0-100）
        
    Returns:
        添加了rank_percentile和rank_tier列的DataFrame
    """
    df = df.copy()
    
    # 计算百分位
    df["rank_percentile"] = df["rank_score"].rank(pct=True) * 100
    
    # 确定阈值
    threshold = df["rank_score"].quantile(1 - percentile / 100)
    
    # 标记tier
    df["rank_tier"] = "rank_unselected"
    df.loc[df["rank_score"] >= threshold, "rank_tier"] = "rank_selected"
    
    return df


def apply_rank_direct_judgment(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    应用Rank直判
    直接标记高相关或低相关文献
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
    
    # 排名前25%的标记为高相关
    mask_selected = df["rank_tier"] == "rank_selected"
    df.loc[mask_selected & mask_undecided, "screening_level"] = "高相关"
    df.loc[mask_selected & mask_undecided, "evidence_type"] = "high_rank"
    df.loc[mask_selected & mask_undecided, "reason"] = "Rank25百分位筛选通过"
    df.loc[mask_selected & mask_undecided, "screening_method"] = "rank25"
    
    return df


def get_rank_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    获取Rank筛选统计信息
    """
    if "rank_score" not in df.columns:
        return {
            "error": "Rank score column not found",
        }
    
    stats = {
        "total_records": len(df),
        "rank_min": df["rank_score"].min(),
        "rank_max": df["rank_score"].max(),
        "rank_mean": df["rank_score"].mean(),
        "rank_median": df["rank_score"].median(),
        "rank_std": df["rank_score"].std(),
    }
    
    # 计算百分位分布
    if "rank_percentile" in df.columns:
        stats["top_25_count"] = (df["rank_tier"] == "rank_selected").sum()
        stats["top_25_percentage"] = stats["top_25_count"] / stats["total_records"] * 100
    
    # 计算rank_tier分布
    if "rank_tier" in df.columns:
        tier_counts = df["rank_tier"].value_counts().to_dict()
        stats["tier_distribution"] = tier_counts
    
    return stats


def print_rank_statistics(df: pd.DataFrame) -> None:
    """
    打印Rank筛选统计信息
    """
    stats = get_rank_statistics(df)
    
    print("=== Rank25百分位筛选统计信息 ===")
    print(f"总记录数: {stats['total_records']}")
    print(f"综合得分范围: {stats['rank_min']:.4f} - {stats['rank_max']:.4f}")
    print(f"平均综合得分: {stats['rank_mean']:.4f}")
    print(f"中位数综合得分: {stats['rank_median']:.4f}")
    print(f"标准差: {stats['rank_std']:.4f}")
    
    if "top_25_count" in stats:
        print(f"\nRank25筛选通过: {stats['top_25_count']} ({stats['top_25_percentage']:.1f}%)")
    
    if "tier_distribution" in stats:
        print("\nTier分布:")
        for tier, count in sorted(stats['tier_distribution'].items()):
            print(f"  {tier}: {count} ({count/stats['total_records']*100:.1f}%)")
