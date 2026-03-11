# -*- coding: utf-8 -*-
"""
配置数据结构定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class RuleMode(Enum):
    """规则模式枚举"""
    STRICT = "strict"      # 严格模式：高精准度，低召回率
    MODERATE = "moderate"  # 中等模式：平衡精准度和召回率
    LOOSE = "loose"        # 宽松模式：高召回率，可能包含更多边界文献


@dataclass
class RuleSet:
    """规则集配置"""
    name: str
    description: str = ""
    high_relevance_patterns: List[str] = field(default_factory=list)
    boundary_patterns: List[str] = field(default_factory=list)
    low_relevance_patterns: List[str] = field(default_factory=list)
    pubtype_patterns: Dict[str, List[str]] = field(default_factory=dict)
    weight: float = 1.0
    enabled: bool = True
    rule_mode: RuleMode = RuleMode.MODERATE  # 规则模式


@dataclass
class LLMConfig:
    """大模型配置"""
    provider: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout: int = 120
    max_retries: int = 3
    temperature: float = 0.0
    max_tokens: int = 2000
    enabled: bool = True


@dataclass
class ScreeningConfig:
    """筛查工作流全局配置"""
    # 基本信息
    project_name: str = "literature_screening"
    topic: str = ""
    description: str = ""
    
    # 规则模式
    rule_mode: RuleMode = RuleMode.MODERATE
    
    # 阶段开关
    enable_rule_screening: bool = True
    enable_tfidf_screening: bool = True
    enable_rank25_screening: bool = True
    enable_llm_screening: bool = True
    
    # 人工介入开关
    manual_review_after_rules: bool = True
    manual_review_after_tfidf: bool = True
    manual_review_after_rank25: bool = True
    manual_review_final: bool = True
    
    # 规则筛选配置
    rule_sets: List[RuleSet] = field(default_factory=list)
    rule_direct_high: bool = True
    rule_direct_low: bool = True
    
    # TF-IDF配置
    tfidf_seed_texts: List[str] = field(default_factory=list)
    tfidf_low_threshold: float = 0.02
    tfidf_high_threshold: float = 0.3
    
    # rank25配置
    rank_percentile: float = 25.0  # 保留前百分之多少
    rank_boundary_margin: float = 5.0  # 边界范围百分比
    
    # 输出配置
    output_dir: str = "./output"
    save_intermediate_results: bool = True
    
    # 高级配置
    max_abstract_chars: int = 3000
    skip_tfidf_layer: bool = False
    batch_size: int = 1000
    
    # 大模型配置
    llm_config: LLMConfig = field(default_factory=LLMConfig)


@dataclass
class ProjectConfig:
    """项目级配置"""
    research_topic: str = ""
    domain: str = "general"
    rule_sets: List[RuleSet] = field(default_factory=list)
    screening_config: ScreeningConfig = field(default_factory=ScreeningConfig)
    input_path: str = ""
    output_path: str = ""
    created_at: str = ""
    updated_at: str = ""
    rule_mode: RuleMode = RuleMode.MODERATE  # 项目级别的规则模式
    

@dataclass
class RuleGenerationConfig:
    """规则生成配置"""
    topic: str = ""
    include_criteria: List[str] = field(default_factory=list)
    exclude_criteria: List[str] = field(default_factory=list)
    custom_instructions: str = ""
    max_high_patterns: int = 20
    max_boundary_patterns: int = 15
    max_low_patterns: int = 15
    max_seed_texts: int = 10
    rule_mode: RuleMode = RuleMode.MODERATE  # 规则生成模式
