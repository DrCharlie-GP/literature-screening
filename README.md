# 通用文献筛查工作流 (Literature Screening Workflow)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 基于 LLM 辅助的智能文献筛查工具，采用 Human-in-Loop 模式，支持多阶段筛选和双分支语义理解。

---

## 📋 项目简介

本项目是一个通用的文献筛查工作流系统，旨在帮助研究人员高效地从大量文献中筛选出与研究主题相关的文献。系统采用**多阶段筛选策略**，结合**规则匹配**、**TF-IDF相似度**、**Rank25百分位**和**LLM语义理解**等多种方法，实现精准而全面的文献筛选。

### 核心特性

- 🎯 **三种规则模式**：严格模式（高精准度）、中等模式（平衡）、宽松模式（高召回率）
- 🤖 **LLM 辅助规则生成**：自动根据研究主题生成筛选规则
- 👤 **Human-in-Loop**：人工判断贯穿整个流程，确保筛选质量
- 📊 **多阶段筛选**：规则筛选 → TF-IDF → Rank25 → 语义理解
- 🔄 **双分支语义分析**：
  - 分支1：边界文献筛选 → 高相关候选集合
  - 分支2：高相关文献深度分析 → 精准分类
- 📁 **多格式支持**：CSV, Excel, RIS, NBIB, JSON, TXT
- 🌐 **多模型支持**：OpenAI, DeepSeek, Kimi, Qwen, Claude 等

---

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- pip 包管理器

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/DrCharlie-GP/literature-screening.git
cd literature-screening
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **运行程序**

```bash
python main.py
```

---

## 📖 使用指南

### 1. 启动程序

运行 `main.py` 后，您将看到交互式主菜单：

```
==================================================
        通用文献筛查工作流
==================================================
1. 加载文献数据
2. 配置研究主题和规则
3. 运行完整筛查流程（含语义理解）
4. 仅运行规则筛选
5. 配置语义理解模型
6. 配置人工审查选项
7. 查看筛选统计
8. 保存筛选结果
9. 退出
==================================================
```

### 2. 加载文献数据

选择菜单项 **1**，然后输入文献文件路径。支持的格式包括：

- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)
- RIS (`.ris`)
- PubMed NBIB (`.nbib`)
- JSON (`.json`, `.jsonl`)
- 文本格式 (`.txt`)

### 3. 配置研究主题和规则

选择菜单项 **2**，按提示输入：

1. **研究主题**：例如"乳腺癌患者骨密度变化"
2. **研究领域**：选择医学、生物学、化学等领域
3. **文献语言**：中文或英文
4. **规则模式**：
   - **严格模式**：高精确率（≥95%），适合系统综述
   - **中等模式**（推荐）：平衡精准度和召回率
   - **宽松模式**：高召回率（≥90%），适合全面调研
5. **是否使用 LLM 生成规则**：推荐选择"是"

#### LLM 配置

如果选择使用 LLM，需要配置：
- **提供商**：OpenAI, DeepSeek, Kimi, Qwen, Claude 等
- **API Key**：从相应平台获取
- **模型名称**：如 `gpt-4`, `deepseek-chat` 等
- **超时时间**：默认 120 秒

### 4. 运行筛查流程

#### 选项 A：完整筛查流程（菜单项 3）

包含以下阶段：

1. **规则筛选**：基于生成的规则进行初步筛选
2. **TF-IDF 相似度筛选**：计算文献与研究主题的相似度
3. **Rank25 百分位筛选**：保留排名前 25% 的文献
4. **语义理解（可选）**：
   - 分支1：边界文献筛选
   - 分支2：高相关文献深度分析

#### 选项 B：仅规则筛选（菜单项 4）

快速进行基于规则的筛选，适合初步筛选。

### 5. 配置人工审查（可选）

选择菜单项 **6**，可以：
- 启用/禁用人工审查
- 设置置信度阈值（默认 0.7）
- 设置审查间隔

### 6. 保存结果

选择菜单项 **8**，输入输出文件路径。支持格式：
- CSV
- Excel
- JSON

---

## 🛠️ 高级功能

### 批量处理与断点续传

语义理解阶段支持：
- **批量处理**：每批次处理 5 篇文献
- **重试机制**：失败自动重试（最多 3 次）
- **断点续传**：中断后可从上次位置继续
- **性能监控**：显示处理速度和预估时间

### 规则模式对比

| 规则模式 | 精确率目标 | 召回率目标 | 适用场景 |
|---------|-----------|-----------|---------|
| 严格模式 | ≥95% | 60-70% | 系统综述、Meta分析 |
| 中等模式 | 80-90% | 75-85% | 一般文献综述（推荐） |
| 宽松模式 | 60-75% | ≥90% | 文献计量分析、全面调研 |

---

## 📁 项目结构

```
literature-screening/
├── main.py                    # 主程序入口
├── requirements.txt           # 依赖包列表
├── config/                    # 配置模块
│   ├── __init__.py
│   ├── schema.py             # 数据结构定义
│   ├── preset_rules.py       # 预设规则模板
│   └── rule_mode_templates.py # 规则模式模板
├── core/                      # 核心功能模块
│   ├── __init__.py
│   ├── config_manager.py     # 配置管理器
│   ├── data_loader.py        # 数据加载与解析
│   ├── rule_engine.py        # 规则筛选引擎
│   ├── tfidf_scorer.py       # TF-IDF相似度计算
│   ├── rank_filter.py        # Rank25百分位筛选
│   ├── llm_client.py         # LLM客户端
│   └── manual_review.py      # 人工审查模块
└── README.md                  # 项目说明文档
```

---

## ⚙️ 配置说明

### 环境变量（可选）

您可以通过环境变量设置默认的 LLM 配置：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

### 配置文件

程序会自动在 `.config` 目录下保存：
- `llm_config.json`：LLM 配置
- `project_config.json`：项目配置

---

## 🐛 常见问题

### Q1: API 调用超时怎么办？

A: 在配置 LLM 时增加超时时间，或检查网络连接。如果使用的是国内模型（如 DeepSeek、Kimi），通常响应更快。

### Q2: 如何处理大量文献？

A: 建议使用"仅规则筛选"模式先进行初步筛选，再对筛选后的文献进行语义理解分析。批量处理功能会自动处理，支持断点续传。

### Q3: 筛选结果不理想怎么办？

A: 可以尝试：
1. 调整规则模式（严格/中等/宽松）
2. 优化研究主题描述
3. 使用 LLM 优化现有规则
4. 启用人工审查模式进行精细调整

### Q4: 支持哪些文献数据库导出格式？

A: 支持 PubMed、Web of Science、EndNote、Zotero 等主流文献管理工具的导出格式。

---

## 📝 使用示例

### 示例：乳腺癌骨密度研究

1. **启动程序**：`python main.py`

2. **加载数据**：选择菜单 1，输入文献文件路径

3. **配置项目**：
   - 研究主题：`乳腺癌患者骨密度变化`
   - 研究领域：`medicine`
   - 文献语言：`中文`
   - 规则模式：`中等模式`
   - 使用 LLM：`是`

4. **运行完整筛查**：选择菜单 3

5. **查看统计**：选择菜单 7

6. **保存结果**：选择菜单 8，输出为 `results.xlsx`

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 提交 Issue

请描述：
- 问题现象
- 复现步骤
- 期望行为
- 环境信息（Python 版本、操作系统等）

### 代码贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 🙏 致谢

感谢以下开源项目的支持：
- [pandas](https://pandas.pydata.org/) - 数据处理
- [scikit-learn](https://scikit-learn.org/) - TF-IDF 计算
- [OpenAI](https://openai.com/) - LLM API

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 项目地址：https://github.com/DrCharlie-GP/literature-screening
- 提交 Issue：https://github.com/DrCharlie-GP/literature-screening/issues

---

**祝您科研顺利！** 🎓
