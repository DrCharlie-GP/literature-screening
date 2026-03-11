# -*- coding: utf-8 -*-
"""
大模型客户端模块
用于辅助生成筛选规则
支持三种规则模式：严格、中等、宽松
"""

import json
import time
from typing import List, Dict, Any, Optional

from config import LLMConfig, RuleMode


class LLMClientError(Exception):
    """LLM客户端异常"""
    pass


# 定义语言特定的提示词模板
PROMPT_TEMPLATES = {
    "chinese": {
        "system": "你是一位专业的文献筛查规则生成专家。",
        "generate": {
            RuleMode.STRICT: r"""你是一位专业的医学文献筛查专家，请根据研究主题生成**严格模式**的文献筛选规则。

研究主题：{research_topic}
研究领域：{domain}
文献语言：中文
规则模式：**严格模式**（高精准度，目标精确率≥95%）

请生成三类规则模式，所有规则必须使用中文：

**严格模式要求**：
- 高相关规则：使用3-4个条件的"与"组合（用"+"连接），确保极高精准度
- 边界规则：使用2-3个条件的"与"组合
- 低相关规则：使用1-2个条件的"与"组合，严格排除

请生成：
1. high_relevance_patterns：高相关规则（至少8个，使用3-4个条件的"与"组合）
2. boundary_patterns：边界规则（至少5个，使用2-3个条件的"与"组合）
3. low_relevance_patterns：低相关规则（至少5个，使用1-2个条件的"与"组合）

重要要求：
- 所有规则必须使用中文或英文正则表达式
- 使用"+"表示"与"关系（如"条件1+条件2+条件3"）
- 规则条目之间为"或"关系
- 单条规则内部的条件为"与"关系
- 使用专业的医学术语

示例输出格式：
{{
  "high_relevance_patterns": [
    "骨量丢失+年变化率+队列研究",
    "骨密度+下降速率+纵向研究"
  ],
  "boundary_patterns": [
    "骨量丢失+年变化率",
    "骨密度+下降速率"
  ],
  "low_relevance_patterns": [
    "骨量+动物实验",
    "骨密度+体外研究"
  ]
}}

请严格按照JSON格式输出，不要添加任何额外内容。""",
            RuleMode.MODERATE: r"""你是一位专业的医学文献筛查专家，请根据研究主题生成**中等模式**的文献筛选规则。

研究主题：{research_topic}
研究领域：{domain}
文献语言：中文
规则模式：**中等模式**（平衡精准度和召回率）

请生成三类规则模式，所有规则必须使用中文：

**中等模式要求**：
- 高相关规则：使用2-3个条件的"与"组合（用"+"连接）
- 边界规则：使用1-2个条件的"与"组合或单条件
- 低相关规则：使用单条件或简单组合

请生成：
1. high_relevance_patterns：高相关规则（至少10个，使用2-3个条件的"与"组合）
2. boundary_patterns：边界规则（至少8个，使用1-2个条件的"与"组合或单条件）
3. low_relevance_patterns：低相关规则（至少8个，使用单条件或简单组合）

示例输出格式：
{{
  "high_relevance_patterns": [
    "骨量丢失+年变化率",
    "骨密度+下降速率"
  ],
  "boundary_patterns": [
    "骨量丢失",
    "骨密度变化"
  ],
  "low_relevance_patterns": [
    "病例报告",
    "信件"
  ]
}}

请严格按照JSON格式输出，不要添加任何额外内容。""",
            RuleMode.LOOSE: r"""你是一位专业的医学文献筛查专家，请根据研究主题生成**宽松模式**的文献筛选规则。

研究主题：{research_topic}
研究领域：{domain}
文献语言：中文
规则模式：**宽松模式**（高召回率，尽可能捕获所有潜在相关文献）

请生成三类规则模式，所有规则必须使用中文：

**宽松模式要求**：
- 高相关规则：使用1-2个条件的"与"组合或单条件
- 边界规则：主要使用单条件
- 低相关规则：仅排除明显无关的类型

请生成：
1. high_relevance_patterns：高相关规则（至少12个，使用1-2个条件的"与"组合或单条件）
2. boundary_patterns：边界规则（至少10个，主要使用单条件）
3. low_relevance_patterns：低相关规则（至少5个，仅排除明显无关类型）

示例输出格式：
{{
  "high_relevance_patterns": [
    "骨量丢失",
    "骨密度",
    "骨量"
  ],
  "boundary_patterns": [
    "骨质疏松",
    "骨骼健康"
  ],
  "low_relevance_patterns": [
    "病例报告",
    "信件"
  ]
}}

请严格按照JSON格式输出，不要添加任何额外内容。"""
        },
        "refine": r"""你是一位文献筛查专家，请根据用户反馈优化现有规则。

现有规则：
{existing_rules}

用户反馈：{feedback}

优化要求：
- 保持所有规则使用中文
- 根据反馈调整规则内容
- 保持相同的JSON格式
- 保持"+"表示"与"关系的用法

请返回优化后的规则，严格按照JSON格式输出。"""
    },
    "english": {
        "system": "You are a professional literature screening rule generation expert.",
        "generate": {
            RuleMode.STRICT: r"""You are a professional medical literature screening expert. Please generate **STRICT MODE** literature screening rules based on the research topic.

Research Topic: {research_topic}
Research Domain: {domain}
Literature Language: English
Rule Mode: **STRICT** (High precision, target ≥95% precision)

Please generate three categories of rule patterns, all rules must be in English:

**Strict Mode Requirements**:
- High relevance rules: Use 3-4 condition "AND" combinations (connected with "+")
- Boundary rules: Use 2-3 condition "AND" combinations
- Low relevance rules: Use 1-2 condition "AND" combinations

Please generate:
1. high_relevance_patterns: High relevance rules (at least 8, use 3-4 condition "AND" combinations)
2. boundary_patterns: Boundary rules (at least 5, use 2-3 condition "AND" combinations)
3. low_relevance_patterns: Low relevance rules (at least 5, use 1-2 condition "AND" combinations)

Example Output Format:
{{
  "high_relevance_patterns": [
    "bone loss+rate+cohort study",
    "bone density+decline+longitudinal"
  ],
  "boundary_patterns": [
    "bone loss+rate",
    "bone density+decline"
  ],
  "low_relevance_patterns": [
    "bone loss+animal",
    "bone density+in vitro"
  ]
}}

Please strictly follow JSON format output, do not add any extra content.""",
            RuleMode.MODERATE: r"""You are a professional medical literature screening expert. Please generate **MODERATE MODE** literature screening rules based on the research topic.

Research Topic: {research_topic}
Research Domain: {domain}
Literature Language: English
Rule Mode: **MODERATE** (Balance precision and recall)

Please generate three categories of rule patterns, all rules must be in English:

**Moderate Mode Requirements**:
- High relevance rules: Use 2-3 condition "AND" combinations (connected with "+")
- Boundary rules: Use 1-2 condition "AND" combinations or single conditions
- Low relevance rules: Use single conditions or simple combinations

Please generate:
1. high_relevance_patterns: High relevance rules (at least 10, use 2-3 condition "AND" combinations)
2. boundary_patterns: Boundary rules (at least 8, use 1-2 condition "AND" combinations or single conditions)
3. low_relevance_patterns: Low relevance rules (at least 8, use single conditions or simple combinations)

Example Output Format:
{{
  "high_relevance_patterns": [
    "bone loss+rate",
    "bone density+decline"
  ],
  "boundary_patterns": [
    "bone loss",
    "bone density change"
  ],
  "low_relevance_patterns": [
    "case report",
    "letter"
  ]
}}

Please strictly follow JSON format output, do not add any extra content.""",
            RuleMode.LOOSE: r"""You are a professional medical literature screening expert. Please generate **LOOSE MODE** literature screening rules based on the research topic.

Research Topic: {research_topic}
Research Domain: {domain}
Literature Language: English
Rule Mode: **LOOSE** (High recall, capture all potentially relevant literature)

Please generate three categories of rule patterns, all rules must be in English:

**Loose Mode Requirements**:
- High relevance rules: Use 1-2 condition "AND" combinations or single conditions
- Boundary rules: Mainly use single conditions
- Low relevance rules: Only exclude obviously irrelevant types

Please generate:
1. high_relevance_patterns: High relevance rules (at least 12, use 1-2 condition "AND" combinations or single conditions)
2. boundary_patterns: Boundary rules (at least 10, mainly use single conditions)
3. low_relevance_patterns: Low relevance rules (at least 5, only exclude obviously irrelevant types)

Example Output Format:
{{
  "high_relevance_patterns": [
    "bone loss",
    "bone density",
    "bone mass"
  ],
  "boundary_patterns": [
    "osteoporosis",
    "bone health"
  ],
  "low_relevance_patterns": [
    "case report",
    "letter"
  ]
}}

Please strictly follow JSON format output, do not add any extra content."""
        },
        "refine": r"""You are a professional medical literature screening expert. Please optimize existing rules based on user feedback.

Existing Rules:
{existing_rules}

User Feedback:
{feedback}

Optimization Requirements:
- Keep all rules in English
- Adjust rule content based on feedback
- Maintain the same JSON format
- Keep using "+" to represent "AND" relationship

Please return optimized rules, strictly follow JSON format output."""
    }
}


class LLMClient:
    """
    大模型客户端基类
    支持不同大模型API的统一接口
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.timeout = config.timeout
    
    def generate_rule_suggestions(
        self,
        research_topic: str,
        sample_documents: List[str] = None,
        domain: str = "general",
        language: str = "chinese",
        rule_mode: RuleMode = RuleMode.MODERATE
    ) -> Dict[str, List[str]]:
        raise NotImplementedError("子类必须实现此方法")
    
    def refine_rules(
        self,
        existing_rules: Dict[str, List[str]],
        feedback: str,
        language: str = "chinese"
    ) -> Dict[str, List[str]]:
        raise NotImplementedError("子类必须实现此方法")
    
    def analyze_document(
        self,
        title: str,
        abstract: str,
        research_topic: str,
        language: str = "chinese"
    ) -> Dict[str, Any]:
        raise NotImplementedError("子类必须实现此方法")
    
    def classify_boundary_document(
        self,
        title: str,
        abstract: str,
        research_topic: str,
        language: str = "chinese"
    ) -> Dict[str, Any]:
        raise NotImplementedError("子类必须实现此方法")
    
    def analyze_documents_batch(
        self,
        documents: List[Dict[str, str]],
        research_topic: str,
        language: str = "chinese",
        analysis_type: str = "classify"
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("子类必须实现此方法")


class OpenAIClient(LLMClient):
    """OpenAI API客户端"""
    
    def _print_loading(self):
        print(f"\r正在调用 {self.config.provider} API... 处理中", end="", flush=True)
        for char in "|/-.":
            print(f"\r正在调用 {self.config.provider} API... {char}", end="", flush=True)
            time.sleep(0.5)
    
    def generate_rule_suggestions(
        self,
        research_topic: str,
        sample_documents: List[str] = None,
        domain: str = "general",
        language: str = "chinese",
        rule_mode: RuleMode = RuleMode.MODERATE
    ) -> Dict[str, List[str]]:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai 库未安装，请通过 pip install openai 安装")
        
        base_url = self.base_url
        if not base_url:
            provider = self.config.provider.lower()
            if provider in ["deepseek", "deepseek-ai"]:
                base_url = "https://api.deepseek.com"
            elif provider in ["kimi", "moonshot", "moonshot-ai"]:
                base_url = "https://api.moonshot.cn/v1"
            elif provider in ["qwen", "ali", "alibabacloud"]:
                base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            elif provider in ["openai", "gpt", "chatgpt"]:
                base_url = "https://api.openai.com/v1"
        
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=base_url if base_url else None,
            timeout=self.config.timeout
        )
        
        lang = language if language in PROMPT_TEMPLATES else "chinese"
        template = PROMPT_TEMPLATES[lang]
        
        if isinstance(template["generate"], dict):
            mode_prompt = template["generate"].get(rule_mode, template["generate"][RuleMode.MODERATE])
        else:
            mode_prompt = template["generate"]
        
        prompt = mode_prompt.format(
            research_topic=research_topic,
            domain=domain
        )
        
        if sample_documents:
            sample_text = "\n\n示例文献：\n" + "\n".join([f"- {doc}" for doc in sample_documents[:3]])
            prompt += sample_text
        
        try:
            self._print_loading()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": template["system"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            detailed_error = f"""
========================================
API调用失败详细信息
========================================
错误类型: {error_type}
错误信息: {error_msg}
API提供商: {self.config.provider}
API基础URL: {base_url}
模型名称: {self.model}
========================================
"""
            raise LLMClientError(detailed_error)
    
    def refine_rules(
        self,
        existing_rules: Dict[str, List[str]],
        feedback: str,
        language: str = "chinese"
    ) -> Dict[str, List[str]]:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai 库未安装，请通过 pip install openai 安装")
        
        base_url = self.base_url or "https://api.openai.com/v1"
        
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=self.config.timeout
        )
        
        lang = language if language in PROMPT_TEMPLATES else "chinese"
        template = PROMPT_TEMPLATES[lang]
        
        prompt = template["refine"].format(
            existing_rules=json.dumps(existing_rules, ensure_ascii=False, indent=2),
            feedback=feedback
        )
        
        try:
            self._print_loading()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": template["system"]},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        
        except Exception as e:
            raise LLMClientError(f"优化规则失败: {str(e)}")
    
    def analyze_document(
        self,
        title: str,
        abstract: str,
        research_topic: str,
        language: str = "chinese"
    ) -> Dict[str, Any]:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai 库未安装")
        
        base_url = self.base_url or "https://api.openai.com/v1"
        client = openai.OpenAI(api_key=self.api_key, base_url=base_url, timeout=self.config.timeout)
        
        if language == "english":
            system_prompt = "You are a professional literature analysis expert."
            user_prompt = f"""Analyze the following literature:
Research Topic: {research_topic}
Title: {title}
Abstract: {abstract[:1000]}

Return JSON format:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "Core content summary...",
  "relevance_score": 0.85,
  "document_type": "Original Research/Review/Meta-analysis/Other"
}}"""
        else:
            system_prompt = "你是一位专业的文献分析专家。"
            user_prompt = f"""分析以下文献：
研究主题：{research_topic}
标题：{title}
摘要：{abstract[:1000]}

返回JSON格式：
{{
  "tags": ["标签1", "标签2", "标签3"],
  "summary": "核心内容摘要...",
  "relevance_score": 0.85,
  "document_type": "原始研究/综述/Meta分析/其他"
}}"""
        
        try:
            self._print_loading()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return {
                "tags": result.get("tags", []),
                "summary": result.get("summary", ""),
                "relevance_score": result.get("relevance_score", 0.0),
                "document_type": result.get("document_type", "未知")
            }
        
        except Exception as e:
            raise LLMClientError(f"文献分析失败: {str(e)}")
    
    def classify_boundary_document(
        self,
        title: str,
        abstract: str,
        research_topic: str,
        language: str = "chinese"
    ) -> Dict[str, Any]:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai 库未安装")
        
        base_url = self.base_url or "https://api.openai.com/v1"
        client = openai.OpenAI(api_key=self.api_key, base_url=base_url, timeout=self.config.timeout)
        
        if language == "english":
            system_prompt = "You are a professional literature screening expert."
            user_prompt = f"""Classify the following document:
Research Topic: {research_topic}
Title: {title}
Abstract: {abstract[:800]}

Classify into: "high", "boundary", or "low"

Return JSON format:
{{
  "judgment": "high/boundary/low",
  "confidence": 0.85,
  "reason": "Explanation"
}}"""
        else:
            system_prompt = "你是一位专业的文献筛查专家。"
            user_prompt = f"""分类以下文献：
研究主题：{research_topic}
标题：{title}
摘要：{abstract[:800]}

分类为："high"（高相关）、"boundary"（边界相关）或 "low"（低相关）

返回JSON格式：
{{
  "judgment": "high/boundary/low",
  "confidence": 0.85,
  "reason": "分类解释"
}}"""
        
        try:
            self._print_loading()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            judgment_map = {
                "high": "高相关",
                "boundary": "边界相关",
                "low": "低相关"
            }
            
            judgment = result.get("judgment", "boundary").lower()
            
            return {
                "judgment": judgment_map.get(judgment, "边界相关"),
                "confidence": result.get("confidence", 0.5),
                "reason": result.get("reason", "")
            }
        
        except Exception as e:
            raise LLMClientError(f"边界文献分类失败: {str(e)}")
    
    def analyze_documents_batch(
        self,
        documents: List[Dict[str, str]],
        research_topic: str,
        language: str = "chinese",
        analysis_type: str = "classify"
    ) -> List[Dict[str, Any]]:
        try:
            import openai
        except ImportError:
            raise LLMClientError("openai 库未安装")
        
        base_url = self.base_url or "https://api.openai.com/v1"
        client = openai.OpenAI(api_key=self.api_key, base_url=base_url, timeout=self.config.timeout)
        
        batch_content = ""
        for i, doc in enumerate(documents, 1):
            title = doc.get("title", "")
            abstract = doc.get("abstract", "")[:600]
            batch_content += f"\n--- 文献 {i} ---\n标题: {title}\n摘要: {abstract}\n"
        
        if language == "english":
            system_prompt = "You are a professional literature screening expert."
            user_prompt = f"""Classify the following {len(documents)} documents:
Research Topic: {research_topic}
{batch_content}

Return JSON array format:
[
  {{
    "judgment": "high/boundary/low",
    "confidence": 0.85,
    "reason": "Explanation"
  }},
  ...
]"""
        else:
            system_prompt = "你是一位专业的文献筛查专家。"
            user_prompt = f"""分类以下 {len(documents)} 篇文献：
研究主题：{research_topic}
{batch_content}

返回JSON数组格式：
[
  {{
    "judgment": "high/boundary/low",
    "confidence": 0.85,
    "reason": "分类解释"
  }},
  ...
]"""
        
        try:
            self._print_loading()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens * 2,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            if isinstance(result, dict):
                for key in ["results", "documents", "data", "items"]:
                    if key in result and isinstance(result[key], list):
                        result = result[key]
                        break
                else:
                    result = [result]
            
            if len(result) != len(documents):
                while len(result) < len(documents):
                    result.append({"judgment": "boundary", "confidence": 0.5, "reason": "结果补齐"})
                result = result[:len(documents)]
            
            return result
        
        except Exception as e:
            raise LLMClientError(f"批量文献分析失败: {str(e)}")


class MockLLMClient(LLMClient):
    """模拟LLM客户端，用于测试"""
    
    def generate_rule_suggestions(
        self,
        research_topic: str,
        sample_documents: List[str] = None,
        domain: str = "general",
        language: str = "chinese",
        rule_mode: RuleMode = RuleMode.MODERATE
    ) -> Dict[str, List[str]]:
        print(f"[MOCK LLM] 生成规则建议，主题：{research_topic}")
        
        for i in range(3):
            print(f"\r正在生成规则建议... {i+1}", end="", flush=True)
            time.sleep(0.5)
        print("\r生成完成！          ")
        
        if language == "english":
            return {
                "high_relevance_patterns": [
                    "bone loss+rate",
                    "bone density+decline",
                    "BMD+change"
                ],
                "boundary_patterns": [
                    "bone loss",
                    "bone density"
                ],
                "low_relevance_patterns": [
                    "case report",
                    "letter"
                ]
            }
        else:
            return {
                "high_relevance_patterns": [
                    "骨量丢失+年变化率",
                    "骨密度+下降速率",
                    "骨量+减少"
                ],
                "boundary_patterns": [
                    "骨量丢失",
                    "骨密度"
                ],
                "low_relevance_patterns": [
                    "病例报告",
                    "信件"
                ]
            }
    
    def refine_rules(
        self,
        existing_rules: Dict[str, List[str]],
        feedback: str,
        language: str = "chinese"
    ) -> Dict[str, List[str]]:
        print(f"[MOCK LLM] 优化规则，反馈：{feedback}")
        for i in range(2, 0, -1):
            print(f"\r正在优化规则... {i}秒", end="", flush=True)
            time.sleep(1)
        print("\r优化完成！          ")
        return existing_rules
    
    def analyze_document(
        self,
        title: str,
        abstract: str,
        research_topic: str,
        language: str = "chinese"
    ) -> Dict[str, Any]:
        print(f"[MOCK LLM] 分析文献: {title[:50]}...")
        for i in range(2, 0, -1):
            print(f"\r正在分析文献内容... {i}秒", end="", flush=True)
            time.sleep(0.5)
        print("\r分析完成！          ")
        
        if language == "english":
            return {
                "tags": ["bone density", "cohort study", "longitudinal analysis"],
                "summary": f"A cohort study analyzing bone density changes related to {research_topic}.",
                "relevance_score": 0.88,
                "document_type": "Original Research"
            }
        else:
            return {
                "tags": ["骨密度", "队列研究", "纵向分析"],
                "summary": f"一项关于{research_topic}的队列研究，分析了骨密度的变化情况。",
                "relevance_score": 0.88,
                "document_type": "原始研究"
            }
    
    def classify_boundary_document(
        self,
        title: str,
        abstract: str,
        research_topic: str,
        language: str = "chinese"
    ) -> Dict[str, Any]:
        print(f"[MOCK LLM] 分类边界文献: {title[:50]}...")
        for i in range(2, 0, -1):
            print(f"\r正在评估文献相关性... {i}秒", end="", flush=True)
            time.sleep(0.5)
        print("\r评估完成！          ")
        
        if language == "english":
            return {
                "judgment": "high",
                "confidence": 0.85,
                "reason": "This study is directly related to the research topic."
            }
        else:
            return {
                "judgment": "高相关",
                "confidence": 0.85,
                "reason": "该研究与研究主题直接相关"
            }
    
    def analyze_documents_batch(
        self,
        documents: List[Dict[str, str]],
        research_topic: str,
        language: str = "chinese",
        analysis_type: str = "classify"
    ) -> List[Dict[str, Any]]:
        print(f"[MOCK LLM] 批量分析 {len(documents)} 篇文献")
        for i in range(2, 0, -1):
            print(f"\r正在批量分析文献... {i}秒", end="", flush=True)
            time.sleep(0.5)
        print("\r分析完成！          ")
        
        results = []
        for doc in documents:
            if language == "english":
                results.append({
                    "judgment": "high",
                    "confidence": 0.85,
                    "reason": "Related to research topic"
                })
            else:
                results.append({
                    "judgment": "高相关",
                    "confidence": 0.85,
                    "reason": "与研究主题相关"
                })
        
        return results


def get_llm_client(config: LLMConfig) -> LLMClient:
    """获取LLM客户端实例"""
    provider = config.provider.lower()
    
    if provider in ["openai", "gpt", "chatgpt", "deepseek", "kimi", "moonshot", "qwen", "ali", "claude", "anthropic"]:
        return OpenAIClient(config)
    elif provider == "mock":
        return MockLLMClient(config)
    else:
        print(f"[WARN] 不支持的LLM提供商：{provider}，使用模拟客户端")
        return MockLLMClient(config)
