# AIproduce 工作台前端 — 开发启动文档

**版本**: v1.0
**前置阅读**:
- `docs/workbench-design.md` — 工作台整体设计（两视图 + 交互 + 角色人设）
- `docs/virtual-office-research.md` — 虚拟 Agent 办公室调研（渲染方案 + 参考项目）

---

## 一、项目初始化

### 1.1 技术栈

| 层 | 选型 | 版本 |
| :--- | :--- | :--- |
| 框架 | React + TypeScript | 18+ |
| 构建 | Vite | 6+ |
| UI 组件库 | Ant Design | 5+ |
| 图表 | Recharts | 2+ |
| 状态管理 | Zustand | 5+ |
| 样式 | Tailwind CSS | 4+ |
| 路由 | React Router | 7+ |
| 实时通信 | WebSocket（原生）+ 3s 轮询降级 | — |

### 1.2 创建命令

```bash
npm create vite@latest aiproduce-workbench -- --template react-ts
cd aiproduce-workbench
npm install antd recharts zustand react-router-dom tailwindcss @tailwindcss/vite
npm run dev   # → http://localhost:5173
```

### 1.3 文件目录结构

```
src/
├── main.tsx                    # 入口
├── App.tsx                     # 路由根
│
├── routes/
│   ├── ProjectList.tsx         # /                   项目列表页
│   ├── Workbench.tsx           # /projects/:id       工作台主页（壳）
│   ├── WorkflowView.tsx        # /projects/:id/workflow  工作流视图
│   └── OfficeView.tsx          # /projects/:id/office     办公室视图
│
├── components/
│   ├── layout/
│   │   ├── TopBar.tsx          # 顶部状态栏（项目名/进度/Token/成本）
│   │   └── SidePanel.tsx       # 右侧详情面板（复用）
│   │
│   ├── workflow/
│   │   ├── PhaseStepper.tsx    # 5 阶段进度条
│   │   ├── NodeTimeline.tsx    # 21 节点纵向时间线
│   │   ├── NodeCard.tsx        # 单个节点卡片
│   │   ├── NodeDetail.tsx      # 节点详情（输入/输出/校验报告）
│   │   ├── SceneHeatmap.tsx    # 阶段三/四的场次热力图
│   │   └── ValidationBadge.tsx # 校验结果徽标（阻塞/警告计数）
│   │
│   ├── office/
│   │   ├── OfficeCanvas.tsx    # <canvas> 主渲染区
│   │   ├── AgentSprite.ts      # 角色精灵类（非 React 组件）
│   │   ├── AgentDetailPanel.tsx # Agent 详情弹窗
│   │   ├── SpeechBubble.tsx    # 对话气泡
│   │   ├── MiniMap.tsx         # 右下角全局小地图
│   │   └── BreakRoom.tsx       # 茶水间/卫生间区域
│   │
│   └── shared/
│       ├── TokenBar.tsx        # Token 消耗统计条
│       ├── LogPanel.tsx        # 底部实时日志面板
│       └── Notification.tsx    # 通知系统
│
├── mock/                       # ★ Mock 数据层（即 API 契约）
│   ├── project.ts              # 项目列表 Mock
│   ├── workflow-state.ts       # 工作流全量快照 Mock
│   ├── office-state.ts         # 办公室全局状态 Mock
│   ├── node-detail.ts          # 单节点详情 Mock
│   └── index.ts                # Mock 导出 + 延迟/随机异常模拟
│
├── stores/
│   ├── useWorkflowStore.ts     # 工作流视图状态
│   ├── useOfficeStore.ts       # 办公室视图状态
│   └── useAppStore.ts          # 全局状态（项目/连接/主题）
│
├── hooks/
│   ├── useWebSocket.ts         # WebSocket 连接 + 3s 轮询降级
│   └── useMockData.ts          # Mock 模式数据注入
│
└── types/
    ├── workflow.ts             # 工作流相关类型定义
    ├── agent.ts                # Agent 相关类型定义
    └── office.ts               # 办公室相关类型定义
```

---

## 二、Mock 数据层（= API 契约）

> **重要说明**：以下 Mock 数据的 JSON 结构就是前端期望的数据格式。后端 API 实现时，返回相同结构即可，具体的 URL 端点路径、Query 参数等不做强制约束，由后端团队自行决定。

### 2.1 TypeScript 类型定义

```typescript
// types/workflow.ts

/** 节点状态 */
type NodeStatus = 'pending' | 'running' | 'retrying' | 'passed' | 'failed' | 'skipped';

/** 校验严重级别 */
type IssueSeverity = 'blocking' | 'warning' | 'suggestion';

/** 阶段信息 */
interface PhaseInfo {
  phase: number;           // 1-5
  name: string;            // "项目初始化与原著解构"
  nodeIds: string[];       // 该阶段的节点列表
  status: 'done' | 'active' | 'pending';
  completedNodes: number;
  totalNodes: number;
}

/** 工作流节点 */
interface NodeInfo {
  nodeId: string;          // "N01"
  name: string;            // "项目初始化"
  agentName: string;       // "项目调度Agent"
  phase: number;
  status: NodeStatus;
  startedAt: string | null;   // ISO 时间戳
  completedAt: string | null;
  retryCount: number;
  maxRetries: number;
  // 摘要（不在详情面板展示，用于列表快速查看）
  summary: {
    inputBrief: string;    // 一句话输入摘要
    outputBrief: string;   // 一句话输出摘要（RUNNING 时为 "生成中..."）
  };
}

/** 阶段三/四的场次卡片 */
interface SceneCardStatus {
  sceneId: string;         // "EP03-S07"
  episodeId: string;       // "EP03"
  sceneNumber: number;     // 7
  narrativeFunction: string; // "塑造人物"
  status: 'pending' | 'running' | 'done' | 'failed';
  characters: string[];    // ["萧炎", "药老"]
  location: string;        // "练武场"
}

/** 校验报告 */
interface ValidationReport {
  nodeId: string;
  checkerAgent: string;
  passed: boolean;
  blockingIssues: Array<{
    dimension: string;      // 校验维度
    description: string;
    location: string;       // "第3场第5句台词"
    suggestion: string;
  }>;
  warningIssues: Array<{
    dimension: string;
    description: string;
    count: number;
  }>;
  suggestionIssues: Array<{
    dimension: string;
    description: string;
  }>;
}

/** 工作流全量快照（GET /api/projects/:id/workflow 的返回格式） */
interface WorkflowSnapshot {
  projectId: string;
  projectName: string;
  mode: 'thin_slice' | 'full';
  currentPhase: number;
  currentNode: string | null;     // 当前正在执行的节点，null = 全部完成或未开始
  startedAt: string;
  phases: PhaseInfo[];
  nodes: NodeInfo[];
  // 阶段三/四的场次矩阵（thin_slice 模式可能为空）
  sceneMatrix: {
    episodeId: string;
    episodeNumber: number;
    totalScenes: number;
    completedScenes: number;
    scenes: SceneCardStatus[];
  }[];
  // 全局统计
  stats: {
    totalNodes: number;
    completedNodes: number;
    failedNodes: number;
    totalTokens: number;
    estimatedCostUsd: number;
    elapsedSeconds: number;
    activeAgentCount: number;
  };
}
```

```typescript
// types/agent.ts

type AgentStatus = 'idle' | 'working' | 'walking' | 'break';

interface AgentEntity {
  agentId: string;           // "character_checker"
  nodeId: string;            // "N12"
  name: string;              // "镜先生"
  emoji: string;             // "🪞"
  department: 'command' | 'asset' | 'creative' | 'qa' | 'polish';
  status: AgentStatus;
  // 工位
  deskPosition: { x: number; y: number };
  // 当前位置（走动中可能与 deskPosition 不同）
  currentPosition: { x: number; y: number };
  // 并发实例（如单场剧本Agent有3个实例）
  instances: AgentInstance[];
  // 当前任务（工作状态时非空）
  currentTask: {
    type: 'dispatch' | 'query' | 'submit' | 'review' | 'reject' | 'cross_check';
    description: string;     // "校验 EP03-S07"
    targetAgentId?: string;  // 走动目标
    message?: string;        // 气泡文本
  } | null;
  // 空闲事件（idle/break 状态时非空）
  idleEvent: {
    name: string;            // "校准墙上所有时钟"
    location: 'desk' | 'breakroom' | 'restroom';
    remainingSeconds: number;
  } | null;
  // 统计
  stats: {
    totalTokens: number;
    totalCalls: number;
    completedTasks: number;
    estimatedCostUsd: number;
  };
}

interface AgentInstance {
  instanceId: string;        // "scene_writer#2"
  status: AgentStatus;
  currentSceneId?: string;   // "EP03-S08"
  startedAt?: string;
  tokensThisSession: number;
}
```

```typescript
// types/office.ts

/** 走动中的交互 */
interface ActiveInteraction {
  fromAgentId: string;
  toAgentId: string;
  type: 'dispatch' | 'query' | 'submit' | 'review' | 'reject' | 'cross_check';
  progress: number;          // 0-1，走动进度
  message: string;           // 气泡文本
  documentType: 'task_slip' | 'folder' | 'script_stack' | 'red_mark_report';
}

/** 办公室全局状态（GET /api/projects/:id/office-state 的返回格式） */
interface OfficeState {
  projectId: string;
  agents: AgentEntity[];
  activeInteractions: ActiveInteraction[];
  breakRoomOccupants: string[];     // agentId 列表
  restroomOccupants: string[];
  announcement: string | null;      // "阶段四完成！茶歇时间~ ☕"
  timestamp: string;
}
```

### 2.2 Mock 数据示例

```typescript
// mock/office-state.ts

export const mockOfficeState: OfficeState = {
  projectId: "demo-001",
  agents: [
    {
      agentId: "scheduler",
      nodeId: "N01",
      name: "总指挥",
      emoji: "🎯",
      department: "command",
      status: "working",
      deskPosition: { x: 480, y: 520 },
      currentPosition: { x: 480, y: 520 },
      instances: [{ instanceId: "scheduler", status: "working" }],
      currentTask: {
        type: "dispatch",
        description: "分发 EP03-S08 任务",
        targetAgentId: "scene_writer_2",
        message: "EP03-S08，给你，限时3分钟"
      },
      idleEvent: null,
      stats: { totalTokens: 8450, totalCalls: 12, completedTasks: 9, estimatedCostUsd: 0.03 }
    },
    {
      agentId: "scene_writer",
      nodeId: "N11",
      name: "小写手",
      emoji: "✍️",
      department: "creative",
      status: "working",
      deskPosition: { x: 300, y: 260 },
      currentPosition: { x: 300, y: 260 },
      instances: [
        { instanceId: "scene_writer#1", status: "working", currentSceneId: "EP03-S07", startedAt: "2026-07-30T14:32:15Z", tokensThisSession: 2847 },
        { instanceId: "scene_writer#2", status: "working", currentSceneId: "EP03-S08", startedAt: "2026-07-30T14:33:40Z", tokensThisSession: 1204 },
        { instanceId: "scene_writer#3", status: "working", currentSceneId: "EP04-S01", startedAt: "2026-07-30T14:34:22Z", tokensThisSession: 523 },
      ],
      currentTask: {
        type: "submit",
        description: "EP03-S07 已生成，提交校验",
        targetAgentId: "character_checker",
        message: "镜先生，EP03-S07 写好了，请过目"
      },
      idleEvent: null,
      stats: { totalTokens: 56230, totalCalls: 8, completedTasks: 5, estimatedCostUsd: 0.22 }
    },
    {
      agentId: "character_checker",
      nodeId: "N12",
      name: "镜先生",
      emoji: "🪞",
      department: "qa",
      status: "working",
      deskPosition: { x: 480, y: 380 },
      currentPosition: { x: 480, y: 380 },
      instances: [{ instanceId: "character_checker", status: "working" }],
      currentTask: {
        type: "review",
        description: "校验 EP03-S06",
        targetAgentId: "scene_writer",
        message: "萧炎这句台词——'我最讨厌背信弃义之人'，和第8集的行为矛盾。你人物弧光跳了一步"
      },
      idleEvent: null,
      stats: { totalTokens: 23450, totalCalls: 45, completedTasks: 38, estimatedCostUsd: 0.12 }
    },
    {
      agentId: "timeline_keeper",
      nodeId: "N03",
      name: "时老",
      emoji: "⏳",
      department: "asset",
      status: "idle",
      deskPosition: { x: 660, y: 120 },
      currentPosition: { x: 660, y: 120 },
      instances: [{ instanceId: "timeline_keeper", status: "idle" }],
      currentTask: null,
      idleEvent: {
        name: "校准墙上所有时钟",
        location: "desk",
        remainingSeconds: 18
      },
      stats: { totalTokens: 12400, totalCalls: 6, completedTasks: 3, estimatedCostUsd: 0.05 }
    },
    {
      agentId: "timeline_checker",
      nodeId: "N13",
      name: "钟馗",
      emoji: "🔔",
      department: "qa",
      status: "break",
      deskPosition: { x: 580, y: 380 },
      currentPosition: { x: 80, y: 40 },  // 在茶水间
      instances: [{ instanceId: "timeline_checker", status: "break" }],
      currentTask: null,
      idleEvent: {
        name: "泡枸杞，摇着折扇在办公室溜达",
        location: "breakroom",
        remainingSeconds: 25
      },
      stats: { totalTokens: 8900, totalCalls: 18, completedTasks: 15, estimatedCostUsd: 0.04 }
    },
    {
      agentId: "final_editor",
      nodeId: "N17",
      name: "总编",
      emoji: "📖",
      department: "polish",
      status: "idle",
      deskPosition: { x: 480, y: 460 },
      currentPosition: { x: 480, y: 460 },
      instances: [{ instanceId: "final_editor", status: "idle" }],
      currentTask: null,
      idleEvent: {
        name: "泡功夫茶，一壶一杯慢慢喝",
        location: "desk",
        remainingSeconds: 72
      },
      stats: { totalTokens: 0, totalCalls: 0, completedTasks: 0, estimatedCostUsd: 0 }
    },
    // ─── 资产管理部剩余 3 人 ───
    {
      agentId: "deconstructor", nodeId: "N02", name: "书虫", emoji: "📚",
      department: "asset", status: "idle",
      deskPosition: { x: 120, y: 120 }, currentPosition: { x: 120, y: 120 },
      instances: [{ instanceId: "deconstructor", status: "idle" }],
      currentTask: null,
      idleEvent: { name: "从书堆里抽出一本古籍翻阅", location: "desk", remainingSeconds: 22 },
      stats: { totalTokens: 34500, totalCalls: 3, completedTasks: 2, estimatedCostUsd: 0.18 }
    },
    {
      agentId: "character_asset", nodeId: "N03", name: "小竹", emoji: "👤",
      department: "asset", status: "idle",
      deskPosition: { x: 300, y: 120 }, currentPosition: { x: 300, y: 120 },
      instances: [{ instanceId: "character_asset", status: "idle" }],
      currentTask: null,
      idleEvent: { name: "用彩色纸折纸鹤，挂在人物关系墙上", location: "desk", remainingSeconds: 15 },
      stats: { totalTokens: 18900, totalCalls: 4, completedTasks: 2, estimatedCostUsd: 0.09 }
    },
    {
      agentId: "world_asset", nodeId: "N03", name: "墨先生", emoji: "🗺️",
      department: "asset", status: "idle",
      deskPosition: { x: 480, y: 120 }, currentPosition: { x: 480, y: 120 },
      instances: [{ instanceId: "world_asset", status: "idle" }],
      currentTask: null,
      idleEvent: { name: "研磨墨条，在废纸上练毛笔字", location: "desk", remainingSeconds: 35 },
      stats: { totalTokens: 15600, totalCalls: 4, completedTasks: 2, estimatedCostUsd: 0.07 }
    },
    // ─── 创作部剩余 3 人 ───
    {
      agentId: "adaptation_planner", nodeId: "N04", name: "策总", emoji: "🎬",
      department: "creative", status: "idle",
      deskPosition: { x: 120, y: 260 }, currentPosition: { x: 120, y: 260 },
      instances: [{ instanceId: "adaptation_planner", status: "idle" }],
      currentTask: null,
      idleEvent: { name: "站在窗边端着咖啡看窗外", location: "desk", remainingSeconds: 28 },
      stats: { totalTokens: 22100, totalCalls: 2, completedTasks: 2, estimatedCostUsd: 0.10 }
    },
    {
      agentId: "episode_outliner", nodeId: "N07", name: "架构师", emoji: "🏗️",
      department: "creative", status: "idle",
      deskPosition: { x: 360, y: 260 }, currentPosition: { x: 360, y: 260 },
      instances: [{ instanceId: "episode_outliner", status: "idle" }],
      currentTask: null,
      idleEvent: { name: "用乐高积木搭三幕式结构模型", location: "desk", remainingSeconds: 55 },
      stats: { totalTokens: 19800, totalCalls: 3, completedTasks: 2, estimatedCostUsd: 0.09 }
    },
    {
      agentId: "scene_splitter", nodeId: "N09", name: "细节控", emoji: "🔍",
      department: "creative", status: "working",
      deskPosition: { x: 180, y: 340 }, currentPosition: { x: 180, y: 340 },
      instances: [
        { instanceId: "scene_splitter#1", status: "working", currentSceneId: "EP03", startedAt: "2026-07-30T14:30:00Z", tokensThisSession: 4100 },
        { instanceId: "scene_splitter#2", status: "working", currentSceneId: "EP04", startedAt: "2026-07-30T14:33:00Z", tokensThisSession: 2800 },
      ],
      currentTask: { type: "query", description: "拆分 EP03 场次", targetAgentId: "character_asset", message: "小竹，EP03 涉及哪些人物的状态变化节点？" },
      idleEvent: null,
      stats: { totalTokens: 15600, totalCalls: 5, completedTasks: 3, estimatedCostUsd: 0.07 }
    },
    // ─── 校验部剩余 1 人 ───
    {
      agentId: "format_checker", nodeId: "N14", name: "方正", emoji: "📏",
      department: "qa", status: "idle",
      deskPosition: { x: 680, y: 380 }, currentPosition: { x: 680, y: 380 },
      instances: [{ instanceId: "format_checker", status: "idle" }],
      currentTask: null,
      idleEvent: { name: "把桌上所有文具按颜色→长度→类型重新排列", location: "desk", remainingSeconds: 42 },
      stats: { totalTokens: 6700, totalCalls: 22, completedTasks: 20, estimatedCostUsd: 0.03 }
    },
  ],
  activeInteractions: [
    {
      fromAgentId: "scene_writer",
      toAgentId: "character_checker",
      type: "submit",
      progress: 0.65,
      message: "镜先生，EP03-S07 写好了，请过目",
      documentType: "script_stack"
    },
    {
      fromAgentId: "character_checker",
      toAgentId: "scene_writer",
      type: "reject",
      progress: 0.30,
      message: "台词风格警告2条，请修改",
      documentType: "red_mark_report"
    }
  ],
  breakRoomOccupants: ["timeline_checker"],
  restroomOccupants: [],
  announcement: null,
  timestamp: "2026-07-30T14:35:06Z"
};
```

### 2.3 工作流快照 Mock 数据

```typescript
// mock/workflow-state.ts

export const mockWorkflowSnapshot: WorkflowSnapshot = {
  projectId: "demo-001",
  projectName: "斗破苍穹-第一季",
  mode: "full",
  currentPhase: 4,
  currentNode: "N11",
  startedAt: "2026-07-30T12:20:00Z",
  phases: [
    { phase: 1, name: "项目初始化与原著解构", nodeIds: ["N01","N02","N03"], status: "done", completedNodes: 3, totalNodes: 3 },
    { phase: 2, name: "改编顶层设计与全局结构", nodeIds: ["N04","N05","N06","N07","N08"], status: "done", completedNodes: 5, totalNodes: 5 },
    { phase: 3, name: "分集结构与场次拆解", nodeIds: ["N09","N10"], status: "active", completedNodes: 0, totalNodes: 2 },
    { phase: 4, name: "逐场剧本批量生成", nodeIds: ["N11","N12","N13","N14","N15"], status: "active", completedNodes: 0, totalNodes: 5 },
    { phase: 5, name: "全局校验与终稿统合", nodeIds: ["N16","N17","N18","N19","N20","N21"], status: "pending", completedNodes: 0, totalNodes: 6 },
  ],
  nodes: [
    // 阶段一
    { nodeId: "N01", name: "项目初始化", agentName: "项目调度Agent", phase: 1, status: "passed", startedAt: "2026-07-30T12:20:00Z", completedAt: "2026-07-30T12:20:05Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "项目配置信息", outputBrief: "共享工作区目录 + 项目配置文件" } },
    { nodeId: "N02", name: "原著文本拆分与分层摘要", agentName: "原著解构Agent", phase: 1, status: "passed", startedAt: "2026-07-30T12:20:10Z", completedAt: "2026-07-30T12:45:30Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "原著全文 TXT (62万字)", outputBrief: "1,247个语义块 + 分层摘要体系 + 基础标签库" } },
    { nodeId: "N03", name: "首轮资产库构建", agentName: "人设+世界观+时间线Agent", phase: 1, status: "passed", startedAt: "2026-07-30T12:45:35Z", completedAt: "2026-07-30T13:05:00Z", retryCount: 1, maxRetries: 3, summary: { inputBrief: "分层摘要 + 基础标签库", outputBrief: "人物资产库v1.0 (47人) + 世界观库v1.0 + 时间轴v1.0" } },
    // 阶段二
    { nodeId: "N04", name: "改编策划总纲生成", agentName: "改编策划Agent", phase: 2, status: "passed", startedAt: "2026-07-30T13:05:10Z", completedAt: "2026-07-30T13:20:00Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "全局摘要 + 资产库v1.0 + 项目配置", outputBrief: "《改编策划总纲》(6模块完整)" } },
    { nodeId: "N05", name: "策划案合规校验", agentName: "全局合规校验Agent", phase: 2, status: "passed", startedAt: "2026-07-30T13:20:05Z", completedAt: "2026-07-30T13:22:00Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "《改编策划总纲》", outputBrief: "合规校验通过 (0阻塞/2建议)" } },
    { nodeId: "N06", name: "资产库迭代更新", agentName: "人设+世界观+时间线Agent", phase: 2, status: "passed", startedAt: "2026-07-30T13:22:10Z", completedAt: "2026-07-30T13:35:00Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "策划案取舍原则 + 资产库v1.0", outputBrief: "官方资产库v2.0 (只读锁定)" } },
    { nodeId: "N07", name: "全剧分集大纲生成", agentName: "分集大纲Agent", phase: 2, status: "passed", startedAt: "2026-07-30T13:35:10Z", completedAt: "2026-07-30T13:50:00Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "资产库v2.0 + 策划总纲", outputBrief: "《全剧分集大纲》(24集)" } },
    { nodeId: "N08", name: "大纲全局校验", agentName: "人设+时间线校验Agent", phase: 2, status: "passed", startedAt: "2026-07-30T13:50:05Z", completedAt: "2026-07-30T13:55:00Z", retryCount: 0, maxRetries: 3, summary: { inputBrief: "《全剧分集大纲》", outputBrief: "大纲校验通过 (0阻塞/3警告)" } },
    // 阶段三（进行中）
    { nodeId: "N09", name: "单集场次拆分", agentName: "场次拆分Agent", phase: 3, status: "running", startedAt: "2026-07-30T13:55:10Z", completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "分集大纲 + 对应原文 + 资产库v2.0", outputBrief: "EP01-EP04 场次拆分中..." } },
    { nodeId: "N10", name: "场次清单校验", agentName: "格式与合规校验Agent", phase: 3, status: "running", startedAt: "2026-07-30T14:05:00Z", completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "EP01-EP02 场次清单", outputBrief: "EP01校验通过 / EP02校验中..." } },
    // 阶段四（进行中）
    { nodeId: "N11", name: "单场剧本生成", agentName: "单场剧本Agent (×3并发)", phase: 4, status: "running", startedAt: "2026-07-30T14:10:00Z", completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "EP01-S01~S12 + EP02-S01~S10 + EP03-S01~S07", outputBrief: "已完成 29/82 场 (35%)" } },
    { nodeId: "N12", name: "人设一致性校验", agentName: "人设校验Agent", phase: 4, status: "running", startedAt: "2026-07-30T14:12:00Z", completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "EP01-S01~S08 剧本初稿", outputBrief: "已校验8场: 6通过/1警告/1打回" } },
    { nodeId: "N13", name: "时间线与细节校验", agentName: "时间线校验Agent", phase: 4, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待N12完成后接收剧本", outputBrief: "—" } },
    { nodeId: "N14", name: "格式与合规校验", agentName: "格式校验Agent", phase: 4, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待N13完成后接收剧本", outputBrief: "—" } },
    { nodeId: "N15", name: "剧本入库", agentName: "项目调度Agent", phase: 4, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待三重校验全部通过", outputBrief: "—" } },
    // 阶段五
    { nodeId: "N16", name: "单集剧本拼接", agentName: "项目调度Agent", phase: 5, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待所有场次入库", outputBrief: "—" } },
    { nodeId: "N17", name: "单集节奏优化", agentName: "全局统稿Agent", phase: 5, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待单集剧本拼接完成", outputBrief: "—" } },
    { nodeId: "N18", name: "全剧拼接与全局审计", agentName: "全局合规校验Agent", phase: 5, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待所有单集优化完成", outputBrief: "—" } },
    { nodeId: "N19", name: "全剧统稿打磨", agentName: "全局统稿Agent", phase: 5, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待全局审计通过", outputBrief: "—" } },
    { nodeId: "N20", name: "终稿合规终审", agentName: "全局合规校验Agent", phase: 5, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待全剧终稿", outputBrief: "—" } },
    { nodeId: "N21", name: "项目结项归档", agentName: "项目调度Agent", phase: 5, status: "pending", startedAt: null, completedAt: null, retryCount: 0, maxRetries: 3, summary: { inputBrief: "等待终审通过", outputBrief: "—" } },
  ],
  sceneMatrix: [
    {
      episodeId: "EP01", episodeNumber: 1, totalScenes: 12, completedScenes: 12,
      scenes: [
        { sceneId: "EP01-S01", episodeId: "EP01", sceneNumber: 1, narrativeFunction: "制造冲突", status: "done", characters: ["萧炎","纳兰嫣然"], location: "萧家大厅" },
        { sceneId: "EP01-S02", episodeId: "EP01", sceneNumber: 2, narrativeFunction: "推进剧情", status: "done", characters: ["萧炎","药老"], location: "后山山洞" },
        // ... S03-S12 均为 done
      ]
    },
    {
      episodeId: "EP02", episodeNumber: 2, totalScenes: 14, completedScenes: 14,
      scenes: [
        { sceneId: "EP02-S01", episodeId: "EP02", sceneNumber: 1, narrativeFunction: "过渡衔接", status: "done", characters: ["萧炎","萧薰儿"], location: "萧家后院" },
        // ... 全部 done
      ]
    },
    {
      episodeId: "EP03", episodeNumber: 3, totalScenes: 15, completedScenes: 3,
      scenes: [
        { sceneId: "EP03-S01", episodeId: "EP03", sceneNumber: 1, narrativeFunction: "推进剧情", status: "done", characters: ["萧炎","药老"], location: "练武场" },
        { sceneId: "EP03-S02", episodeId: "EP03", sceneNumber: 2, narrativeFunction: "推进剧情", status: "done", characters: ["萧炎"], location: "练武场(夜)" },
        { sceneId: "EP03-S03", episodeId: "EP03", sceneNumber: 3, narrativeFunction: "铺垫伏笔", status: "done", characters: ["药老"], location: "山洞" },
        { sceneId: "EP03-S04", episodeId: "EP03", sceneNumber: 4, narrativeFunction: "塑造人物", status: "running", characters: ["萧炎","萧薰儿"], location: "后山" },
        { sceneId: "EP03-S05", episodeId: "EP03", sceneNumber: 5, narrativeFunction: "塑造人物", status: "running", characters: ["萧炎"], location: "练武场(黄昏)" },
        { sceneId: "EP03-S06", episodeId: "EP03", sceneNumber: 6, narrativeFunction: "推进剧情", status: "running", characters: ["萧炎","药老","萧战"], location: "萧家大厅" },
        { sceneId: "EP03-S07", episodeId: "EP03", sceneNumber: 7, narrativeFunction: "塑造人物", status: "running", characters: ["萧炎","药老"], location: "练武场(黄昏)" },
        { sceneId: "EP03-S08", episodeId: "EP03", sceneNumber: 8, narrativeFunction: "推进剧情", status: "pending", characters: ["萧炎"], location: "坊市" },
        // ... S09-S15 均为 pending
      ]
    },
    {
      episodeId: "EP04", episodeNumber: 4, totalScenes: 14, completedScenes: 0,
      scenes: [
        { sceneId: "EP04-S01", episodeId: "EP04", sceneNumber: 1, narrativeFunction: "制造冲突", status: "running", characters: ["萧炎","加列奥"], location: "坊市拍卖场" },
        // ... S02-S14 pending
      ]
    },
  ],
  stats: {
    totalNodes: 21, completedNodes: 8, failedNodes: 0,
    totalTokens: 256230, estimatedCostUsd: 1.42, elapsedSeconds: 8106,
    activeAgentCount: 7,
  },
};
```

### 2.4 Mock 模式开关

```typescript
// mock/index.ts

// 开发时设为 true，上线后改为 false
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

// 模拟网络延迟 (200-800ms)
function randomDelay() {
  return new Promise(r => setTimeout(r, 200 + Math.random() * 600));
}

// 模拟 5% 概率的随机异常（测试错误处理）
function maybeError() {
  if (Math.random() < 0.05) throw new Error('模拟网络异常');
}

export async function fetchWorkflowSnapshot(projectId: string): Promise<WorkflowSnapshot> {
  if (!USE_MOCK) {
    return fetch(`/api/projects/${projectId}/workflow`).then(r => r.json());
  }
  await randomDelay();
  maybeError();
  return mockWorkflowSnapshot;
}

export async function fetchOfficeState(projectId: string): Promise<OfficeState> {
  if (!USE_MOCK) {
    return fetch(`/api/projects/${projectId}/office-state`).then(r => r.json());
  }
  await randomDelay();
  maybeError();
  // 每次返回时随机微调 Agent 状态（模拟实时变化）
  return randomizeMockState(mockOfficeState);
}
```

---

## 三、路由设计

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProjectList />} />
        <Route path="/projects/:id" element={<Workbench />}>
          {/* 默认重定向到工作流视图 */}
          <Route index element={<Navigate to="workflow" replace />} />
          <Route path="workflow" element={<WorkflowView />} />
          <Route path="workflow/:nodeId" element={<WorkflowView />} />
          <Route path="office" element={<OfficeView />} />
          <Route path="office/:agentId" element={<OfficeView />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

路由对应 URL：

```
/                                      → 项目列表页
/projects/demo-001                     → 工作台（默认跳 workflow）
/projects/demo-001/workflow            → 工作流视图
/projects/demo-001/workflow/N11        → 工作流视图 + 展开 N11 详情
/projects/demo-001/office              → 办公室视图
/projects/demo-001/office/scene_writer → 办公室 + 展开小写手详情
```

---

## 四、组件树

```
<App>
  ├── <ProjectList />                          # / 路由
  │
  └── <Workbench>                              # /projects/:id 路由
        ├── <TopBar />                         # 项目名 | 进度 | Token | 成本 | [工作流/办公室] 切换
        │
        ├── <WorkflowView>                     # /projects/:id/workflow
        │     ├── <PhaseStepper />             # 阶段 1-5 进度条
        │     ├── <NodeTimeline>               # 21 节点纵向时间线
        │     │     └── <NodeCard /> ×21       # 每个节点卡片（可点击）
        │     ├── <SceneHeatmap />             # 阶段三/四展开时显示
        │     └── <SidePanel>                  # 右侧详情面板
        │           └── <NodeDetail />         # 选中节点的输入/输出/校验
        │
        └── <OfficeView>                       # /projects/:id/office
              ├── <OfficeCanvas>               # <canvas> 主渲染区
              │     ├── (AgentSprite)          # 角色精灵（Canvas 内部绘制）
              │     ├── (SpeechBubble)         # 对话气泡
              │     └── (BreakRoom)            # 茶水间/卫生间区域
              ├── <MiniMap />                  # 右下角全局小地图
              ├── <AgentDetailPanel />         # 点击 Agent 的详情弹窗
              └── <LogPanel />                 # 底部可折叠实时日志
```

---

## 五、状态管理（Zustand Store 设计）

### 5.1 全局 Store

```typescript
// stores/useAppStore.ts
interface AppState {
  // 连接状态
  connected: boolean;
  useMock: boolean;

  // 当前项目
  currentProjectId: string | null;
  projectName: string;

  // 模式
  viewMode: 'workflow' | 'office';

  // 通知
  notifications: Array<{ id: string; type: 'error'|'warning'|'info'|'success'; message: string }>;

  // Actions
  setConnected: (v: boolean) => void;
  setViewMode: (v: 'workflow' | 'office') => void;
  addNotification: (n: Omit<Notification, 'id'>) => void;
}
```

### 5.2 工作流 Store

```typescript
// stores/useWorkflowStore.ts
interface WorkflowState {
  snapshot: WorkflowSnapshot | null;
  selectedNodeId: string | null;
  loading: boolean;

  // Actions
  fetchSnapshot: (projectId: string) => Promise<void>;
  selectNode: (nodeId: string | null) => void;
}
```

### 5.3 办公室 Store

```typescript
// stores/useOfficeStore.ts
interface OfficeStoreState {
  officeState: OfficeState | null;
  selectedAgentId: string | null;
  loading: boolean;

  // 动画控制
  animationFrameId: number | null;

  // Actions
  fetchState: (projectId: string) => Promise<void>;
  selectAgent: (agentId: string | null) => void;
  startRenderLoop: (canvas: HTMLCanvasElement) => void;
  stopRenderLoop: () => void;
}
```

---

## 六、Canvas 渲染引擎（办公室视图）

参考 Pixel Agents 的 GameEngine 分层，简化版本：

```
┌─────────────────────────────────────────┐
│              OfficeCanvas.tsx            │  ← React 组件，持有 <canvas> ref
│  负责：useEffect 启动/停止渲染循环       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│            renderLoop()                  │  ← requestAnimationFrame
│  每帧执行：                              │
│  1. clearCanvas()                       │
│  2. drawBackground()  — 办公室地板/墙壁  │
│  3. drawFurniture()   — 工位/桌椅/装饰   │
│  4. drawAgents()      — 角色精灵+状态动画│
│  5. drawBubbles()     — 对话气泡         │
│  6. drawInteractions()— 走动中的交互动画  │
│  7. drawAnnouncement()— 全局广播横幅      │
└──────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           SpriteManager                 │  ← 精灵加载+缓存
│  sprites: Map<string, HTMLImageElement> │
│  loadSprite(name): Promise<void>        │
│  getFrame(name, row, col): ImageData    │
└──────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           Pathfinding                   │  ← 简单路径网格
│  walkPath: {x,y}[]  — 预定义路径点      │
│  findPath(from, to): {x,y}[]            │
│  getProgress(from, to, t): {x,y}        │  ← t ∈ [0,1]
└──────────────────────────────────────────┘
```

### 开发分步策略

| 步 | 内容 | 产物 |
| :--- | :--- | :--- |
| **Step 1** | 静态背景 + 13 个 Emoji 定位在工位上 | 能看到"办公室"的基本样子 |
| **Step 2** | 状态色点（绿/蓝/红圆点画在每个 Emoji 下方） | 能看到谁在工作 |
| **Step 3** | 走动动画（Emoji 用 CSS `translate` 在两个位置间移动） | 能看到交互 |
| **Step 4** | 气泡弹出（绝对定位 `<div>` 叠在 Canvas 上方，非 Canvas 内绘制） | 能看到对话 |
| **Step 5** | Canvas 一体渲染（把气泡也画进 Canvas，去掉 DOM 叠层） | 性能优化 |
| **Step 6** | 替换 Emoji 为精灵表动画 | 正式视觉 |

> **建议**：Step 1-4 用 **DOM + CSS** 做，能极快出原型（1-2 天可看到走动效果）。Step 5-6 再迁移到 **Canvas 渲染**。OpenClaw Office 证明了纯 SVG+CSS 做办公室是完全可行的——我们的 13 个角色如果不做太复杂的帧动画，DOM 方案就能撑到上线。

---

## 七、开发顺序建议（分 4 个迭代）

### Sprint 1：骨架 + 工作流视图 MVP（3-5 天）

**目标**：能看到 21 节点状态 + 点击看输入输出

- [ ] 项目初始化（Vite + Ant Design + Tailwind + Zustand + Router）
- [ ] 类型定义 + Mock 数据
- [ ] `TopBar`（静态）
- [ ] `PhaseStepper`（5 阶段进度）
- [ ] `NodeTimeline` + `NodeCard`（21 节点，颜色映射状态）
- [ ] `NodeDetail`（选中节点展示输入/输出/校验）
- [ ] `useWorkflowStore` + Mock 数据注入
- [ ] 路由配置

### Sprint 2：办公室视图 MVP（3-5 天）

**目标**：能看到 Agent 在工位上、有状态色、能走动

- [ ] `OfficeCanvas`（先 DOM 方案：背景图 + Emoji 定位）
- [ ] 13 个 Agent 在各自工位上渲染（静态）
- [ ] 状态色点（绿/蓝/红/灰/橙）
- [ ] 走动动画（CSS `transition` 在两个位置间移动）
- [ ] `SpeechBubble`（绝对定位气泡，随走动移动）
- [ ] `AgentDetailPanel`（点击 Emoji 弹出详情）
- [ ] `useOfficeStore` + Mock 数据注入
- [ ] `MiniMap`

### Sprint 3：增强 + 实时通信（3-5 天）

**目标**：办公室活起来（茶水间事件、日志、通知）

- [ ] 茶水间/卫生间随机事件系统
- [ ] 随机空闲事件触发（时老对表、总编泡茶...）
- [ ] `LogPanel`（底部实时日志）
- [ ] `Notification`（通知系统）
- [ ] `useWebSocket`（WebSocket + 3s 轮询降级）
- [ ] 场次热力图（`SceneHeatmap`）
- [ ] 深链接路由（`/workflow/N11` 自动展开对应节点）

### Sprint 4：Canvas 迁移 + 精灵表（3-5 天）

**目标**：从 DOM 方案升级到 Canvas 渲染

- [ ] `SpriteManager`（加载 MetroCity 精灵表）
- [ ] `renderLoop`（Canvas requestAnimationFrame）
- [ ] 角色帧动画（打字/阅读/行走）
- [ ] Canvas 内气泡渲染
- [ ] 部门房间隔断 + 走廊路径
- [ ] `Pathfinding`（简单网格寻路）

---

## 八、关键设计约束（防跑偏）

1. **Mock 数据结构 = API 契约**：后端团队拿到第二章的 TypeScript 类型定义就知道该返回什么
2. **办公室先 DOM 后 Canvas**：不要一上来就搞 Canvas 渲染引擎。DOM 方案 2 天出效果、Canvas 方案 2 周出效果。先用 DOM 验证交互逻辑，再迁移
3. **工作流视图和办公室视图共享同一份数据源**：都是 `WorkflowState`，只是可视化维度不同。不要为两个视图分别定义数据格式
4. **Ant Design 只用于工作流视图**：时间线、卡片、表格、Stepper 用 Ant Design。办公室视图是纯自定义渲染，不依赖组件库
5. **13 个角色的人设文本不要修改**：`workbench-design.md` 第十章的角色设定是经过仔细推敲的，后续只是把它从文字翻译成视觉（精灵/配色/工位道具）

---

## 九、Sprint 2 专项：DOM 方案办公室渲染细节

> Sprint 2 用纯 DOM + CSS 实现办公室，这是最快的出效果路径。以下是具体实现要点。

### 9.1 办公室坐标系统

```
(0,0) ──────────────────────────────────────→ x (800px)
  │
  │   ┌─────────┐  ┌──────────┐  ┌──────────┐
  │   │ 茶水间    │  │  走廊     │  │ 卫生间    │
  │   │ (80,40)  │  │          │  │ (720,40)  │
  │   └─────────┘  └──────────┘  └──────────┘
  │
  │   ┌──────────────────────────────────────────┐
  │   │         资产管理部 (y=100~200)             │
  │   │  📚(120) 👤(300) 🗺️(480) ⏳(660)        │
  │   └──────────────────────────────────────────┘
  │
  │   ┌──────────────────────────────────────────┐
  │   │         创作部 (y=240~360)                 │
  │   │  🎬(120) 🏗️(360) 🔍(180,340) ✍️×3(520~680)│
  │   └──────────────────────────────────────────┘
  │
  │   ┌──────────────────────────────────────────┐
  │   │         校验部 (y=360~420)                 │
  │   │  🪞(480) 🔔(580) 📏(680)                 │
  │   └──────────────────────────────────────────┘
  │
  │   ┌──────────────────────────────────────────┐
  │   │         统稿部 (y=440~480)                 │
  │   │  📖(480)                                  │
  │   └──────────────────────────────────────────┘
  │
  │   ┌──────────────────────────────────────────┐
  │   │         调度中心 (y=500~560)               │
  │   │  🎯(480)  [公告板]                        │
  │   └──────────────────────────────────────────┘
  │
  ▼ y (560px)
```

### 9.2 Agent 组件实现

```typescript
// components/office/AgentSprite.tsx  (DOM版本，非Canvas)
interface AgentSpriteProps {
  agent: AgentEntity;
  onClick: (agentId: string) => void;
}

export function AgentSprite({ agent, onClick }: AgentSpriteProps) {
  const pos = agent.currentPosition;

  const statusColor = {
    idle: '#d9d9d9',
    working: '#1677ff',
    walking: '#fa8c16',
    break: '#52c41a',
  }[agent.status];

  return (
    <div
      className="absolute cursor-pointer transition-all duration-100"
      style={{
        left: pos.x,
        top: pos.y,
        transform: 'translate(-50%, -50%)',
        zIndex: agent.status === 'walking' ? 50 : 10,
      }}
      onClick={() => onClick(agent.agentId)}
    >
      {/* 角色 Emoji（后续替换为 <img> 精灵帧） */}
      <div className="text-3xl text-center select-none">{agent.emoji}</div>

      {/* 状态指示灯 */}
      <div
        className="w-3 h-3 rounded-full mx-auto mt-1 border-2 border-white"
        style={{ backgroundColor: statusColor }}
      />

      {/* 姓名标签 */}
      <div className="text-xs text-center text-gray-600 mt-0.5 whitespace-nowrap">
        {agent.name}
      </div>

      {/* 并发实例数徽标 */}
      {agent.instances.length > 1 && (
        <div className="absolute -top-1 -right-1 w-5 h-5 bg-blue-500 text-white
                        text-xs rounded-full flex items-center justify-center font-bold">
          {agent.instances.length}
        </div>
      )}

      {/* 头顶 Token 进度条（P2） */}
      {agent.status === 'working' && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-10 h-1 bg-gray-200 rounded">
          <div
            className="h-full bg-blue-500 rounded"
            style={{ width: `${Math.min(100, agent.stats.totalTokens / 1000)}%` }}
          />
        </div>
      )}
    </div>
  );
}
```

### 9.3 走动动画插值

```typescript
// stores/useOfficeStore.ts 中的走动逻辑

function animateWalk(agentId: string, from: Position, to: Position, durationMs: number) {
  const startTime = performance.now();

  function tick(now: number) {
    const elapsed = now - startTime;
    const t = Math.min(elapsed / durationMs, 1.0);
    // easeInOutQuad 缓动
    const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

    set(state => {
      const agent = state.officeState?.agents.find(a => a.agentId === agentId);
      if (!agent) return;
      agent.currentPosition = {
        x: from.x + (to.x - from.x) * eased,
        y: from.y + (to.y - from.y) * eased,
      };
    });

    if (t < 1.0) {
      requestAnimationFrame(tick);
    } else {
      // 到达后触发气泡 + 停留
      set(state => {
        const agent = state.officeState?.agents.find(a => a.agentId === agentId);
        if (!agent) return;
        agent.currentPosition = to;
        agent.status = 'working';
      });
    }
  }

  requestAnimationFrame(tick);
}
```

### 9.4 对话气泡组件

```typescript
// components/office/SpeechBubble.tsx
export function SpeechBubble({ agent }: { agent: AgentEntity }) {
  if (!agent.currentTask?.message) return null;

  const pos = agent.currentPosition;
  const color = {
    dispatch: '#52c41a',    // 绿-任务分发
    query: '#1677ff',       // 蓝-信息查询
    submit: '#1677ff',      // 蓝-创作提交
    review: '#fa8c16',      // 橙-校验审核
    reject: '#ff4d4f',      // 红-打回修改
    cross_check: '#1677ff', // 蓝-交叉校验
  }[agent.currentTask.type] || '#333';

  return (
    <div
      className="absolute z-50 animate-bubbleFadeIn"
      style={{ left: pos.x + 30, top: pos.y - 50, maxWidth: 220 }}
    >
      <div
        className="px-3 py-2 rounded-lg text-xs text-white shadow-md"
        style={{ backgroundColor: color }}
      >
        {agent.currentTask.message}
      </div>
      <div
        className="w-0 h-0 mx-auto"
        style={{
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
          borderTop: `6px solid ${color}`,
        }}
      />
    </div>
  );
}
```

### 9.5 DOM 方案的已知局限

| 局限 | 影响 | 何时解决 |
| :--- | :--- | :--- |
| 不支持角色帧动画（打字/阅读） | 角色只有静态 Emoji + 位移动画 | Sprint 4 Canvas 迁移 |
| 走道不自然（直线移动） | 看起来像棋子移动而非真人走路 | Sprint 4 加寻路 |
| 大量气泡时 DOM 节点增多 | 13 个角色全部有气泡也不到 30 个节点，无性能问题 | 无需解决 |
| 无法做粒子特效（烟花/天气） | 阶段完成的庆祝效果做不了 | Sprint 4 Canvas 或永不支持 |

---

## 十、环境变量配置

```bash
# .env (开发时)
VITE_USE_MOCK=true              # 使用 Mock 数据，不连接后端
VITE_API_BASE=http://localhost:8000   # 后端 API 地址（USE_MOCK=false 时生效）
VITE_WS_URL=ws://localhost:8000/ws   # WebSocket 地址

# .env.production (上线时)
VITE_USE_MOCK=false
VITE_API_BASE=https://api.aiproduce.example.com
VITE_WS_URL=wss://api.aiproduce.example.com/ws
```

---

## 十一、后端对接指南

> 当后端 API 就绪后，只需切换环境变量。确认后端返回的数据结构符合第二章的 TypeScript 类型定义即可。

### 11.1 切换步骤

1. 设置 `VITE_USE_MOCK=false`
2. 确认后端 API 返回的 JSON 字段名和嵌套层级与第二章类型一致
3. 删除 `mock/` 目录（或保留作为测试夹具）

### 11.2 后端需要实现的数据端点

| 端点 | 返回类型 | 说明 |
| :--- | :--- | :--- |
| `GET /api/projects` | `ProjectSummary[]` | 项目列表 |
| `GET /api/projects/:id/workflow` | `WorkflowSnapshot` | 工作流全量快照 |
| `GET /api/projects/:id/office-state` | `OfficeState` | 办公室全局状态 |
| `GET /api/projects/:id/workflow/:nodeId` | `NodeDetail` | 单节点详情（输入/输出/校验） |
| `WS /ws/projects/:id` | 推送事件 | 实时状态变更推送 |
| `POST /api/projects/:id/retry/:nodeId` | — | 手动重试失败节点 |

**唯一硬性要求**：返回的 JSON 字段名和嵌套层级与第二章的 TypeScript 类型定义一致。前端不做字段映射——后端返回什么就用什么。

**不要求**：端点 URL 路径不必完全相同（前端 `mock/index.ts` 改一行即可）；WebSocket 事件格式可后定；查询参数、分页等细节后端自行决定。

### 11.3 从 Python 后端生成 OfficeState 的参考代码

```python
# 后端需要实现的转换逻辑示意
# 输入：WorkflowState（src/workflow/state.py）+ Agent 运行时状态
# 输出：符合 OfficeState 类型的 JSON

def build_office_state(workflow_state, agent_runtimes) -> dict:
    """将内部状态转换为前端期望的 OfficeState 格式"""
    agents = []
    for agent_id, runtime in agent_runtimes.items():
        node_id = runtime.get("node_id")
        node_status = workflow_state.node_statuses.get(node_id, "pending")

        # 后端状态 → 前端状态
        status_map = {
            "running": "working",
            "retrying": "working",
            "passed": "idle",
            "failed": "idle",
            "pending": "idle",
            "skipped": "idle",
        }
        status = status_map.get(node_status, "idle")

        agents.append({
            "agentId": agent_id,
            "nodeId": node_id,
            "name": runtime["name"],
            "emoji": runtime["emoji"],
            "department": runtime["department"],
            "status": status,
            "deskPosition": runtime["desk_position"],
            "currentPosition": runtime.get("current_position", runtime["desk_position"]),
            "instances": [
                {
                    "instanceId": f"{agent_id}#{i+1}",
                    "status": "working" if node_status == "running" else "idle",
                    "currentSceneId": inst.get("scene_id"),
                    "startedAt": inst.get("started_at"),
                    "tokensThisSession": inst.get("tokens", 0),
                }
                for i, inst in enumerate(runtime.get("instances", []))
            ],
            "currentTask": build_task_info(workflow_state, agent_id) if status == "working" else None,
            "idleEvent": pick_random_idle_event(agent_id) if status == "idle" else None,
            "stats": {
                "totalTokens": token_counter._node_totals.get(node_id, TokenUsage()).total_tokens,
                "totalCalls": sum(1 for r in token_counter._records if r.node_id == node_id),
                "completedTasks": runtime.get("completed", 0),
                "estimatedCostUsd": token_counter._node_totals.get(node_id, TokenUsage()).estimated_cost_usd,
            },
        })

    return {
        "projectId": workflow_state.project_config["project_id"],
        "agents": agents,
        "activeInteractions": build_interactions(workflow_state),
        "breakRoomOccupants": random_break_agents(agents),
        "restroomOccupants": [],
        "announcement": None,
        "timestamp": datetime.now().isoformat(),
    }
```
