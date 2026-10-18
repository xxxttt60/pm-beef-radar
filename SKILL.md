---
name: pm-beef-radar
description: "面向 AI 产品经理的 Agent 产品雷达：从 GitHub 筛选「具备 Agent 能力（多轮上下文/RAG/工具调用/记忆）、可本地跑通、可二次包装为 0-1 项目」的 AI Agent 产品，产出产品拆解 + PRD 大纲 + 改造路线 + 面试叙事简历包。触发词：「找PM项目」「牛肉雷达产品版」「PM项目雷达」「Agent产品雷达」「产品项目包装」「AI产品作品集」"
display_name: "牛肉雷达产品版"
display_name_en: "Beef PM Radar"
description_zh: "帮产品经理从 GitHub 筛选可二次包装的 AI Agent 产品，产品验证 + 简历叙事生成"
description_en: "Find AI agent products that PMs can run, dissect and re-package as resume projects"
version: "1.1.0"
agent_created: true
---

# 产品经理 Agent 产品雷达（牛肉雷达产品版）

> 改编自「牛肉项目雷达」（backend-agent-project-selector，程序员牛肉出品），面向产品经理求职场景重写了筛选逻辑与输出物。本 skill 与原版互相独立，修改本 skill 不影响原版。
>
> 核心差异：研发版验证「源码证据」，产品版验证「产品证据」——本地跑通 / 官方 demo 走通主流程 + 从仓库与 issues 提取真实产品素材，再包装成 0-1 项目叙事。
>
> 定位边界：**本 skill 的推荐对象始终是 AI Agent 产品**（具备多轮上下文 / RAG / 工具调用 / 记忆中至少 2 项的应用）。无 Agent 能力的普通 B 端工具（CRM、工单、BI、项目管理等）不属于推荐范围，只能作为宿主或底座出现在叙事背景里；平台/构建器类项目（MaxKB、FastGPT、Dify、Yuxi 等）同样只能当底座，不得作为项目主体。

## 能力范围

从 GitHub 搜索适合产品经理二次包装的 AI Agent 产品（通用场景 Agent 应用 + B 端业务场景 Agent 应用），完成「候选池 → 短名单确认 → 仓库拉取 → 产品体验验证 → 简历项目包」全流程，生成 `pm-project-resume-pack.md`（PDF 可选）。

推荐模式是必填项。用户必须指定 `ai-product-only`、`b2b-only`、`mixed`、`safe-mode`、`vertical-mode` 中的一种；如果用户没有指定模式，先完整列出所有可选模式并反问，不要开始搜索或生成推荐。

## 必须遵守

- 用户每次初始化找项目、选项目或生成简历项目时，如果推荐模式缺失，必须先完整列出所有可选模式并反问，不能自行默认、推断或继续执行。
- 除非用户明确要求不要联网，否则要搜索当前 GitHub / Web 项目后再推荐。
- 优先推荐「有可体验的产品形态、可本地跑通或有官方 demo」的 Agent 产品；纯框架、SDK、工具库、prompt 集合、awesome list、纯爬虫一律不推荐。
- 「产品形态」不限于自带 Web UI：自带 UI / 桌面端 / 嵌入现有平台（微信、Telegram、Slack、Discord 等聊天机器人）/ API 服务 + 交互文档 / CLI 交互都算——判据是**用户能否端到端体验主流程、能否现场演示**，而不是有没有前端。无自带 UI 的项目必须在短名单中注明演示形态与演示成本，演示路径不清晰或演示成本过高（如需要自建完整前端）时降权或淘汰。
- **任何模式下，最终推荐必须通过 Agent 四件套校验（多轮上下文 / RAG / 工具调用 / 记忆，至少命中 2 项；ai-product-only 优先 ≥3 项）**；无 Agent 能力的普通 B 端工具（CRM、工单、BI、项目管理）不在任何模式的推荐范围内，只能作为宿主/底座背景；平台/构建器类（MaxKB、FastGPT、Dify 等）同样只能当底座，不得作为项目主体。
- 四件套校验是**必要非充分条件**：通过门槛只说明「不是纯 RAG 问答壳」，人工复核必须再问一句「除 RAG 问答之外还有什么」——工具编排 / 业务实体 / 人机协作至少具备一项，否则淘汰（脚本 `BEYOND_RAG_GATE` 已做关键词初筛，人工复核确认是否真实具备）。
- **B 端场景项目必须过「企业落地性」门槛**（详见 `筛选评分.md` 企业落地性门槛节）：不能在企业实际落地的（代操作企业系统的 computer-use/browser-use 类、纯个人工具定位的 local-first 类）一律淘汰（脚本 `ENTERPRISE_REDLINE` 初筛，人工按落地性四问复核——场景真实性 / ROI 可量化 / 合规安全 / 替代风险）。通用场景项目不做硬淘汰，但短名单必须标注企业落地约束并给出叙事调整建议。
- 不要推荐一眼就是「教程复刻 / 课程 demo」的项目（如 todo、chatgpt 套壳、单页 chat UI）；优先有真实业务场景、多角色权限、数据持久化的产品。
- 先构建多样化候选池（≥4 个分桶、≥6 组查询），再做最终选择；不把 star 数作为主要排序依据，1k+ star 即可入围，20k+ 不额外加分。
- 候选池阶段读取 README 前若干行做产品形态 probe（是否有 UI/demo/部署方式/业务场景），probe 只用于筛选和定位，不支撑最终「产品拆解 / 改造方案」。
- 拉取最终候选仓库前，必须先向用户展示 3-4 个短名单项目、每个项目的包装方向和主要淘汰理由，并等待用户确认；用户确认后才能执行 `references/pull_github_repos.py`。
- 最终入选项目必须经过 `references/pull_github_repos.py` 真实拉取到本地；未成功拉取（manifest 状态非 `cloned`）的项目不得进入最终推荐。
- 产品验证只能基于本地仓库目录（README/docs/部署配置/目录结构/issues 线索）+ 用户实际跑通情况；不得用模型记忆或网页摘要替代。
- 无法提取至少 5 个产品证据点的项目必须淘汰（证据点定义见 `执行流程.md` 第 10 步）。
- 必须区分「项目已有能力」「建议改造 / 0-1 叙事」「可写入简历」；未经用户确认已完成改造的内容，一律写成"完成改造后可写"，不得写成已有成果。
- 简历叙事必须体现责任层级：需求洞察 → 方案设计 → 推动落地 → 指标闭环，不得写成"参与了 / 了解了"。
- 默认使用中文输出，除非用户要求其他语言。

## 推荐模式

- `ai-product-only`：只推荐 AI Agent 产品（知识库问答 Agent、智能客服 Agent、ChatBI 问数 Agent、学习/面试/办公 Agent 等）。
- `b2b-only`：只推荐 B 端业务场景的 Agent 产品（智能客服、销售/SDR、招聘/HR、数据分析、运营/营销 Agent 等）；无 Agent 能力的传统 B 端工具一律不推荐。
- `mixed`：一个通用场景 Agent 产品 + 一个 B 端场景 Agent 产品，且两者不共用同一简历卖点。
- `safe-mode`：优先依赖少、Docker 一键起、文档清晰、7 天内能跑通并产出拆解 + PRD 的 Agent 产品。
- `vertical-mode`：优先能贴合用户自述的目标行业或岗位场景的 Agent 产品（行业与场景由用户输入指定，skill 不预设任何行业），包装方向为「垂直场景 AI 落地」。

## 缺少推荐模式时的反问话术

如果用户没有明确写出推荐模式，直接回复：

你想按哪种推荐模式执行？

- ai-product-only：只找通用场景的 AI Agent 产品（知识库问答、学习、面试、写作/办公 Agent）
- b2b-only：只找 B 端场景的 Agent 产品（智能客服、销售、招聘、数据分析 Agent）
- mixed：一个通用场景 Agent + 一个 B 端场景 Agent
- safe-mode：只推荐容易跑通、7 天能出拆解和 PRD 的 Agent 产品
- vertical-mode：优先贴合你的目标垂直行业场景的 Agent 产品

你回复其中一个模式后，我再开始搜索 GitHub 并生成简历叙事。

## 使用示例

### 快速使用

```
牛肉雷达产品版，推荐模式 mixed：一个通用场景 Agent 产品 + 一个 B 端场景 Agent 产品，帮我各找 1 个。
```

### 完整输入

```
牛肉雷达产品版，推荐模式 vertical-mode
目标岗位：AI 产品经理 / B 端产品经理（按用户实际填写）
垂直行业：由用户填写（如电商、教育、金融、医疗、制造等，可留空）
体验能力：会 Python，能本地 Docker 跑项目；不写生产级代码
时间预算：2 周
避开方向：纯框架、chatgpt 套壳、IoT、需要 GPU 集群的项目
输出需求：产品拆解 + PRD 大纲 + 0-1 改造路线 + 简历写法 + 面试问答
```

## 脚本执行方式

```bash
# 候选池搜索（离线自测加 --offline-sample；GitHub 限速时加大 --sleep、--readme-lines 0）
python references/search_pm_candidates.py --mode mixed --output pm-candidate-pool.json --shortlist-output pm-shortlist-preview.md

# 强制仓库拉取（用户确认短名单后）
python references/pull_github_repos.py --repo https://github.com/owner/repo --output-dir .repo-source-cache --manifest repo-source-manifest.json

# 可选：导出 PDF（需先 pip install reportlab；缺依赖时只交付 md，不算失败）
python references/markdown_to_pdf.py pm-project-resume-pack.md --output pm-project-resume-pack.pdf --title "PM 项目推荐报告"
```

## 参考资料加载

按任务需要加载，不要一次性加载所有资料：

- `references/执行流程.md`：项目选择任务必载。
- `references/用户输入模板.md`：用户需要模板、示例，或推荐模式缺失需要反问时加载。
- `references/筛选评分.md`：筛选、分桶、推荐模式打分时加载。
- `references/简历写法.md`：写简历条目和面试问题前加载。
- `references/输出模板.md`：生成最终 Markdown 文件前加载。
- `references/search_pm_candidates.py`：候选池搜索和短名单确认前优先执行。
- `references/pull_github_repos.py`：最终候选仓库验证前必须执行。
- `references/markdown_to_pdf.py`：可选。已安装 reportlab 或用户要求 PDF 时执行；缺依赖时保留 md 并提示安装命令。
- `references/规则索引.md`：只在需要查看文档映射关系时加载。

## 高层流程

1. 检查用户是否明确给出推荐模式；没有则停止并列出全部模式反问。
2. 提取用户画像：目标岗位、垂直行业、体验能力（能否跑 Docker / 调 API）、时间预算、避开方向、输出需求。
3. 运行 `references/search_pm_candidates.py` 建候选池（Agent 产品稀缺，目标 15-30 个仓库）。
4. 按 `筛选评分.md` 过滤和打分：先做三层判定（平台 / 框架 / 应用），再过 Agent 四件套门槛（≥2 项）和「除 RAG 外」门槛（工具编排 / 业务实体 / 人机协作 ≥1 项），再过产品完整度门槛（≥2 项）；B 端项目最后过企业落地性门槛（红线淘汰 + 落地性四问复核）；宿主平台与平台/构建器只能作底座，每桶保留前 3-5 个。
5. 输出 3-4 个短名单项目（含 Agent 四件套打勾情况、包装方向、选择理由、淘汰理由），等用户确认。
6. 用户确认后强制执行 `references/pull_github_repos.py`，只信 manifest 中 `status=cloned` 的仓库。
7. 产品体验验证：本地跑通或按部署文档评估可跑性，逐项核对 Agent 四件套，提取 ≥5 个产品证据点；不达标即淘汰。
8. 按 AI PM 面试三层标准对照（硬门槛 / 分水岭 / 加分项），标出每个项目的缺口与改造动作。
9. 按 `输出模板.md` 和 `简历写法.md` 生成 `pm-project-resume-pack.md`；PDF 仅在用户需要且 reportlab 可用时导出。

## 输出内容

默认在当前工作区生成：

- `pm-candidate-pool.json`：候选池原始记录（含初筛分与理由）
- `pm-shortlist-preview.md`：脚本生成的短名单预览
- `pm-project-shortlist.md`：人工复核后的短名单确认稿（含实证结论）
- `pm-project-resume-pack.md`：最终简历项目包
- `pm-project-resume-pack.pdf`：可选 PDF 版本（需 reportlab）
- `repo-source-manifest.json`：仓库拉取结果和状态记录

## 与原版（backend-agent-project-selector）的关系

- 继承：流程骨架（模式闸门 → 候选池 → 短名单确认 → 强制拉取 → 验证 → 简历包）、pull/pdf 两个通用脚本。
- 重写：分桶与查询词（Agent 场景视角）、筛选门槛（三层判定 + Agent 四件套 + 产品完整度，替代业务型 Agent 门槛）、验证方式（产品证据点替代源码证据点）、输出物（PRD 大纲 + 0-1 改造路线替代技术难点清单）。
- 原版文件零改动；本 skill 独立演进。

## 作者与出处

- 原版：程序员牛肉（backend-agent-project-selector / Beef Project Radar）
- 产品版：基于原版改编，面向产品经理求职场景
