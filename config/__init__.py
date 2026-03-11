# -*- coding: utf-8 -*-
"""
配置模块
"""

from .schema import (
    RuleSet,
    LLMConfig,
    ScreeningConfig,
    ProjectConfig,
    RuleGenerationConfig,
    RuleMode,
)
from .preset_rules import (
    DEFAULT_PUBTYPE_PATTERNS,
    get_default_rule_set,
    get_medical_research_template,
    get_basic_science_template,
    get_clinical_research_template,
    list_available_templates,
    get_template_by_name,
    get_preset_rules,
)
from .rule_mode_templates import (
    RuleModeTemplates,
    get_strict_rules,
    get_moderate_rules,
    get_loose_rules,
    get_rules_by_mode,
    get_rule_mode_description,
    get_rule_mode_comparison,
)

__all__ = [
    # 配置数据结构
    "RuleSet",
    "LLMConfig",
    "ScreeningConfig",
    "ProjectConfig",
    "RuleGenerationConfig",
    "RuleMode",
    
    # 预设规则
    "DEFAULT_PUBTYPE_PATTERNS",
    "get_default_rule_set",
    "get_medical_research_template",
    "get_basic_science_template",
    "get_clinical_research_template",
    "list_available_templates",
    "get_template_by_name",
    "get_preset_rules",
    
    # 规则模式模板
    "RuleModeTemplates",
    "get_strict_rules",
    "get_moderate_rules",
    "get_loose_rules",
    "get_rules_by_mode",
    "get_rule_mode_description",
    "get_rule_mode_comparison",
]
