# AIproduce 开发指南

## 项目概述

AIproduce 是一个 AI 多智能体系统，用于将小说（40-100万字）改编为剧本（影视/短剧/漫剧）。

- **架构模式**: 星形集中调度（项目调度器为中心 Hub）
- **技术栈**: Python 3.11+ / LangGraph / LangChain / SQLAlchemy / ChromaDB
- **13个 Agent** 分 5 层协作，**21个工作流节点** 分 5 阶段执行

## 快速开始

### 环境准备

```bash
# 1. 克隆项目
cd AIproduce

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -e .

# 4. (可选) 安装开发依赖（测试 + Gradio Web UI）
pip install -e ".[dev]"

# 5. (可选) 设置 LLM API Key
# 不设置也能运行，系统会自动使用规则降级模式
set ANTHROPIC_API_KEY=sk-ant-xxx
```

### 快速验证

```bash
# 1. 初始化项目
aiproduce init --name "测试项目" --source tests/fixtures/sample_novel_chapter.md

# 2. 运行 Thin Slice（最小验证链路）
aiproduce run --thin-slice --project <PROJECT_ID>

# 3. 查看结果
aiproduce status --project <PROJECT_ID>
aiproduce report --project <PROJECT_ID>

# 4. (可选) 启动 Web UI 查看结果
aiproduce web
```

### 使用向导快速开始

```bash
# 交互式配置向导（推荐新手使用）
aiproduce wizard
```

## 项目结构

```
AIproduce/
├── Readme.md                        # 方案设计文档
├── DEVELOPMENT.md                   # 开发指南（本文件）
├── pyproject.toml                   # 项目依赖 & 配置
├── config/
│   ├── project.yaml                 # 项目配置模板
│   ├── agents.yaml                  # 13个Agent注册信息
│   ├── workflow.yaml                # 21节点工作流定义
│   └── prompts/                     # 13个 Prompt 模板 (.md)
├── src/
│   ├── models/                      # Pydantic 数据模型
│   │   ├── project.py               #   ProjectConfig
│   │   ├── asset.py                 #   AssetLibrary (人物/世界观/时间线)
│   │   ├── chunk.py                 #   SemanticChunk 系列
│   │   ├── outline.py               #   EpisodeOutline / SceneCard
│   │   └── script.py                #   SceneScript / EpisodeScript
│   ├── db/                          # SQLite 持久化层
│   │   ├── engine.py                #   DatabaseEngine 单例
│   │   ├── models.py                #   8张 ORM 表
│   │   └── repository.py            #   Repository 模式 CRUD
│   ├── store/
│   │   └── chroma_store.py          # ChromaDB 向量存储封装
│   ├── agents/                      # 13个Agent实现
│   │   ├── base.py                  #   AgentBase 基类
│   │   ├── scheduler.py             #   N01/N15/N16/N21 调度
│   │   ├── deconstructor.py         #   N02 原著解构
│   │   ├── character_asset.py       #   N03 人设资产管理
│   │   ├── world_asset.py           #   N03 世界观管理
│   │   ├── timeline_asset.py        #   N03 时间线管理
│   │   ├── adaptation_planner.py    #   N04 改编策划总纲
│   │   ├── episode_outliner.py      #   N07 分集大纲
│   │   ├── scene_splitter.py        #   N09 场次拆分
│   │   ├── scene_writer.py          #   N11 单场剧本
│   │   ├── character_checker.py     #   N12 人设校验
│   │   ├── timeline_checker.py      #   N13 时间线校验
│   │   ├── format_checker.py        #   N14 格式校验
│   │   └── final_polisher.py        #   N17/N19 全局统稿
│   ├── workflow/
│   │   ├── state.py                 #   WorkflowState 状态定义
│   │   ├── edges.py                 #   条件路由/准入准出
│   │   └── runner.py               #   WorkflowRunner 流程编排
│   ├── cli/
│   │   ├── main.py                  #   Click CLI 入口
│   │   └── commands.py              #   命令实现
│   ├── web/
│   │   └── app.py                   #   Gradio Web UI
│   └── utils/
│       ├── logger.py                #   结构化日志
│       ├── token_counter.py         #   Token 成本统计
│       └── text_utils.py            #   文本处理工具
├── tests/
│   ├── test_deconstructor.py        # N02 单元测试
│   ├── test_scene_writer.py         # N11 单元测试
│   └── fixtures/                    # 测试小说
│       ├── sample_novel.md          #   极小型测试 (455字)
│       ├── sample_novel_chapter.md  #   古装仙侠 (1994字)
│       ├── sample_novel_modern.md   #   现代悬疑 (2200字)
│       └── sample_novel_fantasy.md  #   科幻奇幻 (2300字)
└── workspace/                       # 运行时工作区 (gitignore)
    └── projects/{project_id}/
        ├── db.sqlite                #   项目数据库
        ├── project.yaml             #   项目配置
        ├── chroma/                  #   向量索引
        ├── assets/                  #   资产库 JSON
        └── work/                    #   过程产出物
            ├── deconstruction/
            ├── planning/
            ├── outlines/
            ├── scenes/
            ├── drafts/
            ├── validation/
            ├── polish/
            └── token_usage.jsonl
```

## 核心设计

### Agent 基类

所有 Agent 继承 `AgentBase`，提供：

| 能力 | 说明 |
|------|------|
| `call_llm(user_input, system_prompt, output_schema)` | 统一 LLM 调用接口 |
| `_call_via_langchain()` | LangChain 后端 |
| `_call_via_anthropic()` | 原生 Anthropic SDK 后端（降级） |
| `_render_prompt(template, **vars)` | `{{variable}}` 模板渲染 |
| `_validate_json(response, schema)` | 结构化输出校验 |
| 自动重试 | 最多 3 次，指数退避 |

**LLM + 降级双模式**：所有 Agent 在无 API Key 时自动切换到规则模式，管道永不中断。

### 双存储架构

| 存储 | 用途 | 技术 |
|------|------|------|
| SQLite | 结构化数据（人物/世界观/时间线/大纲/剧本） | SQLAlchemy ORM |
| ChromaDB | 原文语义检索（向量索引） | ChromaDB PersistentClient |

### 校验分级

三级校验标准（N12/N13/N14）：

| 级别 | 含义 | 行为 |
|------|------|------|
| Blocking | 硬伤，必须修复 | 打回重写（最多 3 次） |
| Warning | 需要关注 | 记录但继续流程 |
| Suggestion | 优化建议 | 人工审核时参考 |

## 工作流节点

### Thin Slice（最小验证链路）

```
N01 → N02 → N03 → N04 → N07 → N09 → N11 → N12 → N13 → N14
 初始化  解构  资产库  策划   大纲   场次   剧本   人设   时间线  格式
```

### 完整 21 节点

```
阶段1 (初始化+解构):  N01 → N02 → N03
阶段2 (改编设计):     N04 → N05 → N06 → N07 → N08
阶段3 (分集结构):     N09 → N10
阶段4 (逐场剧本):     N11 → N12 → N13 → N14 → N15 → N16
阶段5 (全局打磨):     N17 → N18 → N19 → N20 → N21
```

## 如何添加新 Agent

### 1. 创建 Prompt 模板

在 `config/prompts/` 下创建 `.md` 文件，使用 `{{variable}}` 标记模板变量。

### 2. 实现 Agent 类

```python
# src/agents/my_agent.py
from src.agents.base import AgentBase
from src.utils.logger import node_logger

class MyAgent(AgentBase):
    node_id = "N99"
    node_name = "我的Agent"

    def __init__(self, model_name="claude-sonnet-5"):
        super().__init__(model_name=model_name, temperature=0.5)
        self._load_prompt()

    def _load_prompt(self):
        prompt_path = Path("config/prompts/99_my_agent.md")
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")

    def execute(self, project_id: str, **kwargs) -> dict:
        with node_logger.node_context(self.node_id, self.node_name) as log:
            # 1. 加载上游数据
            # 2. LLM 处理（或降级规则处理）
            # 3. 保存产出物
            # 4. 返回结果
            return {"verdict": "PASS", "...": "..."}
```

### 3. 注册到工作流

1. `config/agents.yaml` — 添加 Agent 元信息
2. `config/workflow.yaml` — 添加节点定义与准入条件
3. `src/agents/__init__.py` — 导出类
4. `src/workflow/runner.py` — 编排到流程中

### 4. 编写测试

```python
# tests/test_my_agent.py
def test_my_agent():
    agent = MyAgent()
    result = agent.execute(project_id="test", ...)
    assert result["verdict"] == "PASS"
```

## 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_deconstructor.py -v

# 带覆盖率
pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html
```

## 双模式说明

### LLM 模式（有 API Key）

- 设置 `ANTHROPIC_API_KEY` 环境变量
- 所有 Agent 调用 Claude API 执行
- 解构质量、剧本质量显著高于规则模式
- 成本: Thin Slice 约 $0.5-2（取决于小说长度）

### 降级模式（无 API Key）

- 无需任何配置，开箱即用
- Agent 使用规则匹配和模板填充
- 适合原型验证、单元测试、CI/CD
- 人物提取有噪声（规则版 NER 不如 LLM 准确）

## 常见问题

### Q: ChromaDB 首次运行很慢？

ChromaDB 首次使用会下载 ONNX embedding 模型（~79MB），仅需一次。之后运行秒级完成。

### Q: 如何切换 LLM 模型？

在 CLI 或配置中指定 `--model` 参数，或在 `config/project.yaml` 中修改 `model.name`。

支持的模型：
- `claude-sonnet-5` (默认，性价比最优)
- `claude-opus-5` (最强质量，成本高)
- `claude-haiku-4-5` (最快最省，适合简单任务)
- `gpt-4o` (OpenAI 备选)

### Q: 如何部署到服务器？

```bash
# 1. 安装依赖
pip install -e ".[dev]"

# 2. 设置 API Key
export ANTHROPIC_API_KEY=sk-ant-xxx

# 3. 启动 Web 服务
aiproduce web --port 7860

# 4. (可选) 生成公网链接
aiproduce web --share
```

### Q: 工作流中断后如何恢复？

项目状态保存在 `workspace/projects/{project_id}/` 中。使用 `aiproduce status --project <ID>` 查看进度，使用 `aiproduce run --thin-slice --project <ID>` 继续运行——已完成节点会自动跳过。

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1.0 | 2026-07 | 初始原型：10/13 Agent、Thin Slice 完整链路、3 题材测试小说 |
