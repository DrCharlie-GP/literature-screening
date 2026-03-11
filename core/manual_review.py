# -*- coding: utf-8 -*-
"""
人工审查模块
用于人工介入文献筛查
"""

import pandas as pd
from typing import List, Dict, Any, Optional


class ManualReviewError(Exception):
    """人工审查异常"""
    pass


def get_undecided_documents(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    获取尚未判定的文献
    
    Args:
        df: 包含筛选结果的DataFrame
        
    Returns:
        尚未判定的文献DataFrame
    """
    mask_undecided = df["screening_level"].isna() | (df["screening_level"] == "")
    return df[mask_undecided].copy()


def display_document(
    doc: pd.Series,
    index: int,
    total: int
) -> None:
    """
    显示文献信息，供人工审查
    
    Args:
        doc: 单个文献记录
        index: 当前显示的索引
        total: 总文献数
    """
    print(f"\n=== 文献 {index+1}/{total} ===")
    print(f"标题: {doc.get('title', 'N/A')}")
    print(f"作者: {doc.get('authors', 'N/A')}")
    print(f"年份: {doc.get('year', 'N/A')}")
    print(f"期刊: {doc.get('journal', 'N/A')}")
    print(f"关键词: {doc.get('keywords', 'N/A')}")
    print(f"摘要: {doc.get('abstract', 'N/A')[:300]}...")
    
    # 显示已有的筛选信息
    print(f"\n已有筛选信息:")
    print(f"  规则层判定: {doc.get('rule_tier', 'N/A')}")
    print(f"  TF-IDF得分: {doc.get('tfidf_score', 'N/A'):.4f}")
    print(f"  综合排名得分: {doc.get('rank_score', 'N/A'):.4f}")
    print(f"  Rank百分位: {doc.get('rank_percentile', 'N/A'):.1f}%")
    
    print("\n=== 请选择相关性 ===")
    print("1. 高相关")
    print("2. 边界相关")
    print("3. 低相关")
    print("4. 跳过，稍后处理")
    print("5. 保存并退出人工审查")


def manual_review(
    df: pd.DataFrame,
    max_docs: Optional[int] = None
) -> pd.DataFrame:
    """
    人工审查界面
    
    Args:
        df: 包含筛选结果的DataFrame
        max_docs: 最大审查文献数，None表示全部
        
    Returns:
        更新后的DataFrame
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
    
    # 获取尚未判定的文献
    undecided_docs = get_undecided_documents(df)
    total_undecided = len(undecided_docs)
    
    if total_undecided == 0:
        print("所有文献已完成判定，无需人工审查。")
        return df
    
    print(f"\n=== 人工审查模式 ===")
    print(f"待审查文献总数: {total_undecided}")
    if max_docs:
        print(f"本次审查最大文献数: {max_docs}")
    print(f"按 1-5 键选择相关性，按 Enter 确认")
    print("按 Ctrl+C 可随时中断人工审查")
    
    # 获取待审查文献的索引
    undecided_indices = undecided_docs.index.tolist()
    
    # 限制最大审查数量
    if max_docs and max_docs < len(undecided_indices):
        undecided_indices = undecided_indices[:max_docs]
    
    reviewed_count = 0
    
    try:
        for idx, doc_idx in enumerate(undecided_indices):
            doc = df.loc[doc_idx]
            display_document(doc, idx, len(undecided_indices))
            
            # 获取用户输入
            while True:
                try:
                    choice = input("请输入选择 (1-5): ").strip()
                    if choice in ["1", "2", "3", "4", "5"]:
                        break
                    else:
                        print("无效输入，请输入 1-5 之间的数字")
                except KeyboardInterrupt:
                    print("\n\n=== 人工审查已中断 ===")
                    return df
            
            # 处理用户选择
            if choice == "1":
                # 高相关
                df.loc[doc_idx, "screening_level"] = "高相关"
                df.loc[doc_idx, "evidence_type"] = "manual_high"
                df.loc[doc_idx, "reason"] = "人工判定为高相关"
                df.loc[doc_idx, "screening_method"] = "manual_review"
                reviewed_count += 1
            elif choice == "2":
                # 边界相关
                df.loc[doc_idx, "screening_level"] = "边界相关"
                df.loc[doc_idx, "evidence_type"] = "manual_boundary"
                df.loc[doc_idx, "reason"] = "人工判定为边界相关"
                df.loc[doc_idx, "screening_method"] = "manual_review"
                reviewed_count += 1
            elif choice == "3":
                # 低相关
                df.loc[doc_idx, "screening_level"] = "低相关"
                df.loc[doc_idx, "evidence_type"] = "manual_low"
                df.loc[doc_idx, "reason"] = "人工判定为低相关"
                df.loc[doc_idx, "screening_method"] = "manual_review"
                reviewed_count += 1
            elif choice == "4":
                # 跳过
                continue
            elif choice == "5":
                # 保存并退出
                print(f"\n=== 人工审查已完成 ===")
                print(f"已审查文献数: {reviewed_count}")
                return df
    
    except KeyboardInterrupt:
        print("\n\n=== 人工审查已中断 ===")
    
    print(f"\n=== 人工审查已完成 ===")
    print(f"已审查文献数: {reviewed_count}")
    return df


def batch_review(
    df: pd.DataFrame,
    screening_level: str,
    indices: List[int]
) -> pd.DataFrame:
    """
    批量审查
    
    Args:
        df: 包含筛选结果的DataFrame
        screening_level: 筛选级别
        indices: 要批量处理的索引列表
        
    Returns:
        更新后的DataFrame
    """
    df = df.copy()
    
    for idx in indices:
        if idx in df.index:
            df.loc[idx, "screening_level"] = screening_level
            df.loc[idx, "evidence_type"] = f"batch_{screening_level}"
            df.loc[idx, "reason"] = f"批量判定为{screening_level}"
            df.loc[idx, "screening_method"] = "batch_review"
    
    return df


def get_review_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    获取人工审查统计信息
    
    Args:
        df: 包含筛选结果的DataFrame
        
    Returns:
        统计信息字典
    """
    stats = {
        "total_records": len(df),
        "manual_high_count": ((df["screening_method"] == "manual_review") & (df["screening_level"] == "高相关")).sum(),
        "manual_boundary_count": ((df["screening_method"] == "manual_review") & (df["screening_level"] == "边界相关")).sum(),
        "manual_low_count": ((df["screening_method"] == "manual_review") & (df["screening_level"] == "低相关")).sum(),
        "batch_count": (df["screening_method"] == "batch_review").sum(),
        "remaining_undecided": len(get_undecided_documents(df)),
    }
    
    # 计算各筛选级别的分布
    level_counts = df["screening_level"].value_counts().to_dict()
    stats["level_distribution"] = level_counts
    
    return stats


def print_review_statistics(df: pd.DataFrame) -> None:
    """
    打印人工审查统计信息
    
    Args:
        df: 包含筛选结果的DataFrame
    """
    stats = get_review_statistics(df)
    
    print("=== 人工审查统计信息 ===")
    print(f"总记录数: {stats['total_records']}")
    print(f"人工判定高相关: {stats['manual_high_count']}")
    print(f"人工判定边界相关: {stats['manual_boundary_count']}")
    print(f"人工判定低相关: {stats['manual_low_count']}")
    print(f"批量处理: {stats['batch_count']}")
    print(f"剩余未判定: {stats['remaining_undecided']} ({stats['remaining_undecided']/stats['total_records']*100:.1f}%)")
    
    print("\n筛选级别分布:")
    for level, count in sorted(stats['level_distribution'].items()):
        print(f"  {level}: {count} ({count/stats['total_records']*100:.1f}%)")
