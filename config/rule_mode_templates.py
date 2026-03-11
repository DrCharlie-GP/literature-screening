# -*- coding: utf-8 -*-
"""
规则模式模板
提供严格、中等、宽松三种模式的预设规则模板
"""

from typing import List, Dict
from config.schema import RuleSet, RuleMode


class RuleModeTemplates:
    """规则模式模板类"""
    
    @staticmethod
    def get_strict_template(topic: str = "general") -> RuleSet:
        """
        严格模式模板
        
        特点：
        - 高相关规则：使用3-4个条件的"与"组合，确保极高精准度
        - 边界规则：使用2-3个条件的"与"组合
        - 低相关规则：使用1-2个条件的"与"组合，严格排除
        - 目标：精确率≥95%，适合需要高可信度的场景
        """
        
        # 通用严格规则（可根据主题定制）
        high_patterns = [
            # 4条件组合（最严格）
            "clinical trial + randomized + controlled + efficacy",
            "systematic review + meta-analysis + evidence + synthesis",
            "cohort study + prospective + longitudinal + follow-up",
            "intervention + randomized + double-blind + placebo",
            
            # 3条件组合（严格）
            "randomized controlled trial + primary outcome",
            "systematic review + Cochrane + meta-analysis",
            "prospective cohort + incidence + risk factors",
            "double-blind + placebo-controlled + randomized",
        ]
        
        boundary_patterns = [
            # 2-3条件组合
            "clinical study + observational",
            "retrospective cohort + analysis",
            "cross-sectional study + prevalence",
            "case-control study + risk factors",
            "pilot study + feasibility",
            "quasi-experimental + intervention",
        ]
        
        low_patterns = [
            # 严格排除
            "case report + single",
            "letter + editor + correspondence",
            "review + narrative + opinion",
            "animal study + in vivo",
            "in vitro + cell culture",
            "protocol + study design",
            "abstract only + conference",
            "commentary + editorial + perspective",
        ]
        
        pubtype_patterns = {
            "original_research": [
                "original article", "research article", "original research",
                "full text", "full-length article"
            ],
            "clinical_trial": [
                "randomized controlled trial", "clinical trial", "RCT",
                "intervention study", "therapeutic trial"
            ],
            "systematic_review": [
                "systematic review", "meta-analysis", "Cochrane review",
                "evidence synthesis", "umbrella review"
            ],
            "cohort_study": [
                "prospective cohort", "retrospective cohort", "cohort study",
                "longitudinal study", "follow-up study"
            ],
        }
        
        return RuleSet(
            name=f"严格模式规则集 - {topic}",
            description="高精准度筛选模式，使用严格的条件组合，目标精确率≥95%",
            high_relevance_patterns=high_patterns,
            boundary_patterns=boundary_patterns,
            low_relevance_patterns=low_patterns,
            pubtype_patterns=pubtype_patterns,
            weight=1.0,
            enabled=True,
            rule_mode=RuleMode.STRICT
        )
    
    @staticmethod
    def get_moderate_template(topic: str = "general") -> RuleSet:
        """
        中等模式模板
        
        特点：
        - 高相关规则：使用2-3个条件的"与"组合
        - 边界规则：使用1-2个条件的"与"组合或单条件
        - 低相关规则：使用单条件或简单组合
        - 目标：平衡精准度和召回率，适合大多数场景
        """
        
        high_patterns = [
            # 3条件组合
            "randomized controlled trial + primary",
            "systematic review + meta-analysis",
            "prospective cohort + risk factors",
            "clinical trial + efficacy + safety",
            
            # 2条件组合（主要）
            "randomized + controlled",
            "systematic review + evidence",
            "cohort study + longitudinal",
            "intervention + outcome",
            "double-blind + placebo",
            "meta-analysis + pooled",
            "prospective + incidence",
            "controlled trial + intervention",
        ]
        
        boundary_patterns = [
            # 2条件组合
            "observational study + analysis",
            "cross-sectional + prevalence",
            "case-control + association",
            "pilot study + preliminary",
            "feasibility study + intervention",
            
            # 单条件（高质量期刊特征）
            "multicenter study",
            "population-based",
            "community-based",
            "registry-based",
        ]
        
        low_patterns = [
            "case report",
            "letter",
            "editorial",
            "commentary",
            "narrative review",
            "animal study",
            "in vitro",
            "protocol",
            "abstract",
            "conference",
        ]
        
        pubtype_patterns = {
            "original_research": [
                "original article", "research article", "full text"
            ],
            "clinical_trial": [
                "randomized controlled trial", "clinical trial", "RCT",
                "controlled trial", "intervention study"
            ],
            "systematic_review": [
                "systematic review", "meta-analysis"
            ],
            "observational_study": [
                "cohort study", "case-control study", "cross-sectional study",
                "observational study"
            ],
            "review": [
                "review article", "comprehensive review"
            ],
        }
        
        return RuleSet(
            name=f"中等模式规则集 - {topic}",
            description="平衡模式，在精准度和召回率之间取得平衡，适合大多数筛查场景",
            high_relevance_patterns=high_patterns,
            boundary_patterns=boundary_patterns,
            low_relevance_patterns=low_patterns,
            pubtype_patterns=pubtype_patterns,
            weight=1.0,
            enabled=True,
            rule_mode=RuleMode.MODERATE
        )
    
    @staticmethod
    def get_loose_template(topic: str = "general") -> RuleSet:
        """
        宽松模式模板
        
        特点：
        - 高相关规则：使用1-2个条件的"与"组合或单条件
        - 边界规则：主要使用单条件
        - 低相关规则：仅排除明显无关的类型
        - 目标：高召回率，尽可能捕获所有潜在相关文献
        """
        
        high_patterns = [
            # 2条件组合（宽松）
            "randomized + trial",
            "systematic review",
            "meta-analysis",
            "cohort study",
            "clinical trial",
            "controlled study",
            "intervention study",
            "prospective study",
            "longitudinal study",
            "comparative study",
            
            # 单条件（核心概念）
            "randomized",
            "controlled trial",
            "evidence-based",
            "population study",
            "epidemiological study",
        ]
        
        boundary_patterns = [
            "observational",
            "descriptive study",
            "analytical study",
            "cross-sectional",
            "prevalence study",
            "survey",
            "questionnaire",
            "interview study",
            "focus group",
            "qualitative study",
        ]
        
        low_patterns = [
            # 仅排除明显无关的类型
            "case report only",
            "letter to editor",
            "editorial comment",
            "opinion piece",
            "animal model",
            "in vitro only",
            "conference abstract only",
        ]
        
        pubtype_patterns = {
            "research": [
                "original", "research", "study", "trial",
                "analysis", "investigation"
            ],
            "review": [
                "review", "systematic", "meta-analysis"
            ],
            "clinical": [
                "clinical", "therapeutic", "treatment",
                "intervention", "efficacy"
            ],
        }
        
        return RuleSet(
            name=f"宽松模式规则集 - {topic}",
            description="高召回率模式，使用宽松的条件，尽可能捕获所有潜在相关文献",
            high_relevance_patterns=high_patterns,
            boundary_patterns=boundary_patterns,
            low_relevance_patterns=low_patterns,
            pubtype_patterns=pubtype_patterns,
            weight=1.0,
            enabled=True,
            rule_mode=RuleMode.LOOSE
        )
    
    @staticmethod
    def get_template_by_mode(mode: RuleMode, topic: str = "general") -> RuleSet:
        """
        根据模式获取对应的规则模板
        
        Args:
            mode: 规则模式
            topic: 研究主题
            
        Returns:
            对应的规则集
        """
        if mode == RuleMode.STRICT:
            return RuleModeTemplates.get_strict_template(topic)
        elif mode == RuleMode.MODERATE:
            return RuleModeTemplates.get_moderate_template(topic)
        elif mode == RuleMode.LOOSE:
            return RuleModeTemplates.get_loose_template(topic)
        else:
            return RuleModeTemplates.get_moderate_template(topic)
    
    @staticmethod
    def get_mode_description(mode: RuleMode) -> Dict[str, str]:
        """
        获取规则模式的详细描述
        
        Args:
            mode: 规则模式
            
        Returns:
            模式描述字典
        """
        descriptions = {
            RuleMode.STRICT: {
                "name": "严格模式",
                "description": "高精准度筛选，使用严格的条件组合",
                "precision_target": "≥95%",
                "recall_target": "60-70%",
                "use_case": "需要高可信度的场景，如系统综述、Meta分析",
                "high_rule_complexity": "3-4个条件的'与'组合",
                "boundary_rule_complexity": "2-3个条件的'与'组合",
                "characteristics": [
                    "使用最严格的条件组合",
                    "高相关规则需要同时满足多个条件",
                    "边界规则也使用多条件组合",
                    "低相关规则严格排除",
                    "适合需要高精准度的场景",
                ]
            },
            RuleMode.MODERATE: {
                "name": "中等模式",
                "description": "平衡精准度和召回率",
                "precision_target": "80-90%",
                "recall_target": "75-85%",
                "use_case": "大多数筛查场景，平衡效率和质量",
                "high_rule_complexity": "2-3个条件的'与'组合",
                "boundary_rule_complexity": "1-2个条件的'与'组合或单条件",
                "characteristics": [
                    "平衡精准度和召回率",
                    "高相关规则使用中等复杂度条件",
                    "边界规则较为宽松",
                    "适合大多数筛查场景",
                    "推荐默认使用",
                ]
            },
            RuleMode.LOOSE: {
                "name": "宽松模式",
                "description": "高召回率，尽可能捕获所有潜在相关文献",
                "precision_target": "60-75%",
                "recall_target": "≥90%",
                "use_case": "初步筛查、探索性研究、确保不遗漏相关文献",
                "high_rule_complexity": "1-2个条件的'与'组合或单条件",
                "boundary_rule_complexity": "主要使用单条件",
                "characteristics": [
                    "使用最宽松的条件",
                    "高相关规则可以是单条件",
                    "边界规则非常宽松",
                    "仅排除明显无关的文献",
                    "适合需要高召回率的场景",
                ]
            }
        }
        
        return descriptions.get(mode, descriptions[RuleMode.MODERATE])


# 便捷函数
def get_strict_rules(topic: str = "general") -> RuleSet:
    """获取严格模式规则"""
    return RuleModeTemplates.get_strict_template(topic)


def get_moderate_rules(topic: str = "general") -> RuleSet:
    """获取中等模式规则"""
    return RuleModeTemplates.get_moderate_template(topic)


def get_loose_rules(topic: str = "general") -> RuleSet:
    """获取宽松模式规则"""
    return RuleModeTemplates.get_loose_template(topic)


def get_rules_by_mode(mode: RuleMode, topic: str = "general") -> RuleSet:
    """根据模式获取规则"""
    return RuleModeTemplates.get_template_by_mode(mode, topic)


def get_rule_mode_description(mode: RuleMode, language: str = "chinese") -> Dict[str, str]:
    """
    获取规则模式的用户友好描述
    
    Args:
        mode: 规则模式
        language: 语言 (chinese/english)
        
    Returns:
        包含名称和描述的字典
    """
    descriptions = {
        "chinese": {
            RuleMode.STRICT: {
                "name": "严格模式",
                "description": "高精确率 (≥95%)，适合需要高度相关文献的场景，如系统性综述、Meta分析",
                "short_name": "严格"
            },
            RuleMode.MODERATE: {
                "name": "中等模式",
                "description": "平衡精确率和召回率，适合大多数研究场景，推荐默认使用",
                "short_name": "中等"
            },
            RuleMode.LOOSE: {
                "name": "宽松模式",
                "description": "高召回率 (≥90%)，适合需要全面收集文献的场景，如文献计量分析",
                "short_name": "宽松"
            }
        },
        "english": {
            RuleMode.STRICT: {
                "name": "Strict Mode",
                "description": "High precision (≥95%), suitable for scenarios requiring highly relevant literature",
                "short_name": "Strict"
            },
            RuleMode.MODERATE: {
                "name": "Moderate Mode",
                "description": "Balanced precision and recall, suitable for most research scenarios",
                "short_name": "Moderate"
            },
            RuleMode.LOOSE: {
                "name": "Loose Mode",
                "description": "High recall (≥90%), suitable for comprehensive literature collection",
                "short_name": "Loose"
            }
        }
    }
    
    lang_desc = descriptions.get(language, descriptions["chinese"])
    return lang_desc.get(mode, lang_desc[RuleMode.MODERATE])


def get_rule_mode_comparison() -> str:
    """
    获取规则模式对比表（文本格式）
    
    Returns:
        格式化的对比表格字符串
    """
    comparison = """
┌──────────────┬────────────┬────────────┬─────────────────────────────┐
│   规则模式    │  精确率目标  │  召回率目标  │         适用场景              │
├──────────────┼────────────┼────────────┼─────────────────────────────┤
│  严格模式     │    ≥95%    │   60-70%   │ 系统综述、Meta分析、高质量研究 │
│  中等模式     │   80-90%   │   75-85%   │ 一般文献综述、初步筛选 [推荐]  │
│  宽松模式     │   60-75%   │    ≥90%    │ 文献计量分析、全面调研、探索性研究│
└──────────────┴────────────┴────────────┴─────────────────────────────┘

规则复杂度说明:
  • 严格模式: 高相关规则使用3-4个条件的"与"组合
  • 中等模式: 高相关规则使用2-3个条件的"与"组合
  • 宽松模式: 高相关规则使用1-2个条件的"与"组合或单条件
"""
    return comparison
