# 虚拟 Agent 办公室项目调研报告

**调研日期**: 2026-07-30
**调研目的**: 为 AIproduce 工作台的"Agent 办公室视图"设计提供参考

---

## 一、项目总览

市面上的虚拟 Agent 办公室项目按可视化风格可分为三派，均在 2025-2026 年密集出现：

| 项目 | Stars | 风格 | 渲染方案 | 核心定位 |
| :--- | :--- | :--- | :--- | :--- |
| **OpenClaw Office** | 632 | 等距 2D SVG | SVG + CSS Animations | Multi-Agent 监控 + Skills 开发平台 |
| **Pixel Agents** | — | 像素风 2D | Canvas 2D | VS Code 扩展 + CLI，agent-agnostic 架构 |
| **OpenClaw Pixel Agents** | — | 像素风 2D | Canvas 2D + GameEngine | 轻量级像素办公室 + 布局编辑器 |
| **OctoOffice** | — | 像素风 2D | Pixi.js 8 | 本地优先的虚拟软件公司 + 全流程编排 |
| **AITEAM-X** | — | 像素风 / 二次元 | — | 模拟经营游戏风格 + 4种视觉主题 |
| **My Virtual Office** | 287 | 等距 2D | 自研引擎 + A*寻路 | 自托管 AI 工作空间 + 天气/日夜循环 |
| **AI Sweatshop** | — | 像素风 2D | PixiJS | 游戏化 + 区块链经济 + 技能升级系统 |

---

## 二、逐项目详细分析

### 2.1 OpenClaw Office

**仓库**: [WW-AI-Lab/openclaw-office](https://github.com/WW-AI-Lab/openclaw-office)
**技术栈**: React 19 + Vite 6 + Zustand 5 + Tailwind CSS 4 + WebSocket + Recharts

#### 借鉴要点

**1) 核心隐喻设计**（⭐⭐⭐⭐⭐ 直接适用）
> Agent = 数字员工 | 办公室 = Agent 运行时 | 工位 = Session | 会议室 = 协作上下文

这个隐喻和我们的设计理念完全一致。OpenClaw Office 将整个系统抽象为一套组织架构，比我们的"5部门13角色"更加通用化。可以考虑将"部门"概念更强调地植入我们的办公室布局中。

**2) SVG 确定性头像生成**（⭐⭐⭐⭐ 可借鉴）
基于 `agentId` 确定性生成 SVG 头像，不同 Agent 有不同外观。这比我们手动为13个角色设计形象更易扩展——当 `单场剧本Agent` 有 N 个并发实例时，可以用确定性算法自动生成 N 个外观略有差异的"小写手"，而不是全部长得一样。

**3) 状态动画映射**（⭐⭐⭐⭐⭐ 直接适用）
```
idle → 坐工位不动
working → 打字/翻阅文件
speaking → 说话气泡
tool_calling → 特殊动画
error → 红色闪烁
```
我们的 6 种状态（IDLE/RUNNING/RETRYING/PASSED/FAILED/SKIPPED）可以映射为对应的角色动画。

**4) 协作连线**（⭐⭐⭐⭐ 直接适用）
Agent 间消息传递时画出可视连接线。在我们的场景中，可以用于可视化作坊交互（校验员→创作者打回、创作者→资产部查询等）。但我们的设计用"角色走动"替代了连线，这是更生动的方案。

**5) 侧边面板图表**（⭐⭐⭐⭐ 直接适用）
Token 折线图 + 成本饼图 + 活跃热力图 + 子 Agent 关系图 + 事件时间轴。这些可以作为 Agent 详情卡片的补充。

**6) Mock 模式**（⭐⭐⭐⭐⭐ 开发必备）
无需连接 Gateway 即可开发。我们开发前端时也应该做 Mock 数据层，模拟 21 节点的运行状态。

#### 不适合借鉴的部分
- OpenClaw Office 的等距 SVG 渲染方案对有大量走动的场景不够灵活，像素 Canvas 方案更适合我们
- 它是一个完整的产品（Skills 开发平台、Chat 工作区、控制台），而我们只需要观测台功能

---

### 2.3 OpenClaw Pixel Agents（SweetSophia）

**仓库**: [SweetSophia/openclaw-pixel-agents](https://github.com/SweetSophia/openclaw-pixel-agents)
**技术栈**: React 19 + Vite + Canvas 2D + Express + Socket.IO

#### 借鉴要点

**1) GameEngine 架构**（⭐⭐⭐⭐⭐ 核心技术参考）

这是最值得深入研究的部分——作者实现了一个完整的 Canvas 2D 游戏引擎：

| 组件 | 职责 |
| :--- | :--- |
| `GameEngine` | Canvas 2D 渲染循环、精灵动画、寻路、宿主门面 |
| `EditorController` | 鼠标/触摸编辑器状态和 Canvas 监听器生命周期 |
| `SpriteLoader` | 加载精灵表单并切片为单帧 Canvas |
| `LayoutEditor` | 工具栏、家具面板、布局管理器 UI |
| `PixelOffice` | Canvas 包装器，将 Agent/布局数据接入 GameEngine |

这套分层架构可以直接参考——我们可以把 AIproduce 办公室的 Canvas 渲染拆成：
- `OfficeRenderer`（渲染循环）
- `PathfindingEngine`（Agent 走动寻路，办公室走道需要定义路径网格）
- `SpriteManager`（13个角色的精灵管理）
- `InteractionAnimator`（走动+气泡+文档交换动画）

**2) 精灵表单格式**（⭐⭐⭐⭐⭐ 直接适用）

```
角色精灵表: 112×96px PNG
- 7 帧/行（16×32px/帧）
- 3 行: 向下(行0)、向上(行1)、向右(行2)
- 帧映射: 0-2 行走, 3-4 打字, 5-6 阅读
- 左方向由翻转右行自动生成
```

我们13个角色每个需要一套精灵表，可以找设计师画，也可以用 [MetroCity](https://jik-a-4.itch.io/metrocity-free-topdown-character-pack) 这个免费素材包（Pixel Agents 用的就是这个）。

**3) 拖拽布局编辑器**（⭐⭐⭐⭐ 可借鉴，非 MVP 必需）

- 家具面板选择 → 点击网格放置
- 拖拽移动、右键旋转、删除
- 布局保存/加载、多个布局切换
- 2 秒防抖自动保存

这个功能可以放到 P2 甚至 P3——先做好固定的办公室布局，后续再让用户自定义。

**4) 家具系统**（⭐⭐⭐ 参考即可）

25 种家具类型：桌子、PC、椅子、植物、书架、白板、咖啡机、画作等。Manifest JSON 定义精灵尺寸和碰撞体积。

我们的需求不同——重点是13个角色的工位设计，而不是通用家具市场。但工位差异化（如书虫的书堆、墨先生的地图桌、时老的座钟）可以参考这个系统的扩展方式。

**5) 数据源模式**（⭐⭐⭐⭐ 架构参考）

三种模式：CLI 轮询 / Ingest 推送 / Auto 自动切换。我们的后端 API 层（第七节设计的 REST + WebSocket）与之思路一致，但可以更简单——直接从 `WorkflowState` 内存对象读取。

#### 不适合借鉴的部分
- 后端用 Express + Socket.IO，而我们更适合 FastAPI + WebSocket（与 Python 技术栈一致）
- 它是 OpenClaw 专属的，架构不需要做到 agent-agnostic

---

### 2.3 OctoOffice

**仓库**: [Chepko932/OctoOffice](https://github.com/Chepko932/OctoOffice)
**技术栈**: Pixi.js 8 + React + Vite + SQLite + WebSocket

#### 借鉴要点

**1) 部门房间设计**（⭐⭐⭐⭐⭐ 直接适用）

OctoOffice 最出彩的设计——7 个部门房间，Agent 按部门归属在不同的房间里工作，穿过走廊开会。这和我们"5部门13角色+部门间走动"的设计高度一致：

| OctoOffice | 我们的设计 |
| :--- | :--- |
| 7 个部门房间 | 5 个部门区域（资产管理部/创作部/校验部/统稿部/调度中心） |
| 走廊连接 | 走廊连接 + 茶水间 + 卫生间 |
| Agent 在房间内走动 | 工位间走动 + 跨部门走动 |

**2) CEO Orchestrator 自主模式**（⭐⭐⭐⭐ 长期可借鉴）

CEO 定期 tick 自主决策——审阅 inbox、创建任务、审批、重新分配工作。这在我们的场景中对应"项目调度Agent"的自动化调度——当所有场次完成校验后，自动触发下一阶段。但要注意 OctoOffice 的 CEO 有最多3个决策/tick 的限制，这是防止 AI 失控的好设计。

**3) Pixi.js 8 渲染**（⭐⭐⭐ 评估中）

Pixi.js 是专业的 2D 游戏渲染引擎，性能比 Canvas 2D 更好（WebGL 加速），内置精灵、容器、粒子系统。但如果我们的 Agent 数量不超过 20，DOM + CSS 或 Canvas 2D 完全够用。Pixi.js 的学习曲线和包体积（~500KB）需要权衡。

**4) Kanban 任务看板**（⭐⭐⭐⭐ 可借鉴）

完整的任务生命周期（Inbox → Planned → In Progress → Review → Done）。这对应我们的工作流视图——21 节点的状态流转本质上就是 Kanban 的纵向版。可以考虑在工作流视图底部加一个迷你 Kanban 展示当前阶段的场次卡片。

**5) 直接 Agent 对话**（⭐⭐⭐ P3 考虑）

给特定 Agent 发消息、Agent 在同一频道回复。对应我们的"人工审核节点交互"——审核者可以直接给创作 Agent 发修改意见。

---

### 2.4 Pixel Agents（pixel-agents-hq）

**仓库**: [pixel-agents-hq/pixel-agents](https://github.com/pixel-agents-hq/pixel-agents)
**技术栈**: React 19 + Vite + Canvas 2D + Fastify

#### 借鉴要点

**1) Agent-agnostic 架构**（⭐⭐⭐⭐⭐ 架构参考）

这是该项目最值得学习的设计理念：

```
core/
  provider/    ← HookProvider 接口定义集成边界
  adapter/     ← 归一化为 AgentEvent 模型
  transport/   ← WebSocket 消息协议
  schema/      ← AsyncAPI 消息契约
server/
  runtime/     ← AgentRuntime 更新中心状态
  persistence/ ← 持久化
adapters/
  vscode/      ← VS Code 适配器
  cli/         ← 独立 CLI 适配器
webview-ui/    ← React 前端
```

**对我们来说**：可以将 AIproduce 的 Agent 监测适配层抽象为 `AgentObserver` 接口——无论是 LangGraph 的回调、日志文件解析还是 WebSocket 事件，统一转化为 `AgentStateUpdate` 事件推给前端。

**2) 状态检测双路径**（⭐⭐⭐⭐ 可借鉴）

- **Hooks 模式**（主路径）：`SessionStart` → `PreToolUse` → `PermissionRequest` → `Stop`
- **Transcript 模式**（备用路径）：扫描 JSONL session 文件

我们的对应方案：
- **主路径**：`WorkflowState._notify()` hook 推送（第九章的设计）
- **备用路径**：定时轮询 `WorkflowState.node_statuses` + 日志 tail

**3) 子 Agent 可视化**（⭐⭐⭐⭐ 直接适用）

子 Agent（如 `Task` tool 产生的临时 Agent）作为独立角色出现在办公室中，有生命周期变化。我们的"单场剧本Agent ×3 并发实例"完全对应这个场景——主 Agent 是工位，#1/#2/#3 是临时出现的角色。

**4) Areas 区域映射**（⭐⭐⭐⭐ 可借鉴）

将办公室划分为命名区域（Areas），将文件夹映射到区域，Agent 自动坐到对应区域。我们可以映射为：将节点类型映射到对应部门工位——N11 的 Agent 自动坐到创作部的"小写手"工位。

**5) 路线图愿景**（⭐⭐⭐ 长期参考）

> Stage 1: Everywhere, with everything.（agent-agnostic）
> Stage 2: Actually a game.（HP条、积分、可交互家具）
> Stage 3: Expand the orchestration frontier.（拖拽组队、任务认领）

我们的"办公室视图"本质上处在 Stage 1→Stage 2 的过渡期。Stage 2 的"Health bars for rate limits and token budgets"是一个很好的灵感——可以在每个 Agent 头顶显示 Token 消耗进度条。

---

## 三、关键设计决策对比

### 3.1 渲染方案选型

| 方案 | 项目代表 | 优点 | 缺点 | 推荐场景 |
| :--- | :--- | :--- | :--- | :--- |
| **SVG + CSS** | OpenClaw Office | 可访问性好、DOM 可交互、CSS 动画简单 | 大量元素性能下降、复杂动画实现困难 | 等距静态办公室 |
| **Canvas 2D** | Pixel Agents, Pixel Agents | 性能好、精灵动画自然、可控性强 | 交互组件需手写、事件系统复杂 | 像素风+走动动画 |
| **Pixi.js 8** | OctoOffice | WebGL 加速、内置动画系统、粒子效果 | 包体积大（~500KB）、学习曲线陡 | 高性能+复杂粒子 |
| **DOM + CSS** | — | 开发最快、可复用 UI 库 | 复杂动画性能差 | 静态卡片式 Agent 列表 |

**对 AIproduce 的建议**：

MVP 阶段用 **Canvas 2D**（参考 Pixel Agents 的 GameEngine 架构），原因：
- 13 个角色 + 走动动画是核心需求，Canvas 2D 最适合精灵动画
- 不需要 WebGL 级别的性能（Pixi.js overkill）
- 有成熟的精灵表格式和 GameEngine 架构可参考
- 与 React 集成可以用 `<canvas>` ref + `useEffect` 渲染循环

长期如果要做粒子特效（"阶段完成！🎉"烟花）、天气效果（AITEAM-X 的 day/night cycle），再考虑升级到 Pixi.js。

### 3.2 角色形象方案

| 方案 | 项目代表 | 优点 | 缺点 |
| :--- | :--- | :--- | :--- |
| **SVG 确定性生成** | OpenClaw Office | 无限扩展、自动差异化 | 风格单一、缺乏个性 |
| **像素精灵表** | Pixel Agents, OctoOffice | 精致、可定制、有游戏感 | 需要美术资源、新角色需新精灵 |
| **Emoji/CSS 图标** | — | 零成本、快速原型 | 视觉冲击力弱 |

**对 AIproduce 的建议**：

**短期（MVP）**：用**大号 Emoji + CSS 卡片 + 简单 CSS 位移动画**做走动。13 个角色用我们设定的 Emoji（📚🪞🔔✍️ 等），走动用 `transform: translate()`。2-3 天可出原型。

**中期**：找设计师画 13 套精灵表（参考 MetroCity 风格），或者用 AI 生成像素角色。参考 Pixel Agents 的 `SpriteLoader` 架构加载精灵。

### 3.3 实时通信方案

| 方案 | 项目代表 | 优点 | 缺点 |
| :--- | :--- | :--- | :--- |
| **WebSocket** | OpenClaw Office, OctoOffice | 双向、低延迟、原生支持 | 需要 WS 服务端 |
| **Socket.IO** | OpenClaw Pixel Agents | 自动重连、房间/广播 | 额外依赖、非标准协议 |
| **SSE** | AITEAM-X | HTTP 原生、单向够用 | 不支持双向（不能暂停/重试） |
| **3 秒轮询** | OpenClaw Pixel Agents, Pixel Agents | 最简单、无需 WS | 延迟高、浪费带宽 |

**对 AIproduce 的建议**：

用 **WebSocket**，与项目 Python 技术栈天然契合（FastAPI 原生支持 WebSocket）。在 `WorkflowState._notify()` 中触发 WS 推送，延迟 < 100ms。同时保留 **3 秒轮询作为降级方案**（WS 断开时自动切轮询）。

---

## 四、可直接复用的开源资源

| 资源 | 来源 | 用途 |
| :--- | :--- | :--- |
| MetroCity 角色包 | [itch.io](https://jik-a-4.itch.io/metrocity-free-topdown-character-pack) | 精灵表基础素材，Pixel Agents 和 OpenClaw Pixel Agents 都在用 |
| Pixel Agents GameEngine | [GitHub](https://github.com/pixel-agents-hq/pixel-agents) | Canvas 2D 渲染引擎架构参考（MIT 协议） |
| OpenClaw Office SVG 头像 | [GitHub](https://github.com/WW-AI-Lab/openclaw-office) | 确定性 SVG 头像生成算法参考 |
| 精灵表格式标准 | OpenClaw Pixel Agents | 112×96px / 7帧×3行 的格式可直接沿用 |

---

## 五、对 AIproduce 办公室视图的修正建议

基于调研结果，对之前设计的第十章做以下修正：

### 5.1 技术方案调整

| 原设计 | 修正后 |
| :--- | :--- |
| DOM + CSS + React | **Canvas 2D + React**（参考 Pixel Agents GameEngine 架构） |
| CSS Transition 走动 | **Canvas 帧动画 + 简单 A* 寻路**（走道网格预定义） |
| 固定布局 | **先做固定布局，预留布局编辑器接口**（参考 OpenClaw Pixel Agents 的家具系统） |
| — | **增加 Mock 模式**（参考 OpenClaw Office），开发时无需连接后端 |

### 5.2 角色形象方案调整

| 原设计 | 修正后 |
| :--- | :--- |
| 手动为 13 个角色设计文字人设 | 分为两层：**底层**——文本人设（保留第十章的角色设定）；**上层**——像素精灵（用 MetroCity 素材包 + 换装配色区分 13 人） |
| Emoji 作为唯一标识 | Emoji 作为 MVP 占位符，逐步替换为精灵表 |
| 并发实例全部相同 | 并发实例用同一精灵表 + 不同配色（如小写手#1 红色文化衫，#2 蓝色文化衫）|

### 5.3 新增功能建议

| 功能 | 灵感来源 | 优先级 |
| :--- | :--- | :--- |
| **Agent 头顶 Token 进度条** | Pixel Agents 路线图 Stage 2 | P2 |
| **部门房间隔断 + 走廊** | OctoOffice 部门房间 | P1（提升办公室真实感）|
| **走道网格 + 简单寻路** | My Virtual Office A* 寻路 | P1（走动更自然）|
| **子 Agent 临时出现/消失动画** | Pixel Agents subagent 可视化 | P1（并发实例可视化）|
| **阶段完成烟花/横幅** | AITEAM-X 环境特效 | P3 |
| **办公室布局编辑器** | 全部四个项目都有 | P3 |
| **CSS 降级渲染** | OpenClaw Office | P0（Canvas 加载失败时回退到 DOM 卡片）|

### 5.4 架构分层调整

参考 Pixel Agents 的分层设计，建议将办公室视图的前端架构分为：

```
office-view/
  core/            # Canvas 渲染引擎（平台无关）
    GameLoop.ts    # requestAnimationFrame 渲染循环
    SpriteManager.ts  # 精灵加载+缓存+切片
    Pathfinding.ts    # 简单网格寻路（办公室走道预定义路径点）
    
  state/           # 状态管理
    OfficeStore.ts # Zustand store（Agent位置/状态/动画帧）
    useAgentSync.ts   # WebSocket + 3s 轮询降级
    
  components/      # React 组件
    OfficeCanvas.tsx   # <canvas> 元素 + useEffect 渲染循环
    AgentDetailPanel.tsx  # 点击 Agent 的详情面板（复用现有设计）
    MiniMap.tsx      # 右下角小地图
    
  assets/          # 静态资源
    sprites/       # 13 套角色精灵表 + 家具精灵表
    layouts/       # 办公室布局 JSON
```

---

## 六、总结

这次调研最大的收获是：**我们的"Agent 办公室"设计思路与 2025-2026 年的行业实践高度吻合，并不是空中楼阁**。有 5+ 个开源项目在探索同一个方向（把 Agent 可视化为办公室角色），而且技术栈（Canvas 2D + React + WebSocket）和设计模式（GameEngine / SpriteLoader / 布局编辑器）已经形成了一套成熟的参考范式。

**核心建议**：
1. **MVP 用 Canvas 2D**，参考 Pixel Agents 的 GameEngine 架构但做减法（不需要布局编辑器、不需要家具市场、不需要 agent-agnostic 适配层）
2. **精灵素材**先用 MetroCity 免费包 + Emoji 占位，后续找设计师画定制精灵
3. **把"部门房间+走廊"做出来**——这是 OctoOffice 最出彩的差异化设计，也让我们的"5部门13角色"概念真正落地
4. **Mock 模式先行**——先让办公室跑起来看到效果，再接入后端数据
