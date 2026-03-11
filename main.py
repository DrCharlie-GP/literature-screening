#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用文献筛查工作流
交互式命令行入口

重构版本：
- 语义理解分为两个分支：边界文献筛选 + 高相关文献深度分析
- 采用"human in loop"模式，人工判断贯穿整个流程
"""

import os
import sys
import json
import re
import argparse
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入核心功能
from core import (
    load_records,
    rule_based_screening,
    apply_rule_direct_judgment,
    print_rule_statistics,
    tfidf_scoring,
    apply_tfidf_threshold,
    print_tfidf_statistics,
    calculate_rank_score,
    rank25_filter,
    apply_rank_direct_judgment as apply_rank_judgment,
    print_rank_statistics,
    get_llm_client,
    manual_review,
    print_review_statistics
)
from core.config_manager import config_manager

# 导入配置类
from config import (
    RuleSet, LLMConfig, ScreeningConfig, ProjectConfig, RuleGenerationConfig,
    RuleMode, get_preset_rules, get_rule_mode_description, get_rule_mode_comparison
)


# ==================== 全局配置常量 ====================
BATCH_SIZE = 5   # 每批次处理文献数量
MAX_RETRY = 3    # 最大重试次数


# ==================== 全局状态管理 ====================
class ScreeningState:
    """筛查流程状态管理"""
    def __init__(self):
        self.df = None  # 文献数据
        self.project_config = None  # 项目配置
        self.llm_config = None  # LLM配置（规则生成）
        self.semantic_llm_config = None  # 语义理解专用LLM配置
        self.language = "chinese"  # 文献语言
        self.stage = "init"  # 当前阶段
        self.candidate_pool = []  # 候选文献池（高相关）
        self.boundary_pool = []  # 边界文献池
        self.semantic_results = {}  # 语义分析结果缓存
        self.rule_mode = RuleMode.MODERATE  # 规则模式（默认中等）
        self.semantic_checkpoint = None  # 语义分析断点信息
        
        # Human-in-loop 设置
        self.enable_human_review = True  # 是否启用人工审查
        self.review_threshold = 0.7  # 人工审查阈值（置信度低于此值时触发）
        self.review_interval = 10  # 每处理N条文献后询问是否继续
        
        # 批量处理配置
        self.batch_size = BATCH_SIZE  # 批次大小
        self.max_retry = MAX_RETRY  # 最大重试次数

# 创建全局状态实例
state = ScreeningState()


def print_menu():
    """打印主菜单"""
    print("\n" + "="*50)
    print("        通用文献筛查工作流")
    print("="*50)
    print("1. 加载文献数据")
    print("2. 配置研究主题和规则")
    print("3. 运行完整筛查流程（含语义理解）")
    print("4. 仅运行规则筛选")
    print("5. 配置语义理解模型")
    print("6. 配置人工审查选项")
    print("7. 查看筛选统计")
    print("8. 保存筛选结果")
    print("9. 退出")
    print("="*50)
    print(f"当前阶段: {state.stage}")
    
    # 显示规则模式
    mode_desc = get_rule_mode_description(state.rule_mode, state.language)
    print(f"规则模式: {mode_desc['name']}")
    
    if state.enable_human_review:
        print("[Human-in-Loop模式: 已启用]")


def clean_file_path(file_path: str) -> str:
    """清理文件路径，去除前后的双引号"""
    file_path = file_path.strip()
    if file_path.startswith('"') and file_path.endswith('"'):
        file_path = file_path[1:-1]
    elif file_path.startswith("'") and file_path.endswith("'"):
        file_path = file_path[1:-1]
    return file_path


def select_language():
    """选择文献语言"""
    print("\n=== 选择文献语言 ===")
    print("1. 中文")
    print("2. 英文")
    choice = input("请选择文献语言 (1-2): ").strip()
    
    if choice == "2":
        state.language = "english"
        print("✓ 已选择英文文献")
    else:
        state.language = "chinese"
        print("✓ 已选择中文文献")
    
    return state.language


def configure_llm_interactive(config_name="默认"):
    """配置大模型"""
    print(f"\n=== 配置{config_name}大模型 ===")
    
    supported_providers = ["openai", "deepseek", "kimi", "doubao", "qwen", "claude", "mock"]
    print("支持的模型提供商:")
    for i, p in enumerate(supported_providers, 1):
        print(f"{i}. {p}")
    provider_choice = input(f"请选择提供商 (1-{len(supported_providers)}): ").strip()
    
    if provider_choice.isdigit() and 1 <= int(provider_choice) <= len(supported_providers):
        provider = supported_providers[int(provider_choice)-1]
    else:
        provider = input(f"请输入LLM提供商 ({', '.join(supported_providers)}): ").strip().lower() or "mock"
    
    if provider != "mock":
        print(f"\n配置 {provider} 模型:")
        api_key = input("请输入API Key: ").strip()
        base_url = input("请输入API基础URL (可选): ").strip()
        model = input("请输入模型名称: ").strip() or f"{provider}-default"
        temperature = input("请输入温度参数 (0.0-2.0, 默认: 0.3): ").strip()
        temperature = float(temperature) if temperature else 0.3
        max_tokens = input("请输入最大生成 tokens (默认: 2000): ").strip()
        max_tokens = int(max_tokens) if max_tokens else 2000
        timeout = input("请输入API超时时间 (秒，默认: 120): ").strip()
        timeout = int(timeout) if timeout else 120
    else:
        api_key = "mock_key"
        base_url = ""
        model = "mock_model"
        temperature = 0.3
        max_tokens = 2000
        timeout = 120
    
    return LLMConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout
    )


def human_review_prompt(doc_info: Dict, current_judgment: str, confidence: float) -> str:
    """Human-in-loop 审查提示"""
    if not state.enable_human_review:
        return current_judgment
    
    if confidence >= state.review_threshold:
        return current_judgment
    
    print(f"\n--- Human-in-Loop 审查 ---")
    print(f"标题: {doc_info.get('title', 'N/A')[:80]}...")
    print(f"当前判定: {current_judgment}")
    print(f"置信度: {confidence:.2f} (低于阈值 {state.review_threshold})")
    
    print("\n选项:")
    print("1. 接受当前判定")
    print("2. 改为高相关")
    print("3. 改为边界相关")
    print("4. 改为低相关")
    print("5. 跳过，稍后处理")
    
    choice = input("请选择 (1-5): ").strip()
    
    if choice == "1":
        return current_judgment
    elif choice == "2":
        return "高相关"
    elif choice == "3":
        return "边界相关"
    elif choice == "4":
        return "低相关"
    else:
        return current_judgment


def generate_rules_with_interaction(research_topic, domain, llm_config, language, rule_mode: RuleMode = RuleMode.MODERATE):
    """生成规则并处理交互"""
    rule_sets = []
    retry_count = 0
    max_retries = 3
    current_rules = None
    
    mode_desc = get_rule_mode_description(rule_mode, language)
    print(f"\n当前规则模式: {mode_desc['name']}")
    print(f"模式说明: {mode_desc['description']}")
    
    while retry_count <= max_retries:
        try:
            print(f"\n正在生成规则... (尝试 {retry_count + 1}/{max_retries + 1})")
            llm_client = get_llm_client(llm_config)
            current_rules = llm_client.generate_rule_suggestions(
                research_topic, 
                domain=domain,
                language=language,
                rule_mode=rule_mode
            )
            
            print("\n=== 生成的规则 ===")
            print("高相关模式:")
            for rule in current_rules["high_relevance_patterns"]:
                print(f"  - {rule}")
            print("\n边界模式:")
            for rule in current_rules["boundary_patterns"]:
                print(f"  - {rule}")
            print("\n低相关模式:")
            for rule in current_rules["low_relevance_patterns"]:
                print(f"  - {rule}")
            
            if state.enable_human_review:
                print("\n=== 规则审查 ===")
                print("1. 接受这些规则")
                print("2. 重新生成规则")
                print("3. 输入修订意见优化规则")
                print("4. 使用预设规则")
                
                choice = input("\n请选择 (1-4): ").strip()
            else:
                choice = "1"
            
            if choice == "1":
                rule_set = RuleSet(
                    name="LLM生成规则",
                    enabled=True,
                    weight=1.0,
                    high_relevance_patterns=current_rules["high_relevance_patterns"],
                    boundary_patterns=current_rules["boundary_patterns"],
                    low_relevance_patterns=current_rules["low_relevance_patterns"],
                    pubtype_patterns={}
                )
                rule_sets.append(rule_set)
                print("✓ 已接受生成的规则")
                return rule_sets
                
            elif choice == "2":
                retry_count += 1
                print("\n重新生成规则...")
                continue
                
            elif choice == "3":
                feedback = input("\n请输入修订意见: ").strip()
                
                if feedback:
                    print("\n正在根据反馈优化规则...")
                    try:
                        optimized_rules = llm_client.refine_rules(
                            current_rules,
                            feedback,
                            language=language
                        )
                        
                        print("\n=== 优化后的规则 ===")
                        print("高相关模式:")
                        for rule in optimized_rules["high_relevance_patterns"]:
                            print(f"  - {rule}")
                        
                        accept = input("\n是否接受优化后的规则? (y/n): ").strip().lower() == "y"
                        
                        if accept:
                            rule_set = RuleSet(
                                name="LLM优化规则",
                                enabled=True,
                                weight=1.0,
                                high_relevance_patterns=optimized_rules["high_relevance_patterns"],
                                boundary_patterns=optimized_rules["boundary_patterns"],
                                low_relevance_patterns=optimized_rules["low_relevance_patterns"],
                                pubtype_patterns={}
                            )
                            rule_sets.append(rule_set)
                            print("✓ 已接受优化后的规则")
                            return rule_sets
                        else:
                            continue
                    except Exception as e:
                        print(f"[ERROR] 优化规则失败: {str(e)}")
                        continue
                else:
                    print("未输入修订意见，继续当前规则")
                    continue
                    
            elif choice == "4":
                print("\n使用预设规则")
                rule_sets = get_preset_rules(domain)
                return rule_sets
            else:
                print("无效选择，默认使用预设规则")
                rule_sets = get_preset_rules(domain)
                return rule_sets
        
        except Exception as e:
            print(f"\n[ERROR] 生成规则失败: {str(e)}")
            if retry_count < max_retries:
                retry = input(f"\n是否重试? ({retry_count+1}/{max_retries}): (y/n): ").strip().lower() == "y"
                if retry:
                    retry_count += 1
                    llm_config.timeout = int(llm_config.timeout * 1.5)
                    print(f"[INFO] 重试中，超时时间调整为 {llm_config.timeout} 秒")
                    continue
                else:
                    break
            
            print("将使用预设规则")
            rule_sets = get_preset_rules(domain)
            return rule_sets
    
    print("\n已达到最大重试次数，使用预设规则")
    rule_sets = get_preset_rules(domain)
    return rule_sets


def select_rule_mode():
    """选择规则模式"""
    print("\n" + "="*50)
    print("选择规则模式")
    print("="*50)
    print("\n规则模式决定了文献筛选的严格程度，影响筛选的精确率和召回率。")
    print("\n可用模式:")
    print("  1. 严格模式 (STRICT)")
    print("     - 高精确率 (≥95%)，适合需要高度相关文献的场景")
    print("  2. 中等模式 (MODERATE) [推荐]")
    print("     - 平衡精确率和召回率，适合大多数研究场景")
    print("  3. 宽松模式 (LOOSE)")
    print("     - 高召回率 (≥90%)，适合需要全面收集文献的场景")
    
    print("\n" + "-"*50)
    print(get_rule_mode_comparison())
    print("-"*50)
    
    while True:
        choice = input("\n请选择规则模式 (1-3, 默认: 2): ").strip()
        
        if choice == "1":
            print("\n✓ 已选择: 严格模式")
            return RuleMode.STRICT
        elif choice == "2" or choice == "":
            print("\n✓ 已选择: 中等模式 (推荐)")
            return RuleMode.MODERATE
        elif choice == "3":
            print("\n✓ 已选择: 宽松模式")
            return RuleMode.LOOSE
        else:
            print("[ERROR] 无效选择，请输入 1-3")


def configure_project_interactive():
    """交互式配置项目"""
    print("\n=== 配置研究主题和规则 ===")
    
    research_topic = input("请输入研究主题: ").strip()
    if not research_topic:
        research_topic = "未指定研究主题"
    
    domains = ["general", "medicine", "biology", "chemistry", "physics", "engineering", "social_science"]
    print("\n选择研究领域:")
    for i, domain in enumerate(domains, 1):
        print(f"{i}. {domain}")
    
    domain_choice = input("请选择 (1-7): ").strip()
    domain = domains[int(domain_choice)-1] if domain_choice.isdigit() and 1<=int(domain_choice)<=7 else "general"
    
    select_language()
    selected_rule_mode = select_rule_mode()
    
    use_llm = input("\n是否使用大模型辅助生成规则? (y/n): ").strip().lower() == "y"
    
    rule_sets = []
    
    if use_llm:
        saved_config = config_manager.load_llm_config()
        use_saved = False
        
        if saved_config:
            use_saved = input("\n检测到保存的大模型配置，是否使用? (y/n): ").strip().lower() == "y"
        
        if use_saved:
            print(f"\n使用保存的配置: {saved_config.provider} - {saved_config.model}")
            llm_config = saved_config
        else:
            llm_config = configure_llm_interactive("规则生成")
            
            save_config = input("\n是否保存大模型配置? (y/n): ").strip().lower() == "y"
            if save_config:
                config_manager.save_llm_config(llm_config)
                print("✓ 配置已保存")
        
        state.llm_config = llm_config
        rule_sets = generate_rules_with_interaction(
            research_topic, 
            domain, 
            llm_config, 
            state.language,
            selected_rule_mode
        )
    
    else:
        print("\n使用预设规则集")
        rule_sets = get_preset_rules(domain)
    
    state.project_config = ProjectConfig(
        research_topic=research_topic,
        domain=domain,
        rule_sets=rule_sets,
        rule_mode=selected_rule_mode
    )
    
    state.rule_mode = selected_rule_mode
    state.stage = "configured"
    
    print("\n" + "="*50)
    print("项目配置完成")
    print("="*50)
    print(f"研究主题: {research_topic}")
    print(f"研究领域: {domain}")
    print(f"规则模式: {get_rule_mode_description(selected_rule_mode, state.language)['name']}")
    print(f"文献语言: {'中文' if state.language == 'chinese' else '英文'}")
    print(f"规则数量: {len(rule_sets)} 组")
    
    return state.project_config


def run_complete_screening():
    """运行完整筛查流程"""
    if state.df is None:
        print("[ERROR] 请先加载文献数据")
        return
    
    if state.project_config is None:
        print("[ERROR] 请先配置研究主题和规则")
        return
    
    df = state.df.copy()
    
    # 阶段1：规则筛选
    print("\n" + "="*50)
    print("阶段1：规则筛选")
    print("="*50)
    
    current_rule_mode = getattr(state, 'rule_mode', 'moderate')
    print(f"当前规则模式: {current_rule_mode}")
    
    df = rule_based_screening(df, state.project_config.rule_sets)
    df = apply_rule_direct_judgment(
        df, 
        rule_mode=current_rule_mode,
        review_threshold=state.review_threshold
    )
    print_rule_statistics(df)
    
    rule_high_indices = df[df["rule_tier"] == "rule_high"].index.tolist()
    rule_boundary_indices = df[df["rule_tier"] == "rule_boundary"].index.tolist()
    rule_undecided_indices = df[df["rule_tier"] == "rule_unclear"].index.tolist()
    
    print(f"\n规则筛选结果:")
    print(f"  - 高相关文献: {len(rule_high_indices)} 条")
    print(f"  - 边界相关文献: {len(rule_boundary_indices)} 条")
    print(f"  - 待进一步筛选: {len(rule_undecided_indices)} 条")
    
    # 阶段2：TF-IDF相似度筛选
    print("\n" + "="*50)
    print("阶段2：TF-IDF相似度筛选")
    print("="*50)
    
    if rule_undecided_indices:
        seed_texts = [state.project_config.research_topic]
        df = tfidf_scoring(df, seed_texts)
        
        low_threshold = float(input("请输入低相关阈值 (默认: 0.02): ").strip() or "0.02")
        high_threshold = float(input("请输入高相关阈值 (默认: 0.3): ").strip() or "0.3")
        
        df = apply_tfidf_threshold(df, low_threshold, high_threshold)
        print_tfidf_statistics(df)
        
        tfidf_high_mask = (df["screening_method"] == "tfidf_threshold") & (df["screening_level"] == "高相关")
        tfidf_high_indices = df[tfidf_high_mask].index.tolist()
        rule_high_indices.extend(tfidf_high_indices)
        
        rule_undecided_indices = df[
            (df["screening_level"].isna() | (df["screening_level"] == "")) &
            (~df.index.isin(rule_boundary_indices))
        ].index.tolist()
        
        print(f"\nTF-IDF筛选结果:")
        print(f"  - 新增高相关: {len(tfidf_high_indices)} 条")
        print(f"  - 待进一步筛选: {len(rule_undecided_indices)} 条")
    else:
        print("所有文献已完成判定，跳过TF-IDF筛选")
    
    # 阶段3：Rank25筛选
    print("\n" + "="*50)
    print("阶段3：Rank25百分位筛选")
    print("="*50)
    
    if rule_undecided_indices:
        df = calculate_rank_score(df)
        percentile = float(input("请输入保留的百分位 (默认: 25.0): ").strip() or "25.0")
        df = rank25_filter(df, percentile)
        df = apply_rank_judgment(df)
        print_rank_statistics(df)
        
        rank25_high_mask = (df["screening_method"] == "rank25") & (df["screening_level"] == "高相关")
        rank25_high_indices = df[rank25_high_mask].index.tolist()
        rule_high_indices.extend(rank25_high_indices)
        
        rule_undecided_indices = df[
            (df["screening_level"].isna() | (df["screening_level"] == "")) &
            (~df.index.isin(rule_boundary_indices))
        ].index.tolist()
        
        print(f"\nRank25筛选结果:")
        print(f"  - 新增高相关: {len(rank25_high_indices)} 条")
        print(f"  - 待语义理解: {len(rule_undecided_indices)} 条")
    else:
        print("所有文献已完成判定，跳过Rank25筛选")
    
    # 语义理解（可选）
    print("\n" + "="*50)
    print("语义理解分析（双分支）- 可选步骤")
    print("="*50)
    print("\n[提示] 语义理解需要调用大模型API，会产生Token消耗")
    
    # 保存结果
    state.df = df.copy()
    state.candidate_pool = rule_high_indices
    state.boundary_pool = rule_boundary_indices
    state.stage = "completed"
    
    # 显示最终结果
    print("\n" + "="*50)
    print("筛查流程完成")
    print("="*50)
    
    total_high = len(df[df["screening_level"] == "高相关"])
    total_boundary = len(df[df["screening_level"] == "边界相关"])
    total_low = len(df[df["screening_level"] == "低相关"])
    total_undecided = len(df[df["screening_level"].isna() | (df["screening_level"] == "")])
    
    print(f"\n最终统计:")
    print(f"  - 高相关: {total_high} 条 ({total_high/len(df)*100:.1f}%)")
    print(f"  - 边界相关: {total_boundary} 条 ({total_boundary/len(df)*100:.1f}%)")
    print(f"  - 低相关: {total_low} 条 ({total_low/len(df)*100:.1f}%)")
    print(f"  - 未判定: {total_undecided} 条 ({total_undecided/len(df)*100:.1f}%)")


def run_rule_only_screening():
    """仅运行规则筛选"""
    if state.df is None:
        print("[ERROR] 请先加载文献数据")
        return
    
    if state.project_config is None:
        print("[ERROR] 请先配置研究主题和规则")
        return
    
    df = state.df.copy()
    
    print("\n" + "="*50)
    print("规则筛选")
    print("="*50)
    
    df = rule_based_screening(df, state.project_config.rule_sets)
    df = apply_rule_direct_judgment(df)
    print_rule_statistics(df)
    
    state.df = df
    state.stage = "rule_only"
    
    print("\n✓ 规则筛选完成")


def configure_semantic_llm():
    """配置语义理解专用模型"""
    print("\n=== 配置语义理解专用模型 ===")
    print("语义理解模型用于双分支深度分析")
    
    state.semantic_llm_config = configure_llm_interactive("语义理解")
    
    print("✓ 语义理解模型配置完成")
    return state.semantic_llm_config


def configure_human_review():
    """配置人工审查选项"""
    print("\n=== 配置人工审查选项 ===")
    print("Human-in-Loop模式将人工判断融入整个筛查流程")
    
    enable = input("是否启用人工审查? (y/n, 默认: y): ").strip().lower()
    state.enable_human_review = enable != "n"
    
    if state.enable_human_review:
        threshold = input(f"请输入置信度阈值 (默认: {state.review_threshold}): ").strip()
        state.review_threshold = float(threshold) if threshold else 0.7
        
        interval = input(f"请输入审查间隔 (每N条询问一次, 默认: {state.review_interval}): ").strip()
        state.review_interval = int(interval) if interval else 10
        
        print(f"\n✓ 人工审查已启用")
        print(f"  - 置信度阈值: {state.review_threshold}")
        print(f"  - 审查间隔: 每 {state.review_interval} 条")
    else:
        print("✓ 人工审查已禁用（全自动模式）")


def view_statistics():
    """查看筛选统计"""
    print("\n=== 筛选统计 ===")
    
    if state.df is None:
        print("[ERROR] 请先加载文献数据")
        return
    
    df = state.df
    
    print(f"\n总文献数: {len(df)}")
    
    level_counts = df["screening_level"].value_counts()
    print("\n筛选级别分布:")
    for level, count in level_counts.items():
        if level:
            percentage = count / len(df) * 100
            print(f"  {level}: {count} ({percentage:.1f}%)")
    
    undecided_count = len(df[df["screening_level"].isna() | (df["screening_level"] == "")])
    if undecided_count > 0:
        percentage = undecided_count / len(df) * 100
        print(f"  未判定: {undecided_count} ({percentage:.1f}%)")


def save_results_interactive():
    """交互式保存结果"""
    print("\n=== 保存筛选结果 ===")
    
    if state.df is None:
        print("[ERROR] 请先加载文献数据")
        return False
    
    df = state.df
    
    output_path = input("请输入输出文件路径 (支持 CSV, Excel, JSON): ").strip()
    output_path = clean_file_path(output_path)
    
    if not output_path:
        print("[ERROR] 输出路径不能为空")
        return False
    
    try:
        if output_path.endswith('.csv'):
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        elif output_path.endswith(('.xlsx', '.xls')):
            df.to_excel(output_path, index=False, engine='openpyxl')
        elif output_path.endswith('.json'):
            df.to_json(output_path, orient='records', force_ascii=False, indent=2)
        else:
            print("[ERROR] 不支持的文件格式，默认保存为CSV")
            output_path += '.csv'
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"✓ 成功保存结果到: {output_path}")
        return True
    except Exception as e:
        print(f"[ERROR] 保存结果失败: {str(e)}")
        return False


def load_data_interactive():
    """交互式加载数据"""
    print("\n=== 加载文献数据 ===")
    file_path = input("请输入文献文件路径 (支持 CSV, Excel, RIS, NBIB, JSON): ").strip()
    
    file_path = clean_file_path(file_path)
    
    if not os.path.exists(file_path):
        print(f"[ERROR] 文件不存在: {file_path}")
        return None
    
    try:
        df, log_df = load_records(file_path)
        print(f"✓ 成功加载 {len(df)} 条文献")
        print("  加载日志:")
        for _, row in log_df.iterrows():
            print(f"    - {row['source_file']}: {row['record_count']} 条记录, 格式: {row['detected_format']}")
        
        state.df = df
        state.stage = "loaded"
        return df
    except Exception as e:
        print(f"[ERROR] 加载文件失败: {str(e)}")
        return None


def main():
    """主程序入口"""
    print("欢迎使用通用文献筛查工作流!")
    print("\n本系统采用 Human-in-Loop 模式，支持双分支语义理解:")
    print("  分支1: 边界文献筛选 → 高相关候选集合")
    print("  分支2: 高相关文献深度分析 → 精准分类")
    
    while True:
        print_menu()
        choice = input("请选择操作 (1-9): ").strip()
        
        if choice == "1":
            load_data_interactive()
        elif choice == "2":
            configure_project_interactive()
        elif choice == "3":
            run_complete_screening()
        elif choice == "4":
            run_rule_only_screening()
        elif choice == "5":
            configure_semantic_llm()
        elif choice == "6":
            configure_human_review()
        elif choice == "7":
            view_statistics()
        elif choice == "8":
            save_results_interactive()
        elif choice == "9":
            print("\n感谢使用通用文献筛查工作流! 再见!")
            break
        else:
            print("[ERROR] 无效选择，请输入 1-9")


if __name__ == "__main__":
    main()
