# -*- coding: utf-8 -*-
"""
预设规则模板库
"""

from typing import List
from .schema import RuleSet


# 默认文献类型模式
DEFAULT_PUBTYPE_PATTERNS = {
    "letter": [r"\bletter\b", r"\bcorrespondence\b"],
    "reply": [r"\breply\b", r"\bresponse\s*to\b", r"\bin\s*reply\b"],
    "comment": [r"\bcomment(?:ary)?\b", r"\beditorial\b"],
    "protocol": [r"\bprotocol\b", r"\bstudy\s*design\b", r"\btrial\s*registr"],
    "review": [r"systematic\s*review", r"meta[\s-]*analy", r"\bscoping\s*review\b"],
}


def get_default_rule_set() -> RuleSet:
    """获取默认规则集"""
    return RuleSet(
        name="default_rules",
        description="默认规则集",
        pubtype_patterns=DEFAULT_PUBTYPE_PATTERNS,
        enabled=True,
    )


def get_medical_research_template() -> RuleSet:
    """获取医学研究规则模板"""
    return RuleSet(
        name="medical_research",
        description="医学研究通用规则",
        high_relevance_patterns=[
            r"clinical\s*trial", r"randomized", r"placebo\s*controlled",
            r"longitudinal", r"prospective", r"cohort",
            r"meta[-\s]*analysis", r"systematic\s*review",
        ],
        boundary_patterns=[
            r"case\s*control", r"cross[-\s]*sectional",
            r"observational", r"retrospective",
        ],
        low_relevance_patterns=[
            r"animal\s*study", r"in\s*vitro",
            r"review\s*article", r"commentary", r"editorial",
            r"letter", r"correspondence",
        ],
        pubtype_patterns=DEFAULT_PUBTYPE_PATTERNS,
    )


def get_basic_science_template() -> RuleSet:
    """获取基础科学规则模板"""
    return RuleSet(
        name="basic_science",
        description="基础科学研究通用规则",
        high_relevance_patterns=[
            r"mechanism", r"pathway", r"molecular",
            r"cellular", r"genetic", r"proteomic",
            r"in\s*vitro", r"in\s*vivo",
        ],
        boundary_patterns=[
            r"computational", r"bioinformatic",
            r"theoretical", r"model",
        ],
        low_relevance_patterns=[
            r"clinical\s*trial", r"human\s*study",
            r"case\s*report", r"clinical\s*practice",
        ],
        pubtype_patterns=DEFAULT_PUBTYPE_PATTERNS,
    )


def get_clinical_research_template() -> RuleSet:
    """获取临床研究规则模板"""
    return RuleSet(
        name="clinical_research",
        description="临床研究通用规则",
        high_relevance_patterns=[
            r"patient", r"clinical", r"treatment",
            r"therapy", r"diagnosis", r"prognosis",
            r"outcome", r"survival",
        ],
        boundary_patterns=[
            r"case\s*series", r"case\s*report",
            r"retrospective", r"chart\s*review",
        ],
        low_relevance_patterns=[
            r"animal\s*model", r"in\s*vitro",
            r"basic\s*science", r"preclinical",
        ],
        pubtype_patterns=DEFAULT_PUBTYPE_PATTERNS,
    )


# 规则模板映射
RULE_TEMPLATES = {
    "default": get_default_rule_set,
    "medical": get_medical_research_template,
    "clinical": get_clinical_research_template,
    "basic": get_basic_science_template,
}


def list_available_templates() -> List[str]:
    """列出所有可用的规则模板"""
    return list(RULE_TEMPLATES.keys())


def get_template_by_name(name: str) -> RuleSet:
    """根据名称获取规则模板"""
    if name in RULE_TEMPLATES:
        return RULE_TEMPLATES[name]()
    return get_default_rule_set()


def get_preset_rules(domain: str = "general") -> List[RuleSet]:
    """
    根据研究领域获取预设规则集
    
    Args:
        domain: 研究领域
        
    Returns:
        规则集列表
    """
    # 根据领域选择合适的规则模板
    if domain == "medicine" or domain == "medical":
        return [get_medical_research_template()]
    elif domain == "biology" or domain == "basic_science":
        return [get_basic_science_template()]
    elif domain == "clinical" or domain == "clinical_research":
        return [get_clinical_research_template()]
    else:
        # 默认返回空规则集，让用户配置
        return [get_default_rule_set()]
