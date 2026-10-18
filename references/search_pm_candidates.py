#!/usr/bin/env python3
"""Search GitHub repositories and build a candidate pool for PM-style project packaging.

PM version of the backend search helper. It finds open-source products that a
product manager can run locally (or via demo), dissect as a product, and
re-package as a 0-1 resume project with a PRD / improvement roadmap.

Dependency-free. Examples:
    python pm-beef-radar/references/search_pm_candidates.py \
        --mode ai-product-only --output pm-candidate-pool.json \
        --shortlist-output pm-shortlist-preview.md
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_REPO_URL = "https://api.github.com/repos/{full_name}"


@dataclass(frozen=True)
class BucketQuery:
    bucket: str
    query: str


AI_PRODUCT_QUERIES = [
    BucketQuery("知识库/RAG问答", "rag knowledge base chatbot stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("知识库/RAG问答", "topic:rag topic:knowledge-base stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("智能客服", "customer support chatbot llm self-hosted stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("数据问数/ChatBI", "chatbi natural language sql llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("数据问数/ChatBI", "data analysis assistant llm dashboard stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("AI学习/教育", "ai tutor learning assistant llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("AI学习/教育", "topic:education topic:ai stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("AI办公/写作", "ai writing assistant self-hosted stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("AI面试/招聘", "ai interview assistant llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("多智能体工作台", "multi-agent workflow app ui stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("投研/金融助手", "investment research assistant llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("内容生成/营销", "ai content generation marketing self-hosted stars:{stars} pushed:>{pushed_after}"),
]

B2B_AGENT_QUERIES = [
    BucketQuery("智能客服 Agent", "customer support ai agent stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("智能客服 Agent", "support chatbot rag llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("销售/SDR Agent", "ai sales agent llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("招聘/HR Agent", "ai recruiting hiring agent llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("数据分析 Agent", "data analysis agent llm sql stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("数据分析 Agent", "chatbi text-to-sql llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("运营/营销 Agent", "marketing automation agent llm stars:{stars} pushed:>{pushed_after}"),
    BucketQuery("企业知识 Agent", "enterprise knowledge assistant agent rag stars:{stars} pushed:>{pushed_after}"),
]

# B 端桶名集合：候选的所有分桶都落在这里面时，按 B 端项目执行企业落地性门槛
B2B_BUCKETS = {q.bucket for q in B2B_AGENT_QUERIES}
# 「数据问数/ChatBI」查询挂在通用桶（AI_PRODUCT_QUERIES）下，但按 筛选评分.md 的分桶定义
# ChatBI 属 B 端场景，落地性判定时一并计入 B 端。
B2B_CLASSIFY_BUCKETS = B2B_BUCKETS | {"数据问数/ChatBI"}


AI_PRODUCT_INCLUDE = {
    "rag", "knowledge", "chatbot", "assistant", "agent", "tutor", "learning",
    "customer support", "analytics", "bi", "chatbi", "sql", "writing",
    "interview", "research", "marketing", "content", "copilot", "qa",
    "graphrag", "text2sql", "text to sql", "nl2sql",
}

B2B_AGENT_INCLUDE = {
    "agent", "agents", "assistant", "copilot", "chatbot", "rag",
    "customer support", "sales", "sdr", "recruiting", "recruitment",
    "hiring", "hr", "data analysis", "chatbi", "sql", "marketing",
    "knowledge", "workflow",
}

# sorted 保证打分理由顺序稳定
ALL_AGENT_INCLUDE = sorted(AI_PRODUCT_INCLUDE | B2B_AGENT_INCLUDE)

PRODUCT_GATE = {
    "产品形态可体验": {
        "ui", "web ui", "webui", "web app", "dashboard", "frontend", "interface", "admin",
        "workspace", "console", "editor", "app", "bot", "telegram",
        "discord", "slack", "whatsapp", "weixin", "wechat", "api",
    },
    "可体验": {
        "demo", "live demo", "hosted", "try online", "screenshots",
        "preview", "sandbox", "playground",
    },
    "业务场景": {
        "education", "learning", "customer", "support", "crm", "hr",
        "recruitment", "interview", "analytics", "report", "knowledge base",
        "writing", "office", "marketing", "ecommerce", "sales", "finance",
    },
    "多用户/权限": {
        "auth", "authentication", "oauth", "sso", "login", "user management",
        "admin", "rbac", "team", "workspace", "multi-tenant", "permission", "role",
    },
    "可部署落地": {
        "docker", "docker-compose", "deploy", "deployment", "self-hosted", "installation",
        "quickstart", "one-click", "helm", "vercel", "kubernetes",
    },
}

AGENT_GATE = {
    "多轮上下文": {
        "multi-turn", "chat history", "context window",
        "follow-up", "conversation", "conversational", "chat", "chatbot",
    },
    "RAG": {
        "rag", "graphrag", "retrieval", "knowledge base", "vector", "embedding",
        "rerank", "reranker", "reranking", "citation", "cite",
    },
    "工具调用": {
        "tool calling", "tool use", "tools", "function calling", "mcp", "plugin",
        "computer-use", "browser-use", "web search", "code execution",
    },
    "记忆": {
        "memory", "memories", "long-term", "personalization", "profile", "preference",
    },
}

# 「除 RAG 问答之外还有什么」：四件套之外的第三道门槛，至少命中一组
BEYOND_RAG_GATE = {
    "工具编排": AGENT_GATE["工具调用"] | {
        "workflow", "orchestration", "automation", "multi-agent", "webhook",
        "工具调用", "插件", "工作流",
    },
    "业务实体": {
        "ticket", "orders", "order management", "approval", "invoice", "inbox",
        "appointment", "booking", "candidates", "resume screening", "student",
        "courses", "sales pipeline", "工单", "订单", "审批", "坐席",
    },
    "人机协作": {
        "human handoff", "handoff", "human-in-the-loop", "hitl", "escalation",
        "human review", "human agent", "transfer to human", "转人工", "人工客服",
    },
}

HOST_PLATFORM_SIGNALS = {
    "helpdesk", "ticketing", "ticket system", "crm", "erp",
    "project management", "wiki", "bi dashboard", "inventory",
    "ecommerce platform", "online store", "blog cms",
}

PLATFORM_SIGNALS = {
    "builder", "platform", "studio", "low-code", "llmops",
    "workflow builder", "orchestration platform", "agent platform",
    "application builder", "build ai",
}

# safe-mode：一周内能跑通并产出优先——部署轻的加分，重基础设施的降权
SAFE_MODE_BOOST = {
    "docker", "docker-compose", "one-click", "quickstart", "self-hosted",
    "deployment", "installation", "setup guide", "一键部署",
}

SAFE_MODE_PENALTY = {
    "gpu", "cuda", "vllm", "k8s", "kubernetes", "helm", "cluster",
    "multi-model", "multi model", "distributed",
}

# 企业落地性红线：B 端场景项目命中即淘汰（不能在企业内实际部署使用）。
# 判定只做排除性初筛——README 未探测到时红线自然不触发，宁可漏杀交人工复核，不误杀。
ENTERPRISE_REDLINE = {
    "代操作企业系统": {
        # 要拿账号在企业系统上代执行操作，权限/审计/责任归属三道关过不了安全评审
        "computer-use", "browser-use", "operate your computer",
        "control your browser", "operate the browser",
    },
    "纯个人工具定位": {
        # 本地优先/个人工具：数据不落中心、无协同无权限无审计，企业没有采购理由
        "local-first", "personal knowledge", "personal notes",
        "personal use", "desktop pet",
    },
}

# B 端业务场景信号：与查询桶双重确认，防止 B 端桶捞出「个人助手」类项目被误按 B 端硬淘汰
B2B_SCENARIO_SIGNALS = {
    "customer support", "customer service", "helpdesk", "ticket", "ticketing",
    "sales", "sdr", "recruiting", "recruitment", "hiring", "hr", "crm",
    "enterprise", "b2b", "saas", "工单", "客服", "坐席",
}

COMMON_EXCLUDE = {
    "awesome",
    "tutorial",
    "template",
    "boilerplate",
    "starter",
    "example",
    "demo-only",
    "ui kit",
    "component library",
    "theme",
    "sdk",
    "wrapper",
    "prompt collection",
    "awesome list",
}

AI_PRODUCT_EXCLUDE = {
    "framework",
    "library",
    "toolkit",
    "llm framework",
    "orchestration framework",
    "research paper",
    "benchmark only",
}

B2B_EXCLUDE = {
    "iot",
    "embedded",
    "firmware",
    "hardware",
    "game",
    "scraper",
    "crawler only",
}


def build_queries(mode: str, min_stars: int, max_stars: int, pushed_after: str) -> list[BucketQuery]:
    star_range = f"{min_stars}..{max_stars}"
    if mode == "ai-product-only":
        source = AI_PRODUCT_QUERIES
    elif mode == "b2b-only":
        source = B2B_AGENT_QUERIES
    elif mode == "mixed":
        source = AI_PRODUCT_QUERIES[:7] + B2B_AGENT_QUERIES[:5]
    elif mode == "vertical-mode":
        source = AI_PRODUCT_QUERIES[:5] + B2B_AGENT_QUERIES[:7]
    else:
        source = AI_PRODUCT_QUERIES + B2B_AGENT_QUERIES
    return [
        BucketQuery(item.bucket, item.query.format(stars=star_range, pushed_after=pushed_after))
        for item in source
    ]


def repo_text(repo: dict, include_readme: bool = True) -> str:
    values = [
        repo.get("full_name", ""),
        repo.get("description") or "",
        repo.get("language") or "",
        " ".join(repo.get("topics") or []),
    ]
    if include_readme:
        values.append(repo.get("readme_probe") or "")
    return " ".join(values).lower()


@lru_cache(maxsize=None)
def keyword_pattern(keyword: str) -> re.Pattern[str]:
    # 整词匹配：避免 erp 命中 enterprise、hr 命中 graphrag、ui 命中 build；
    # 词内空格/连字符/下划线互通（multi-turn = multi turn = multi_turn），允许复数 s/es
    parts = [re.escape(part) for part in re.split(r"[\s\-_]+", keyword) if part]
    body = r"[\s\-_]+".join(parts)
    return re.compile(r"(?<![a-z0-9])" + body + r"(?:s|es)?(?![a-z0-9])")


def has_keyword(text: str, keyword: str) -> bool:
    return keyword_pattern(keyword).search(text) is not None


def matched_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    return [keyword for keyword in sorted(keywords) if has_keyword(text, keyword)]


def count_hits(text: str, gate: dict[str, set[str]]) -> tuple[int, list[str]]:
    hits = [name for name, keywords in gate.items() if matched_keywords(text, keywords)]
    return len(hits), hits


def count_gate_hits(text: str) -> tuple[int, list[str]]:
    return count_hits(text, PRODUCT_GATE)


def count_agent_hits(text: str) -> tuple[int, list[str]]:
    return count_hits(text, AGENT_GATE)


def count_beyond_rag_hits(text: str) -> tuple[int, list[str]]:
    return count_hits(text, BEYOND_RAG_GATE)


def is_host_platform(text: str) -> bool:
    return bool(matched_keywords(text, HOST_PLATFORM_SIGNALS))


def is_b2b_project(repo: dict) -> bool:
    # B 端判定 = 所有分桶均来自 B 端查询桶 + 文本含 B 端业务场景信号，双重确认：
    # B 端桶偶尔捞出「个人助手」类项目（如 computer-use 个人助手），按通用处理只标注落地约束；
    # 跨桶项目（mixed 下同命中通用桶）同样按通用处理。宁可漏杀交人工复核，不误杀。
    buckets = set(repo.get("buckets") or [])
    if not buckets or not buckets <= B2B_CLASSIFY_BUCKETS:
        return False
    return bool(matched_keywords(repo_text(repo), B2B_SCENARIO_SIGNALS))


def enterprise_redline_hits(repo: dict) -> dict[str, list[str]]:
    text = repo_text(repo)
    return {
        name: matched_keywords(text, keywords)
        for name, keywords in ENTERPRISE_REDLINE.items()
    }


def mode_exclude(mode: str) -> set[str]:
    if mode == "ai-product-only":
        return AI_PRODUCT_EXCLUDE
    if mode == "b2b-only":
        return B2B_EXCLUDE
    return set()


def score_repo(repo: dict, mode: str) -> tuple[int, list[str]]:
    text = repo_text(repo)

    score = 0
    reasons: list[str] = []
    for word in matched_keywords(text, ALL_AGENT_INCLUDE):
        score += 2
        reasons.append(f"命中产品关键词:{word}")
    # README 里的排除词只降权，不淘汰（硬淘汰见 is_filtered，只看名称/描述/topics）
    for word in matched_keywords(text, COMMON_EXCLUDE | mode_exclude(mode)):
        score -= 4
        reasons.append(f"降权/排除关键词:{word}")

    gate_count, gate_hits = count_gate_hits(text)
    if gate_count >= 3:
        score += gate_count * 2
        reasons.append(f"产品完整度门槛:{'/'.join(gate_hits[:4])}")
    elif mode in ("ai-product-only", "b2b-only"):
        score -= 6
        reasons.append(f"产品完整度不足:{gate_count}/3")

    agent_count, agent_hits = count_agent_hits(text)
    if agent_count >= 2:
        score += agent_count * 3
        reasons.append(f"Agent能力:{'/'.join(agent_hits[:4])}")
    else:
        score -= 8
        reasons.append(f"Agent能力不足:{agent_count}/2")
    beyond_count, beyond_hits = count_beyond_rag_hits(text)
    if beyond_count:
        score += beyond_count * 2
        reasons.append(f"除RAG外:{'/'.join(beyond_hits)}")
    else:
        reasons.append("除RAG外:无(工具编排/业务实体/人机协作均未命中)")
    if is_host_platform(text) and agent_count < 2:
        score -= 6
        reasons.append("疑似宿主平台(客服台/工单/CRM/BI)")
    # 任何模式下平台/构建器都只能作底座
    platform_hits = matched_keywords(text, PLATFORM_SIGNALS)
    if platform_hits:
        score -= 5
        reasons.append(f"疑似平台/构建器(仅可作底座):{'/'.join(platform_hits[:2])}")

    if mode == "vertical-mode":
        reasons.append("垂直模式:需人工补充行业关键词匹配评估")
    if mode == "safe-mode":
        boost = matched_keywords(text, SAFE_MODE_BOOST)
        penal = matched_keywords(text, SAFE_MODE_PENALTY)
        if boost:
            score += 3
            reasons.append(f"safe-mode易跑通:{'/'.join(boost[:3])}")
        if penal:
            score -= 4
            reasons.append(f"safe-mode重基础设施(降权):{'/'.join(penal[:3])}")
    # 企业落地性：B 端项目命中红线会在 is_filtered 淘汰，此处留降权理由兜底；
    # 通用项目不淘汰，但必须标注落地约束（如 computer-use 类要换安全边界叙事）
    for name, hits in enterprise_redline_hits(repo).items():
        if not hits:
            continue
        if is_b2b_project(repo):
            score -= 8
            reasons.append(f"企业落地性红线(B端):{name}:{'/'.join(hits[:2])}")
        else:
            reasons.append(f"企业落地约束(通用,需换叙事):{name}:{'/'.join(hits[:2])}")

    stars = int(repo.get("stars") or 0)
    if stars >= 1000:
        score += 2
        reasons.append("1k+ star 社区验证")
    if stars > 20000:
        score -= 1
        reasons.append("过热项目轻微降权")

    description = repo.get("description") or ""
    if 20 <= len(description) <= 220:
        score += 1
        reasons.append("描述信息较完整")

    return score, reasons


def is_filtered(repo: dict, mode: str) -> tuple[bool, str]:
    text = repo_text(repo)
    # 硬淘汰只看名称/描述/topics：README 里 "for example"、"theme" 太常见，误杀风险高
    head_text = repo_text(repo, include_readme=False)
    for word in matched_keywords(head_text, COMMON_EXCLUDE):
        return True, f"硬排除关键词: {word}"
    if mode == "ai-product-only":
        for word in matched_keywords(head_text, AI_PRODUCT_EXCLUDE):
            return True, f"纯框架/库,不适合PM包装: {word}"
    if mode == "b2b-only":
        for word in matched_keywords(head_text, B2B_EXCLUDE):
            return True, f"方向冲突: {word}"
    gate_count, gate_hits = count_gate_hits(text)
    if gate_count < 2:
        return True, f"产品完整度门槛不足: {gate_count}/2 ({'/'.join(gate_hits) or '无'})"
    agent_count, agent_hits = count_agent_hits(text)
    if agent_count < 2:
        return True, f"Agent能力门槛不足: {agent_count}/2 ({'/'.join(agent_hits) or '无'})"
    if is_host_platform(text) and agent_count < 3:
        return True, "疑似宿主平台(客服台/工单/CRM/BI)，Agent能力不足3项，不作Agent项目推荐"
    beyond_count, _ = count_beyond_rag_hits(text)
    if beyond_count == 0:
        return True, "除RAG外无增量: 工具编排/业务实体/人机协作均未命中，属于「LLM+知识库+聊天窗」同质化类型"
    # 企业落地性红线（仅 B 端项目）：不能在企业实际落地的形态直接淘汰。
    # 红线判定是排除性的——README 未探测到时不会误杀，漏掉的交人工复核（见 筛选评分.md 企业落地性门槛）。
    if is_b2b_project(repo):
        for name, hits in enterprise_redline_hits(repo).items():
            if hits:
                return True, (
                    f"企业落地性红线({name}): {'/'.join(hits[:3])}"
                    "——B 端项目不能在企业实际落地，排除（脚本初筛，人工复核确认）"
                )
    return False, ""


def github_get(url: str, token: str | None, timeout: int) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pm-beef-radar",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_readme_probe(full_name: str, token: str | None, timeout: int, max_lines: int) -> tuple[str, str]:
    url = f"{GITHUB_REPO_URL.format(full_name=full_name)}/readme"
    try:
        payload = github_get(url, token, timeout)
        content = payload.get("content") or ""
        encoding = payload.get("encoding") or ""
        if encoding != "base64" or not content:
            return "", "README empty or unsupported encoding"
        raw = base64.b64decode(content, validate=False)
        text = raw.decode("utf-8", errors="ignore")
        lines = text.splitlines()[:max_lines]
        return "\n".join(lines), f"README probe {len(lines)} lines"
    except Exception as exc:  # noqa: BLE001 - README probe is best-effort
        return "", f"README probe failed: {exc}"


def search_repositories(
    queries: Iterable[BucketQuery],
    per_query: int,
    token: str | None,
    sleep_seconds: float,
    timeout: int,
    readme_lines: int,
) -> list[dict]:
    seen: dict[str, dict] = {}
    for item in queries:
        params = urllib.parse.urlencode(
            {"q": item.query, "sort": "updated", "order": "desc", "per_page": per_query}
        )
        url = f"{GITHUB_SEARCH_URL}?{params}"
        try:
            payload = github_get(url, token, timeout)
        except Exception as exc:  # noqa: BLE001 - keep searching remaining buckets
            print(f"QUERY_FAILED bucket={item.bucket!r} query={item.query!r} error={exc}", file=sys.stderr)
            time.sleep(sleep_seconds)
            continue

        total = payload.get("total_count", 0)
        print(f"QUERY bucket={item.bucket} total={total} query={item.query}")
        for raw in payload.get("items", []):
            full_name = raw.get("full_name", "")
            if not full_name:
                continue
            record = seen.setdefault(
                full_name,
                {
                    "full_name": full_name,
                    "url": raw.get("html_url"),
                    "stars": raw.get("stargazers_count", 0),
                    "language": raw.get("language"),
                    "pushed_at": raw.get("pushed_at"),
                    "description": raw.get("description"),
                    "topics": raw.get("topics", [])[:16],
                    "readme_probe": "",
                    "readme_probe_status": "not probed",
                    "buckets": [],
                    "queries": [],
                },
            )
            if item.bucket not in record["buckets"]:
                record["buckets"].append(item.bucket)
            record["queries"].append(item.query)
        time.sleep(sleep_seconds)
    if readme_lines > 0:
        for record in seen.values():
            full_name = record.get("full_name") or ""
            probe, status = fetch_readme_probe(full_name, token, timeout, readme_lines)
            record["readme_probe"] = probe
            record["readme_probe_status"] = status
            time.sleep(max(0.05, sleep_seconds / 3))
    return list(seen.values())


def enrich(records: list[dict], mode: str) -> list[dict]:
    enriched = []
    for record in records:
        filtered, filter_reason = is_filtered(record, mode)
        score, reasons = score_repo(record, mode)
        copy = dict(record)
        copy["score"] = score
        copy["filtered"] = filtered
        copy["filter_reason"] = filter_reason
        copy["score_reasons"] = reasons
        copy["bucket"] = " / ".join(copy.get("buckets") or [])
        enriched.append(copy)
    enriched.sort(key=lambda item: (item["filtered"], -item["score"], item.get("full_name", "")))
    return enriched


def pick_shortlist(records: list[dict], limit: int) -> list[dict]:
    shortlist: list[dict] = []
    used_buckets: set[str] = set()
    for record in records:
        if record.get("filtered"):
            continue
        buckets = record.get("buckets") or [record.get("bucket", "")]
        if any(bucket not in used_buckets for bucket in buckets) or len(shortlist) >= len(used_buckets):
            shortlist.append(record)
            used_buckets.update(buckets)
        if len(shortlist) >= limit:
            break
    if len(shortlist) < limit:
        chosen = {item["full_name"] for item in shortlist}
        for record in records:
            if record.get("filtered") or record["full_name"] in chosen:
                continue
            shortlist.append(record)
            if len(shortlist) >= limit:
                break
    return shortlist


def markdown_preview(mode: str, records: list[dict], shortlist: list[dict], output: Path) -> None:
    filtered = [record for record in records if record.get("filtered")]
    lines = [
        "# GitHub 项目短名单确认（PM 产品版）",
        "",
        f"> 生成时间：{datetime.now(UTC).isoformat()}",
        f"> 推荐模式：{mode}",
        "",
        "## 建议深入体验的短名单",
        "",
        "| 项目 | 链接 | 分桶 | 语言 | Star | 初筛分 | 选择理由 |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in shortlist:
        reasons = "；".join(item.get("score_reasons") or [])
        lines.append(
            f"| {item['full_name']} | {item.get('url')} | {item.get('bucket')} | "
            f"{item.get('language') or ''} | {item.get('stars') or 0} | {item.get('score')} | {reasons} |"
        )

    lines.extend(
        [
            "",
            "## 初筛淘汰样例",
            "",
            "| 项目 | 链接 | 分桶 | 淘汰 / 降权理由 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in filtered[:20]:
        lines.append(
            f"| {item['full_name']} | {item.get('url')} | {item.get('bucket')} | {item.get('filter_reason')} |"
        )

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "请先确认短名单方向；确认后再运行 `pull_github_repos.py` 拉取仓库，并完成产品体验验证（本地跑通或读部署文档 + 提取 ≥5 个产品证据点）。",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search GitHub and build a PM packaging candidate pool.")
    parser.add_argument(
        "--mode",
        choices=["ai-product-only", "b2b-only", "mixed", "safe-mode", "vertical-mode"],
        required=True,
        help="Recommendation mode used to choose query buckets and filters.",
    )
    parser.add_argument("--output", type=Path, default=Path("pm-candidate-pool.json"))
    parser.add_argument("--shortlist-output", type=Path, default=Path("pm-shortlist-preview.md"))
    parser.add_argument("--shortlist", type=int, default=4, help="Number of repos to preview before cloning.")
    parser.add_argument("--per-query", type=int, default=10, help="GitHub results per query. Max recommended: 20.")
    parser.add_argument("--min-stars", type=int, default=500)
    parser.add_argument("--max-stars", type=int, default=50000)
    parser.add_argument("--pushed-after", default="2025-01-01")
    parser.add_argument("--sleep", type=float, default=1.2, help="Delay between GitHub API requests.")
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument(
        "--readme-lines",
        type=int,
        default=260,
        help="Fetch and score the first N README lines for stronger project-type filtering. Use 0 to disable.",
    )
    parser.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable containing GitHub token.")
    parser.add_argument(
        "--offline-sample",
        action="store_true",
        help="Do not call GitHub; write a small deterministic sample for script validation.",
    )
    return parser.parse_args()


def offline_records(mode: str) -> list[dict]:
    if mode in ("ai-product-only", "mixed"):
        return [
            {
                "full_name": "sample/ai-knowledge-base",
                "url": "https://github.com/sample/ai-knowledge-base",
                "stars": 2400,
                "language": "TypeScript",
                "pushed_at": "2026-01-01T00:00:00Z",
                "description": "Self-hosted RAG knowledge base web app with team workspaces, admin roles, docker deploy and live demo screenshots",
                "topics": ["rag", "knowledge-base", "self-hosted"],
                "readme_probe": "Web UI workspace. Upload documents, chat with citations. Agent can call MCP tools for web search; low-confidence answers go to human review. Auth with roles, admin panel. Docker compose deploy, live demo available.",
                "readme_probe_status": "offline sample",
                "buckets": ["知识库/RAG问答"],
                "queries": [],
            },
            {
                "full_name": "sample/helpdesk-platform",
                "url": "https://github.com/sample/helpdesk-platform",
                "stars": 5200,
                "language": "Ruby",
                "pushed_at": "2026-01-01T00:00:00Z",
                "description": "Self-hosted helpdesk ticketing platform for customer support teams with agent roles and dashboard",
                "topics": ["helpdesk", "ticketing", "self-hosted"],
                "readme_probe": "Unified inbox for email and chat. Ticket assignment, teams, admin dashboard, docker deploy. AI assistant add-on is paid.",
                "readme_probe_status": "offline sample",
                "buckets": ["工单客服"],
                "queries": [],
            },
            {
                "full_name": "sample/llm-framework-lib",
                "url": "https://github.com/sample/llm-framework-lib",
                "stars": 8000,
                "language": "Python",
                "pushed_at": "2026-01-01T00:00:00Z",
                "description": "Lightweight LLM orchestration framework library for building pipelines",
                "topics": ["framework", "llm"],
                "readme_probe": "Framework library, pip install. No UI, no demo, no business scenario.",
                "readme_probe_status": "offline sample",
                "buckets": ["多智能体工作台"],
                "queries": [],
            },
        ]
    return [
        {
            "full_name": "sample/support-agent-app",
            "url": "https://github.com/sample/support-agent-app",
            "stars": 1500,
            "language": "Python",
            "pushed_at": "2026-01-01T00:00:00Z",
            "description": "AI customer support agent app with rag knowledge base, multi-turn conversation, tool calling for ticket lookup and human handoff",
            "topics": ["ai-agent", "customer-support", "rag"],
            "readme_probe": "Support agent web app. Multi-turn chat with context, RAG over docs, tools to query tickets and orders, human handoff rules. Docker deploy, live demo screenshots.",
            "readme_probe_status": "offline sample",
            "buckets": ["智能客服 Agent"],
            "queries": [],
        },
        {
            "full_name": "sample/scraper-tool",
            "url": "https://github.com/sample/scraper-tool",
            "stars": 3000,
            "language": "Python",
            "pushed_at": "2026-01-01T00:00:00Z",
            "description": "Fast web scraper crawler toolkit",
            "topics": ["scraper", "crawler"],
            "readme_probe": "Crawler library, CLI only. No UI, no business scenario.",
            "readme_probe_status": "offline sample",
            "buckets": ["运营/营销 Agent"],
            "queries": [],
        },
    ]


def main() -> int:
    args = parse_args()
    if args.offline_sample:
        records = offline_records(args.mode)
    else:
        token = os.getenv(args.token_env)
        queries = build_queries(args.mode, args.min_stars, args.max_stars, args.pushed_after)
        records = search_repositories(
            queries,
            args.per_query,
            token,
            args.sleep,
            args.timeout,
            args.readme_lines,
        )

    enriched = enrich(records, args.mode)
    shortlist = pick_shortlist(enriched, args.shortlist)
    args.output.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_preview(args.mode, enriched, shortlist, args.shortlist_output)
    print(f"CANDIDATES: {args.output.resolve()} ({len(enriched)} repos)")
    print(f"SHORTLIST: {args.shortlist_output.resolve()} ({len(shortlist)} repos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
