# -*- coding: utf-8 -*-
"""
配置文件管理模块
用于保存和加载配置
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from config import LLMConfig, ProjectConfig


class ConfigManager:
    """
    配置文件管理器
    """
    
    def __init__(self, config_dir: str = ".config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件保存目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.llm_config_file = self.config_dir / "llm_config.json"
        self.project_config_file = self.config_dir / "project_config.json"
    
    def save_llm_config(self, config: LLMConfig) -> None:
        """
        保存LLM配置
        
        Args:
            config: LLM配置对象
        """
        config_dict = {
            "provider": config.provider,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        with open(self.llm_config_file, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    
    def load_llm_config(self) -> Optional[LLMConfig]:
        """
        加载LLM配置
        
        Returns:
            LLM配置对象，如果文件不存在则返回None
        """
        if not self.llm_config_file.exists():
            return None
        
        with open(self.llm_config_file, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        
        return LLMConfig(**config_dict)
    
    def save_project_config(self, config: ProjectConfig) -> None:
        """
        保存项目配置
        
        Args:
            config: 项目配置对象
        """
        # 转换规则集为字典
        rule_sets_dict = []
        for rule_set in config.rule_sets:
            rule_sets_dict.append({
                "name": rule_set.name,
                "description": rule_set.description,
                "high_relevance_patterns": rule_set.high_relevance_patterns,
                "boundary_patterns": rule_set.boundary_patterns,
                "low_relevance_patterns": rule_set.low_relevance_patterns,
                "pubtype_patterns": rule_set.pubtype_patterns,
                "weight": rule_set.weight,
                "enabled": rule_set.enabled
            })
        
        config_dict = {
            "research_topic": getattr(config, "research_topic", ""),
            "domain": getattr(config, "domain", ""),
            "rule_sets": rule_sets_dict
        }
        
        with open(self.project_config_file, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    
    def load_project_config(self) -> Optional[Dict[str, Any]]:
        """
        加载项目配置
        
        Returns:
            项目配置字典，如果文件不存在则返回None
        """
        if not self.project_config_file.exists():
            return None
        
        with open(self.project_config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def has_saved_config(self) -> bool:
        """
        检查是否有保存的配置
        
        Returns:
            是否有保存的配置
        """
        return self.llm_config_file.exists()
    
    def delete_configs(self) -> None:
        """
        删除所有配置文件
        """
        if self.llm_config_file.exists():
            self.llm_config_file.unlink()
        if self.project_config_file.exists():
            self.project_config_file.unlink()


# 创建全局配置管理器实例
config_manager = ConfigManager()
