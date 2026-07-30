# AIproduce 开发指南

## 项目概述

AIproduce 是一个 AI 多智能体系统，用于将小说（40-100万字）改编为剧本（影视/短剧/漫剧）。

- **架构模式**: 星形集中调度（项目调度器为中心 Hub）
- **技术栈**: Python 3.11+ / LangGraph / LangChain / SQLAlchemy / ChromaDB
- **13个 Agent** 分 5 层协作，**21个工作流节点** 分 5 阶段执行

---

## 快速开始

### 方式一：Docker（推荐，无需装 Python）

```bash
# 1. 配置 API Key
cp .env.example .env
nano .env   # 填入 DEEPSEEK_API_KEY 或 ANTHROPIC_API_KEY

# 2. 构建并启动
docker build -t aiproduce .
docker run -p 7860:7860 -v aiproduce_workspace:/app/workspace -v $(pwd)/.env:/app/.env:ro aiproduce

# 3. 浏览器打开 http://localhost:7860
```

### 方式二：本地 Python 环境

```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置 API Key（可选，不配则使用规则降级模式）
cp .env.example .env
nano .env   # 填入 Key

# 4. 快速验证
aiproduce wizard
# 或直接跑
aiproduce run --thin-slice --novel tests/fixtures/sample_novel_chapter.md --name "测试"
```

### 不配 API Key 也能跑

系统有完整的规则降级模式，无需任何 Key 即可跑通全流程——剧本质量不如接 LLM 时好，但适合原型验证。

---

## 配置 LLM

### .env 文件（推荐）

复制 `.env.example` → `.env`，填入对应 Key：

```bash
# DeepSeek 系列
DEEPSEEK_API_KEY=sk-你的key
DEFAULT_MODEL=deepseek-v4-pro

# Claude 系列
# ANTHROPIC_API_KEY=sk-ant-你的key
# DEFAULT_MODEL=claude-sonnet-5

# OpenAI 系列
# OPENAI_API_KEY=sk-你的key
# DEFAULT_MODEL=gpt-4o
```

项目启动时会自动加载 `.env` 文件，多个 Key 可以同时存在，通过 `DEFAULT_MODEL` 切换。

### 支持的模型

| 模型 | 环境变量 | 说明 |
|------|---------|------|
| `deepseek-v4-pro` | `DEEPSEEK_API_KEY` | DeepSeek 旗舰 |
| `deepseek-chat` | `DEEPSEEK_API_KEY` | DeepSeek V3 |
| `deepseek-reasoner` | `DEEPSEEK_API_KEY` | DeepSeek R1 |
| `claude-sonnet-5` | `ANTHROPIC_API_KEY` | Claude 性价比之选 |
| `claude-opus-5` | `ANTHROPIC_API_KEY` | Claude 最强质量 |
| `claude-haiku-4-5` | `ANTHROPIC_API_KEY` | Claude 最快最省 |
| `gpt-4o` | `OPENAI_API_KEY` | OpenAI 备选 |
| `gpt-4o-mini` | `OPENAI_API_KEY` | OpenAI 轻量 |

---

## Docker 部署

### 本地 Docker Desktop（Windows/macOS）

```powershell
# PowerShell
copy .env.example .env
notepad .env               # 填 Key
docker build -t aiproduce .
docker run -p 7860:7860 -v aiproduce_workspace:/app/workspace -v .\.env:/app/.env:ro aiproduce
```

浏览器打开 `http://localhost:7860`。

### 云服务器（Linux）

```bash
# SSH 连上服务器
git clone <仓库地址> aiproduce && cd aiproduce
cp .env.example .env && nano .env   # 填 Key
bash deploy/deploy.sh               # 一键部署
```

访问 `http://服务器IP:7860`。

### 生产级部署

```bash
# 配 Nginx 反代 + 域名（见 deploy/nginx.conf）
sudo cp deploy/nginx.conf /etc/nginx/sites-available/aiproduce
sudo certbot --nginx -d 你的域名.com

# 开机自启（见 deploy/aiproduce.service）
sudo cp deploy/aiproduce.service /etc/systemd/system/
sudo systemctl enable --now aiproduce
```

### Docker Compose

```bash
cp .env.example .env
nano .env   # 填 Key
docker compose up -d
```

---

## CLI 命令

| 命令 | 说明 |
|------|------|
| `aiproduce init -n "项目" -s novel.txt` | 初始化项目 |
| `aiproduce run --thin-slice -p <ID>` | 运行最小验证链路 |
| `aiproduce run --thin-slice --novel novel.txt` | 从小说直接运行 |
| `aiproduce wizard` | 交互式配置向导 |
| `aiproduce status` | 查看所有项目 |
| `aiproduce status -p <ID>` | 查看项目进度 |
| `aiproduce report` | Token 消耗统计 |
| `aiproduce web` | 启动 Gradio Web UI |

---

## 项目结构

```
AIproduce/
├── Readme.md                        # 方案设计文档
├── DEVELOPMENT.md                   # 开发指南（本文件）
├── .env.example                     # 环境变量模板
├── Dockerfile                       # Docker 镜像
├── docker-compose.yml               # Docker Compose
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
│   │   ├── base.py                  #   AgentBase 基类（支持 Claude/DeepSeek/OpenAI）
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
├── deploy/                          # 部署文件
│   ├── deploy.sh                    #   一键部署脚本
│   ├── nginx.conf                   #   Nginx 反代配置
│   └── aiproduce.service            #   systemd 服务
├── tests/
│   ├── test_deconstructor.py        # N02 单元测试
│   ├── test_scene_writer.py         # N11 单元测试
│   └── fixtures/                    # 测试小说（古装/现代/科幻）
│       ├── sample_novel.md
│       ├── sample_novel_chapter.md
│       ├── sample_novel_modern.md
│       └── sample_novel_fantasy.md
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

---

## 核心设计

### Agent 基类

所有 Agent 继承 `AgentBase`，提供：

| 能力 | 说明 |
|------|------|
| `call_llm(user_input, system_prompt, output_schema)` | 统一 LLM 调用接口 |
| `_call_via_langchain()` | LangChain 后端（Claude / DeepSeek / OpenAI） |
| `_call_via_anthropic()` | 原生 Anthropic SDK 后端（降级） |
| `_render_prompt(template, **vars)` | `{{variable}}` 模板渲染 |
| `_validate_json(response, schema)` | 结构化输出校验 |
| 自动重试 | 最多 3 次，指数退避 |

**LLM + 降级双模式**：所有 Agent 在无 API Key 时自动切换到规则模式，管道永不中断。

**多模型支持**：通过 `.env` 中的 `DEFAULT_MODEL` 切换。DeepSeek 使用 OpenAI 兼容接口（`ChatOpenAI`），Claude 使用原生 SDK。

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

---

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

---

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

---

## 常见问题

### Q: ChromaDB 首次运行很慢？

ChromaDB 首次使用会下载 ONNX embedding 模型（~79MB），仅需一次。Docker 构建时已预下载。

### Q: 如何切换 LLM 模型？

编辑 `.env` 文件中的 `DEFAULT_MODEL`，重启容器即可，无需重新构建。

### Q: Docker 容器内网页打不开？

确保 Gradio 绑定 `0.0.0.0` 而非 `127.0.0.1`（Docker 要求）。Dockerfile 默认已配置正确。

### Q: 工作流中断后如何恢复？

项目状态保存在 `workspace/projects/{project_id}/` 中。使用 `aiproduce status -p <ID>` 查看进度，`aiproduce run --thin-slice -p <ID>` 继续运行——已完成节点自动跳过。

### Q: 云服务器上如何开放端口？

```bash
# 防火墙放行 7860 端口
sudo ufw allow 7860
# 云服务商控制台也需要在安全组中放行 7860
```

推荐使用 Nginx 反代到 80/443 端口（见 `deploy/nginx.conf`）。

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1.0 | 2026-07 | 13/13 Agent、Thin Slice 完整链路、Docker 部署、DeepSeek 支持、.env 配置、Gradio Web UI、4 题材测试小说、云服务器一键部署 |
