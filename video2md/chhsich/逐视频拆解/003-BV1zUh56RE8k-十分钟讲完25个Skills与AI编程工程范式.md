# 视频 003｜Matt Pocock：十分钟讲透 25 个 AI 编程 Skills 与 150K Token 聪明区工程闭环

> **文档级别**：✅ A 级深度解析（通读 ASR 高清转录，共 1343 秒，干货密度拉满）  
> **视频 ID**：`BV1zUh56RE8k` ｜ **平台**：`Bilibili` ｜ **时长**：`22:23`  
> **原片链接**：[https://www.bilibili.com/video/BV1zUh56RE8k](https://www.bilibili.com/video/BV1zUh56RE8k)  
> **讲者**：Matt Pocock (@mattpocockuk) ｜ **译制**：ChHsich ｜ **分析日期**：2026-09-01  
> **核心原则**：口述完全忠实于原声；提供全套 25 个技能的分类矩阵、工作流编排图、Prompt 模板与可直接落地的工程 SOP。

---

## 一、 基础信息与可信度档案

| 字段 | 内容 | 核验说明 |
| :--- | :--- | :--- |
| **官方标题** | Matt Pocock：十分钟讲完 25 个 Skills | mattpocock/skills v1.2.3【中英字幕】 | [点击直达 B 站原片](https://www.bilibili.com/video/BV1zUh56RE8k) |
| **原作者** | Matt Pocock（Total TypeScript 创始人、AI Hero 作者） | [Twitter / X 原片](https://x.com/mattpocockuk/status/2088290952704151671) |
| **配套开源仓库** | [github.com/mattpocock/skills](https://github.com/mattpocock/skills) | 全球标杆级 AI Skills 仓库（>236k Stars） |
| **发布时间** | 2026-08-25 | 抓取基准日 |
| **互动数据** | 播放量: 6,407 ｜ 点赞: 224 ｜ 评论: 21 | 高收藏比硬核技术实战解析 |
| **数据源类型** | 🤖 Faster-Whisper ASR 高清转录 + 原片双语校对 | 准确率: >99% |

---

## 二、 全景认知脉络与 25 个 Skills 工业级流水线（Executive Framework）

### 1. 从单一会话到多窗口工单流演进图

```mermaid
graph TD
    subgraph 阶段一: 需求对齐与设计概念定义 (Shaping)
        A["grill-with-docs / grill-me<br/>(高强度盘问 + ADR 架构决策对齐)"]
        A --> B{"任务规模评估"}
    end

    subgraph 阶段二: 150K Token 聪明区任务切片 (Slicing)
        B -- "< 150K Token (单窗口闭环)" --> C["implement<br/>(TDD 红绿重构)"]
        B -- "> 150K Token (超大工程)" --> D["to-spec (沉淀确定性规格书)"]
        D --> E["to-tickets (拆解独立子工单)"]
        E --> F1["Agent 窗口 1: implement"]
        E --> F2["Agent 窗口 2: implement"]
        E --> F3["Agent 窗口 3: implement"]
    end

    subgraph 阶段三: 质量闸门 (Quality Gate)
        C & F1 & F2 & F3 --> G["code-review (双轴审查: 规范轴 + 设计轴)"]
    end

    subgraph 顶层宏观决策编排 (Wayfinder Layer)
        WF["wayfinder (生成决策工单地图)"] -.-> PROT["prototype (技术可行性探针)"]
        WF -.-> RES["research (外部文档/竞品调研)"]
        PROT & RES -.-> D
    end
```

---

## 三、 25 个 Skills 完整矩阵与逐个核心机制解析

### 1. 核心工程流水线（The Core Pipeline）

| 技能名称 | 触发时机 | 核心机制与输入输出 | 关键价值 |
| :--- | :--- | :--- | :--- |
| **`grill-with-docs`** | 项目开局 / 复杂需求 | 强制 AI 对开发者进行连续深度盘问，查阅官方 Docs，生成 ADR 架构决策记录 | 消除 95% 的隐式假设与需求偏差 |
| **`to-spec`** | 盘问对齐结束后 | 将聊天记录萃取为标准化、确定性的 PRD 规格书（存入 Issue 追踪器） | 作为系统唯一真理来源（Destination） |
| **`to-tickets`** | 规格书定稿后 | 按照 150K Token 上下文最佳负载，将 Spec 拆解为多个自包含子工单 | 消除 Agent 会话中后期的“迟钝区” |
| **`implement`** | 领取具体工单时 | 内置 TDD 契约驱动，严格按 `红(写失败测试) -> 绿(写实现) -> 重构` 推进 | 确保代码 100% 具备测试自愈能力 |
| **`code-review`** | 代码编写完成后 | **双轴审查**：规范轴（代码风格/Lint/TS 类型） + 设计轴（是否符合原架构接缝） | 防止代码意图走偏与架构腐化 |

---

### 2. 宏观塑造与超大工程编排（Macro Shaping & Architecture）

| 技能名称 | 核心机制与实操流程 |
| :--- | :--- |
| **`wayfinder`** | 专为跨越数周、涉及几十个决策的超大工程设计。它不直接生成实现代码，而是**生成“决策地图 (Decision Tickets)”**，层层消解决策依赖。 |
| **`prototype`** | 在正式敲定设计前，让 AI 编写一个极小、一次性的探针 Demo，验证核心 API 可行性或性能瓶颈。 |
| **`research`** | 外部调研专家，专门抓取第三方 SDK、官方白皮书、最新库的 Breaking Changes 并输出总结报告。 |
| **`improve-codebase-architecture`** | 扫描整个代码库，识别出扁平分散的“浅模块 (Shallow Modules)”，输出深模块重构方案与可视化拓扑图。 |

---

### 3. 日常维护与疑难排查（Maintenance & Diagnostics）

| 技能名称 | 核心机制与实操流程 |
| :--- | :--- |
| **`diagnosing-bugs`** | 建立严密的“假说-验证”诊断闭环：1. 隔离复现环境；2. 提出假说；3. 添加断言探针；4. 验证假说；5. 最小化修复。 |
| **`resolving-merge-conflicts`** | **践行“切斯特顿栅栏 (Chesterton's Fence)”原则**：强制使用 `git blame` 向上追溯冲突两端代码的初始 PR 与提交动机，弄清原因后再做裁决。 |
| **`triage`** | 专为开源维护者设计，批量扫描堆积的 Open Issues，自动打标签、评估严重等级、排查重复项并输出处理优先级。 |
| **`wizard`** | 针对人类专属性操作（如配置 AWS 权限、申请第三方 API Key、2FA 认证），自动生成带交互引导的本地向导脚本。 |

---

### 4. 团队交接与高效协作（Handover & Communication）

| 技能名称 | 核心机制与实操流程 |
| :--- | :--- |
| **`grill-me`** | 纯粹的需求盘问器（不查文档），快速遍历设计树，适合日常轻量 Feature 讨论。 |
| **`handoff`** | 将当前 Agent 的上下文精炼为一份标准结构化快照，供另一个窗口的全新 Agent 无缝接力。 |
| **`to-questionnaire`** | 将 AI 的盘问会话离线化为一份 Markdown/Google Doc 问卷，供产品经理或客户线下填写后再回传。 |
| **`teach`** | **代码库极速上手神器**：自动根据当前代码库生成自适应 HTML 交互式教程，快速带领新工程师理解架构。 |
| **`wait-what`** | 专治大模型废话与幻觉重述，强制 AI 用 DDD 统一语言精简概括核心技术结论。 |
| **`writing-for-agents`** | 编写技能的 Meta-Skill，专门用来设计、重构并优化其他 `.agents/skills` 或 `AGENTS.md`。 |
| **`ask-matt`** | 内置于技能套件的随身咨询顾问，解答用户在什么场景下该选用哪个技能。 |

---

### 5. 底层基石参考技能（Foundational References）
- **`tdd`**：TDD 最佳实践红绿循环规范。
- **`grilling`**：提问哲学与设计树遍历算法。
- **`domain-modeling`**：领域驱动设计 (DDD) 实体与值对象建模。
- **`codebase-design`**：深模块与高内聚软件设计哲学。

---

## 四、 💻 可直接执行的工程模版与实操代码范式（Drop-in Assets）

### 1. 150K Token 规格书标准模板 (`to-spec` 产物示范)
```markdown
# [SPEC-001] 支付网关深模块重构规格书

## 1. 目标与设计概念 (Design Concept)
- 消除原有 `stripe/`, `paypal/` 散碎浅模块的跨层直接调用；
- 统一收敛为单一高内聚 `PaymentGatewayService` 深模块。

## 2. 公开接缝契约 (Interface Seam)
```typescript
export interface PaymentGatewayService {
  charge: (req: ChargeRequest) => Promise<Result<ChargeReceipt, PaymentError>>;
  refund: (req: RefundRequest) => Promise<Result<RefundReceipt, PaymentError>>;
}
```

## 3. 子工单拆解清单 (Tickets Breakdown for 150K Smart Zone)
- [ ] **Ticket-1**: 编写 `PaymentGatewayService` 接口类型与 Vitest 契约测试集
- [ ] **Ticket-2**: 在 `internal/stripe-adapter.ts` 中实现 Stripe 驱动并跑通单测
- [ ] **Ticket-3**: 在 `internal/paypal-adapter.ts` 中实现 PayPal 驱动并跑通单测
- [ ] **Ticket-4**: 切换业务路由并执行双轴代码审查
```

---

### 2. 双轴代码审查 Checklist (`code-review` 提示词范式)
```markdown
【指令】：请对本次 PR 进行严格的【双轴代码审查 (Dual-Axis Review)】。

【第一轴：规范轴 (Standards Axis)】
1. 是否存在未处理的 Promise / 隐式 any / 违反 TypeScript 严格模式的代码？
2. 是否遵循了代码库既有的命名风格与目录层级规范？
3. 单元测试覆盖率是否达到 100% 关键分支覆盖？

【第二轴：设计轴 (Design Axis)】
1. 模块是否保持了“深模块”特性（公开 index.ts 仅暴露极简接口，内部实现未泄漏）？
2. 是否严格对齐了最初 SPEC 文档中的领域术语与业务契约？
3. 是否破坏了任何现有的错误处理边界？
```

---

## 五、 🛠️ 实战避坑指南与局限性（Best Practices）

1. **小任务过度仪式感陷阱**：对于修改一个按钮颜色或修正一行拼写的简单任务，强行走完 5 步流程会严重降低效率；小任务直接在单窗口使用 `implement` 即可；
2. **工单切分粒度的平衡**：子工单切得过碎会导致工单本身的管理开销过大；推荐每个 Ticket 的实现工作量控制在 15~30 分钟内。

---

## 六、 💬 核心技术问答（FAQ）

- **Q1（架构设计哲学）**：为什么 Matt Pocock 的 25 个 Skills 绝大多数设计为“用户手动显式调用”，而不是“让 Agent 在后台自动感知触发”？
  - **A1**：因为自动触发型 Skill 会把大量规则提示词预先塞入 Agent 的 System Prompt，常态化侵占宝贵的 150K Token 聪明区，引发严重的 Prompt 杂音与注意力漂移；而按需显式调用能实现“零常驻上下文开销”，每个 Skill 仅在需要时精准注入。
- **Q2（多 Agent 编排实战）**：在团队中如何利用 `to-spec` + `to-tickets` 实现多 Agent 并行开发？
  - **A2**：由资深架构师配合主 Agent 在首个会话中完成 `grill-with-docs` 与 `to-spec`，输出无歧义的确定性规格书；随后使用 `to-tickets` 将任务拆分为解耦的独立子工单；最后为每个工单开启一个全新的 Agent 会话分别执行 `implement`，完成后通过 `code-review` 汇总结算。
- **Q3（疑难排查）**：当遇到一个神仙难测的 Heisenbug（时隐时现的并发 Bug）时，`diagnosing-bugs` 推荐的标准 SOP 是什么？
  - **A3**：严禁无脑胡乱改代码！1. 先编写一个必定能触发该 Bug 的最小化复现测试（Minimal Reproduction）；2. 在假设节点添加不可变的断言探针；3. 在测试绿灯前严禁触碰生产逻辑代码；4. 修复后保留该测试用例作为永久回归防线。

---

**上一篇**：[002-BV1pq8B64EFH-AI时代软件基本功反而更重要.md](./002-BV1pq8B64EFH-AI时代软件基本功反而更重要.md) ｜ **下一篇**：[004-BV1mubY6jE4u-5条Prompt从零搭一个MCPServer与结构化AI编程.md](./004-BV1mubY6jE4u-5条Prompt从零搭一个MCPServer与结构化AI编程.md) ｜ **返回总索引** → [00-总索引.md](./00-总索引.md)
