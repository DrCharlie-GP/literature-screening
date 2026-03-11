# -*- coding: utf-8 -*-
"""
规则筛选引擎模块
基于规则集对文献进行初步筛选
支持"与"关系的条件组合
"""

import re
from typing import List, Dict, Any, Union
from dataclasses import dataclass, field

import pandas as pd

from config import RuleSet
from core.data_loader import safe_str


class RuleEngineError(Exception):
    """规则引擎异常"""
    pass


@dataclass
class CombinedRule:
    """
    组合规则
    支持"与"关系的多个条件组合
    
    例如：
    - 同时出现"骨量"和"年变化率"
    - 同时出现"骨量"和"队列研究"
    """
    name: str  # 规则名称
    conditions: List[str]  # 条件列表（所有条件必须同时满足）
    rule_type: str = "high"  # high, boundary, low
    weight: float = 1.0
    
    def match(self, text: str) -> bool:
        """
        检查文本是否匹配所有条件（"与"关系）
        
        Args:
            text: 待检查的文本
            
        Returns:
            是否匹配所有条件
        """
        for condition in self.conditions:
            if not _match_pattern(text, condition):
                return False
        return True
    
    def get_matched_conditions(self, text: str) -> List[str]:
        """
        获取匹配的条件列表
        
        Args:
            text: 待检查的文本
            
        Returns:
            匹配的条件列表
        """
        matched = []
        for condition in self.conditions:
            if _match_pattern(text, condition):
                matched.append(condition)
        return matched


def _match_pattern(text: str, pattern: str) -> bool:
    """
    匹配单个模式
    
    Args:
        text: 待检查的文本
        pattern: 匹配模式（支持正则表达式或简单字符串）
        
    Returns:
        是否匹配
    """
    try:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    except re.error:
        # 正则表达式无效，使用简单字符串匹配
        if pattern.lower() in text.lower():
            return True
    return False


def _match_any(text: str, patterns: List[str]) -> List[str]:
    """匹配任意模式（"或"关系）"""
    hits = []
    for p in patterns or []:
        if _match_pattern(text, p):
            hits.append(p)
    return hits


def convert_to_combined_rules(rule_set: RuleSet) -> Dict[str, List[CombinedRule]]:
    """
    将传统规则集转换为组合规则
    
    转换策略：
    1. 如果模式包含"+"，则拆分为多个条件的"与"关系
    2. 否则作为单条件的规则
    
    Args:
        rule_set: 传统规则集
        
    Returns:
        组合规则字典
    """
    combined_rules = {
        "high": [],
        "boundary": [],
        "low": []
    }
    
    # 转换高相关规则
    for pattern in rule_set.high_relevance_patterns or []:
        if "+" in pattern:
            # "与"关系：拆分为多个条件
            conditions = [p.strip() for p in pattern.split("+")]
            combined_rules["high"].append(CombinedRule(
                name=f"high_combined_{len(combined_rules['high'])}",
                conditions=conditions,
                rule_type="high",
                weight=rule_set.weight
            ))
        else:
            # 单条件规则
            combined_rules["high"].append(CombinedRule(
                name=f"high_single_{len(combined_rules['high'])}",
                conditions=[pattern],
                rule_type="high",
                weight=rule_set.weight
            ))
    
    # 转换边界规则
    for pattern in rule_set.boundary_patterns or []:
        if "+" in pattern:
            conditions = [p.strip() for p in pattern.split("+")]
            combined_rules["boundary"].append(CombinedRule(
                name=f"boundary_combined_{len(combined_rules['boundary'])}",
                conditions=conditions,
                rule_type="boundary",
                weight=rule_set.weight * 0.5
            ))
        else:
            combined_rules["boundary"].append(CombinedRule(
                name=f"boundary_single_{len(combined_rules['boundary'])}",
                conditions=[pattern],
                rule_type="boundary",
                weight=rule_set.weight * 0.5
            ))
    
    # 转换低相关规则
    for pattern in rule_set.low_relevance_patterns or []:
        if "+" in pattern:
            conditions = [p.strip() for p in pattern.split("+")]
            combined_rules["low"].append(CombinedRule(
                name=f"low_combined_{len(combined_rules['low'])}",
                conditions=conditions,
                rule_type="low",
                weight=rule_set.weight
            ))
        else:
            combined_rules["low"].append(CombinedRule(
                name=f"low_single_{len(combined_rules['low'])}",
                conditions=[pattern],
                rule_type="low",
                weight=rule_set.weight
            ))
    
    return combined_rules


def rule_based_screening(
    df: pd.DataFrame, 
    rule_sets: List[RuleSet]
) -> pd.DataFrame:
    """
    基于规则的筛选（支持"与"关系的条件组合）
    
    规则逻辑：
    - 规则条目之间为"或"关系（满足任一规则即可）
    - 每个规则条目内部的多个条件为"与"关系（必须同时满足）
    
    为每条记录添加：
      - rule_high_hits: 命中的高相关规则
      - rule_boundary_hits: 命中的边界规则
      - rule_low_hits: 命中的低相关规则
      - rule_pubtype: 识别出的文献类型
      - rule_tier: 规则层判定（rule_high / rule_boundary / rule_low / rule_unclear）
      - rule_score: 规则综合得分
    """
    df = df.copy()
    
    high_hits_col = []
    boundary_hits_col = []
    low_hits_col = []
    pubtype_col = []
    tier_col = []
    score_col = []
    
    for _, row in df.iterrows():
        text = " ".join([
            safe_str(row.get("title", "")),
            safe_str(row.get("abstract", "")),
            safe_str(row.get("keywords", "")),
        ])
        
        total_high = 0
        total_boundary = 0
        total_low = 0
        all_high_hits = []
        all_boundary_hits = []
        all_low_hits = []
        all_pubtypes = []
        
        # 应用所有启用的规则集
        for rule_set in rule_sets:
            if not rule_set.enabled:
                continue
            
            # 转换为组合规则
            combined_rules = convert_to_combined_rules(rule_set)
            
            # 检查高相关规则（"与"关系）
            for rule in combined_rules["high"]:
                if rule.match(text):
                    matched_conditions = rule.get_matched_conditions(text)
                    all_high_hits.append(f"{rule.name}({'+'.join(matched_conditions)})")
                    total_high += len(matched_conditions) * rule.weight
            
            # 检查边界规则（"与"关系）
            for rule in combined_rules["boundary"]:
                if rule.match(text):
                    matched_conditions = rule.get_matched_conditions(text)
                    all_boundary_hits.append(f"{rule.name}({'+'.join(matched_conditions)})")
                    total_boundary += len(matched_conditions) * rule.weight
            
            # 检查低相关规则（"与"关系）
            for rule in combined_rules["low"]:
                if rule.match(text):
                    matched_conditions = rule.get_matched_conditions(text)
                    all_low_hits.append(f"{rule.name}({'+'.join(matched_conditions)})")
                    total_low += len(matched_conditions) * rule.weight
            
            # 文献类型检测（保持原有逻辑）
            pubtypes = []
            for ptype, patterns in (rule_set.pubtype_patterns or {}).items():
                if _match_any(text, patterns):
                    pubtypes.append(ptype)
            
            all_pubtypes.extend(pubtypes)
        
        # 综合判定
        if total_high > 0 and total_low == 0:
            tier = "rule_high"
            score = total_high
        elif total_boundary > 0 and total_low == 0:
            tier = "rule_boundary"
            score = total_boundary * 0.5
        elif total_low > 0 and total_high == 0 and total_boundary == 0:
            tier = "rule_low"
            score = -total_low
        else:
            tier = "rule_unclear"
            score = 0.0
        
        high_hits_col.append("; ".join(all_high_hits) if all_high_hits else "")
        boundary_hits_col.append("; ".join(all_boundary_hits) if all_boundary_hits else "")
        low_hits_col.append("; ".join(all_low_hits) if all_low_hits else "")
        pubtype_col.append("; ".join(list(set(all_pubtypes))) if all_pubtypes else "")
        tier_col.append(tier)
        score_col.append(score)
    
    df["rule_high_hits"] = high_hits_col
    df["rule_boundary_hits"] = boundary_hits_col
    df["rule_low_hits"] = low_hits_col
    df["rule_pubtype"] = pubtype_col
    df["rule_tier"] = tier_col
    df["rule_score"] = score_col
    
    return df


def apply_rule_direct_judgment(
    df: pd.DataFrame, 
    direct_high: bool = True, 
    direct_low: bool = True,
    rule_mode: str = "moderate",
    review_threshold: float = 0.5
) -> pd.DataFrame:
    """
    应用规则直判
    直接标记高相关或低相关文献
    
    Args:
        df: 文献数据框
        direct_high: 是否直判高相关
        direct_low: 是否直判低相关
        rule_mode: 规则模式 (strict/moderate/loose)
        review_threshold: 复核阈值，低于此分数的文献需要复核
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
    if "needs_review" not in df.columns:
        df["needs_review"] = False
    if "review_reason" not in df.columns:
        df["review_reason"] = ""
    
    if direct_high:
        mask_high = df["rule_tier"] == "rule_high"
        
        # 宽松模式下，对低分高相关文献标记需复核
        if rule_mode == "loose":
            # 单条件匹配的高相关文献需要复核
            mask_single_condition = mask_high & (df["rule_score"] < review_threshold * 2)
            df.loc[mask_single_condition, "needs_review"] = True
            df.loc[mask_single_condition, "review_reason"] = "宽松模式：单条件匹配，建议复核"
            
            # 综述、信件等文献类型需要复核
            mask_pubtype_review = mask_high & df["rule_pubtype"].str.contains("review|letter|comment|editorial", case=False, na=False)
            df.loc[mask_pubtype_review, "needs_review"] = True
            df.loc[mask_pubtype_review, "review_reason"] = "宽松模式：综述/信件/评论类文献，建议复核"
        
        df.loc[mask_high, "screening_level"] = "高相关"
        df.loc[mask_high, "evidence_type"] = "rule_pattern_matched"
        df.loc[mask_high, "reason"] = "规则层直判：命中高相关特征"
        df.loc[mask_high, "screening_method"] = "rule_direct_high"
    
    if direct_low:
        mask_low = df["rule_tier"] == "rule_low"
        df.loc[mask_low, "screening_level"] = "低相关"
        df.loc[mask_low, "evidence_type"] = "not_applicable"
        df.loc[mask_low, "reason"] = "规则层直判：命中低相关特征"
        df.loc[mask_low, "screening_method"] = "rule_direct_low"
    
    # 对边界文献标记需关注
    mask_boundary = df["rule_tier"] == "rule_boundary"
    df.loc[mask_boundary, "needs_review"] = True
    df.loc[mask_boundary, "review_reason"] = "边界文献：需要进一步评估"
    
    return df


def get_rule_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    获取规则筛选统计信息
    """
    stats = {
        "total_records": len(df),
        "rule_high_count": int((df["rule_tier"] == "rule_high").sum()),
        "rule_boundary_count": int((df["rule_tier"] == "rule_boundary").sum()),
        "rule_low_count": int((df["rule_tier"] == "rule_low").sum()),
        "rule_unclear_count": int((df["rule_tier"] == "rule_unclear").sum()),
        "direct_high_count": int((df["screening_method"] == "rule_direct_high").sum()),
        "direct_low_count": int((df["screening_method"] == "rule_direct_low").sum()),
    }
    
    # 计算各类型文献分布
    pubtype_stats = {}
    for pubtypes in df["rule_pubtype"].dropna():
        if not pubtypes or pubtypes == "":
            pubtype_stats["unknown"] = pubtype_stats.get("unknown", 0) + 1
        else:
            for ptype in pubtypes.split("; "):
                pubtype_stats[ptype] = pubtype_stats.get(ptype, 0) + 1
    stats["pubtype_distribution"] = pubtype_stats
    
    # 计算需复核文献统计
    if "needs_review" in df.columns:
        stats["needs_review_count"] = int(df["needs_review"].sum())
        stats["needs_review_percentage"] = stats["needs_review_count"] / stats["total_records"] * 100 if stats["total_records"] > 0 else 0
        
        # 按原因分类统计
        review_reason_stats = {}
        for reason in df[df["needs_review"] == True]["review_reason"].dropna():
            if reason:
                review_reason_stats[reason] = review_reason_stats.get(reason, 0) + 1
        stats["review_reason_distribution"] = review_reason_stats
    
    return stats


def print_rule_statistics(df: pd.DataFrame) -> None:
    """
    打印规则筛选统计信息
    """
    stats = get_rule_statistics(df)
    
    print("=== 规则筛选统计信息 ===")
    print(f"总记录数: {stats['total_records']}")
    print(f"规则高相关: {stats['rule_high_count']} ({stats['rule_high_count']/stats['total_records']*100:.1f}%)")
    print(f"规则边界: {stats['rule_boundary_count']} ({stats['rule_boundary_count']/stats['total_records']*100:.1f}%)")
    print(f"规则低相关: {stats['rule_low_count']} ({stats['rule_low_count']/stats['total_records']*100:.1f}%)")
    print(f"规则未明确: {stats['rule_unclear_count']} ({stats['rule_unclear_count']/stats['total_records']*100:.1f}%)")
    print(f"直接判定高相关: {stats['direct_high_count']} ({stats['direct_high_count']/stats['total_records']*100:.1f}%)")
    print(f"直接判定低相关: {stats['direct_low_count']} ({stats['direct_low_count']/stats['total_records']*100:.1f}%)")
    
    print("\n文献类型分布:")
    for ptype, count in sorted(stats['pubtype_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {ptype}: {count}")
    
    # 打印需复核文献统计
    if "needs_review_count" in stats:
        print("\n" + "="*50)
        print("【需关注】文献复核统计")
        print("="*50)
        print(f"需复核文献总数: {stats['needs_review_count']} ({stats['needs_review_percentage']:.1f}%)")
        
        if stats.get('review_reason_distribution'):
            print("\n需复核原因分布:")
            for reason, count in sorted(stats['review_reason_distribution'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count}")
        
        # 特别关注边界文献
        boundary_needs_review = stats['rule_boundary_count']
        if boundary_needs_review > 0:
            print(f"\n⚠️  边界文献需特别关注: {boundary_needs_review} 条")
            print("   建议：对边界文献进行人工审查，确认其与研究主题的相关性")
        
        # 宽松模式警告
        if stats.get('needs_review_percentage', 0) > 30:
            print("\n⚠️  警告：需复核文献比例较高 (>30%)")
            print("   建议：考虑切换到中等模式或严格模式以提高筛选精度")


def create_combined_rule_example():
    """
    创建组合规则示例
    
    示例：骨量减少速率主题的规则
    """
    # 高相关规则（"与"关系）
    high_rules = [
        "骨量+年变化率",  # 同时出现"骨量"和"年变化率"
        "骨量+队列研究",  # 同时出现"骨量"和"队列研究"
        "骨密度+纵向研究",  # 同时出现"骨密度"和"纵向研究"
        "bone mass+annual change",  # 英文示例
        "BMD+longitudinal",  # 英文示例
    ]
    
    # 边界规则
    boundary_rules = [
        "骨量+横断面",  # 同时出现"骨量"和"横断面"
        "骨密度+横断面",
    ]
    
    # 低相关规则
    low_rules = [
        "骨量+动物实验",  # 同时出现"骨量"和"动物实验"
        "骨密度+体外研究",
        "bone+in vitro",
    ]
    
    return RuleSet(
        name="骨量减少速率组合规则",
        description="使用'与'关系的条件组合规则",
        high_relevance_patterns=high_rules,
        boundary_patterns=boundary_rules,
        low_relevance_patterns=low_rules,
        weight=1.0,
        enabled=True
    )
