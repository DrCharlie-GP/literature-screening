# -*- coding: utf-8 -*-
"""
核心功能模块
包含文献筛查的主要功能
"""

# 数据加载模块
from .data_loader import (
    load_records,
    standardize_columns,
    clean_dataframe,
    safe_str
)

# 规则引擎模块
from .rule_engine import (
    rule_based_screening,
    apply_rule_direct_judgment,
    get_rule_statistics,
    print_rule_statistics
)

# TF-IDF评分模块
from .tfidf_scorer import (
    tfidf_scoring,
    apply_tfidf_threshold,
    get_tfidf_statistics,
    print_tfidf_statistics
)

# Rank25筛选模块
from .rank_filter import (
    calculate_rank_score,
    rank25_filter,
    apply_rank_direct_judgment,
    get_rank_statistics,
    print_rank_statistics
)

# LLM客户端模块
from .llm_client import (
    get_llm_client,
    LLMClientError
)

# 人工审查模块
from .manual_review import (
    manual_review,
    batch_review,
    get_undecided_documents,
    get_review_statistics,
    print_review_statistics
)

__all__ = [
    # 数据加载
    "load_records",
    "standardize_columns",
    "clean_dataframe",
    "safe_str",
    
    # 规则引擎
    "rule_based_screening",
    "apply_rule_direct_judgment",
    "get_rule_statistics",
    "print_rule_statistics",
    
    # TF-IDF评分
    "tfidf_scoring",
    "apply_tfidf_threshold",
    "get_tfidf_statistics",
    "print_tfidf_statistics",
    
    # Rank25筛选
    "calculate_rank_score",
    "rank25_filter",
    "apply_rank_direct_judgment",
    "get_rank_statistics",
    "print_rank_statistics",
    
    # LLM客户端
    "get_llm_client",
    "LLMClientError",
    
    # 人工审查
    "manual_review",
    "batch_review",
    "get_undecided_documents",
    "get_review_statistics",
    "print_review_statistics"
]
