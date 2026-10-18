# 牛肉雷达 · 产品经理版（pm-beef-radar）

一个装进 Agent 环境就能用的 Skill：从 GitHub 海量开源项目里，帮你筛出**能写进简历、讲得出企业落地**的 AI 产品经理项目方向。

> **参考项目**：本项目参考了「程序员牛肉」开源的「牛肉雷达」项目的整体思路，在它基础上做了产品经理求职场景的深度定制（门槛强化、企业落地性评估、评分校准等），感谢原项目带来的启发。

## 它解决什么问题

转型或求职中的产品经理需要「有真实产品体量的项目」做背书，直接去 GitHub 找会系统性踩三类坑：

| 坑 | 表现 | 后果 |
| --- | --- | --- |
| 平台 / 框架当主体 | 推的是 LLMOps 平台、Agent 框架、SDK | 面试一问「你负责什么」就露馅 |
| 同质化问答壳 | LLM + 知识库 + 聊天窗，凑齐三件套但没别的 | 讲不出除 RAG 外的增量 |
| 讲不出落地 | B 端方向却过不了企业安全评审 / 没有采购理由 | 「怎么落地」一问叙事崩塌 |

本 Skill 用**五道门槛 + 评分模型 + 强制源码验证**把这三类坑系统性排掉。

## 五种推荐模式

| 模式 | 用途 |
| --- | --- |
| `ai-product-only` | 只找通用场景 AI Agent（知识库问答、学习、面试、写作办公） |
| `b2b-only` | 只找 B 端场景 Agent（智能客服、销售、招聘、数据分析） |
| `mixed` | 一个通用 + 一个 B 端（默认推荐） |
| `safe-mode` | 依赖少、Docker 一键起、7 天能出产品拆解和 PRD |
| `vertical-mode` | 贴合你指定的垂直行业 |

## 五道筛选门槛

1. **三层判定**：平台 / 构建器只能当底座，框架淘汰，应用才可作项目主体；宿主平台（客服台、工单、BI 工具）不能单独作为 Agent 项目推荐
2. **Agent 四件套 ≥2 项**：多轮上下文 / RAG / 工具调用 / 记忆
3. **除 RAG 外增量 ≥1 项**：工具编排 / 业务实体（工单、订单、审批）/ 人机协作（转人工）——否则视为同质化问答壳淘汰
4. **产品完整度 ≥2 项**：可体验形态、真实业务场景、多用户权限、可部署落地等
5. **企业落地性门槛（B 端项目必查）**
   - 红线硬淘汰：代操作企业系统（computer-use / browser-use 类，权限 / 审计 / 责任归属过不了安全评审）、纯个人工具定位（local-first，企业没有采购理由）
   - 落地性四问人工复核：场景真实性 / ROI 可量化 / 合规安全 / 替代风险
   - 通用项目不做硬淘汰，但强制标注落地约束与叙事调整建议

关键词初筛与人工复核各司其职：脚本层面的判定均按「宁漏杀交人工复核，不误杀」设计（如 README 探测失败时红线不触发）。

## 工作流

```
输入模板收集需求（模式 / 岗位 / 行业 / 时间预算 / 避开方向）
  → search_pm_candidates.py 搜索候选池（GitHub Search API + README 探测）
  → 评分排序 + 五道门槛过滤（关键词初筛）
  → 短名单人工复核（含落地性四问）
  → pull_github_repos.py 强制拉取验证（未成功克隆不得进入推荐）
  → 体验验证 + 证据点提取（≥5 个）
  → 生成简历包（产品拆解 / PRD 大纲 / 0-1 改造路线 / 简历写法 / 面试问答）
```

## 快速开始

**安装**：把本仓库整体复制到你的 Agent skills 目录：

```
# Trae / WorkBuddy
C:\Users\<你>\.workbuddy\skills\pm-beef-radar
# Claude Code 等
~/.claude/skills/pm-beef-radar
```

**离线自测**（不消耗 GitHub 配额）：

```bash
python references/search_pm_candidates.py --mode mixed --offline-sample \
  --output out.json --shortlist-output out.md
```

**真实搜索**（建议配置 token：匿名核心接口仅 60 次/小时，README 探测极易限流，配 token 后为 5000 次/小时）：

```bash
export GITHUB_TOKEN=ghp_xxx   # Windows PowerShell: $env:GITHUB_TOKEN='ghp_xxx'
python references/search_pm_candidates.py --mode mixed \
  --output pm-candidate-pool.json --shortlist-output pm-shortlist.md
```

评分规则、模式语义、输出格式详见 [references/](references/) 目录（筛选评分.md、执行流程.md、用户输入模板.md、输出模板.md、简历写法.md、规则索引.md）。

## 目录结构

```
SKILL.md                        Skill 入口（Agent 读取）
references/
  search_pm_candidates.py       候选池搜索 + 评分 + 五道门槛过滤
  pull_github_repos.py          强制源码验证（克隆 + manifest）
  markdown_to_pdf.py            报告导出（可选，需 reportlab）
  筛选评分.md / 执行流程.md / 用户输入模板.md / 输出模板.md / 简历写法.md / 规则索引.md
```

## 参考项目与致谢

本项目参考了「程序员牛肉」开源的「牛肉雷达」项目的整体思路，在其基础上做了产品经理求职场景的深度定制，感谢原项目的启发。

## 许可

本仓库全部内容以 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)（知识共享署名-非商业性使用 4.0 国际）许可发布：

- ✅ 个人学习、修改、非商业分发（保留署名）
- ❌ 未经另行书面授权，不得用于任何商业用途
