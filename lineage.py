# -*- coding: utf-8 -*-
"""
演进链自动构建模块 —— Research Lineage Builder。

输入一篇论文（标题 + 摘要），自动构建「前置 → 当前 → 后续」的技术演进链。

流程：
1. LLM 判断这篇论文的前置工作（它建立在哪些关键论文之上）
2. OpenAlex 检索这些前置论文、以及引用当前论文的后续论文
3. LLM 综合，输出结构化的演进链（每一步的「问题 → 尝试 → 瓶颈 → 改进」）
"""

import json

import requests

import literature

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def _call(messages, api_key, json_mode=False, max_tokens=3000):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def infer_predecessors(title: str, abstract: str, api_key: str) -> list:
    """让 LLM 判断这篇论文的前置工作（关键前置论文标题列表）。"""
    system = (
        "你是科研史专家，擅长识别一篇论文的「前置工作」——它建立在哪些关键论文之上。"
        "只输出一个 JSON 数组，元素是论文标题字符串。"
    )
    user = (
        f"论文：《{title}》\n摘要：{abstract[:1500]}\n\n"
        f"请列出这篇论文最重要的 3~5 篇前置工作（技术依赖的关键论文），"
        f"要求：必须给出论文的**精确英文标题**（能在学术数据库里搜到的完整标题，不要泛泛的描述、不要用「某综述」「相关研究」这类模糊词）。"
        f"JSON 格式：[\"论文标题1\", \"论文标题2\", ...]"
    )
    content = _call(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        api_key, json_mode=True, max_tokens=800,
    )
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        # 某些情况 LLM 包了一层 {"papers": [...]}
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    except Exception:
        return []


def build_lineage(title: str, abstract: str, api_key: str) -> dict:
    """构建完整演进链，返回结构化的前置/当前/后续节点。"""
    # 1. LLM 判断前置
    predecessors = infer_predecessors(title, abstract, api_key)

    # 2. OpenAlex 检索前置论文详情（按标题精确搜，避免无关高被引论文）
    pred_nodes = []
    for name in predecessors[:5]:
        try:
            hits = literature.search_by_title(name, limit=1)
            if hits:
                pred_nodes.append(hits[0])
        except Exception:
            continue

    # 3. OpenAlex 检索当前论文（按标题精确搜）+ 后续论文
    cur = None
    try:
        hits = literature.search_by_title(title, limit=1)
        if hits:
            cur = hits[0]
    except Exception:
        pass

    cite_nodes = []
    if cur:
        try:
            cite_nodes = literature.get_citations(cur["id"], limit=5)
        except Exception:
            pass

    # 4. LLM 综合，输出结构化演进链
    lineage = synthesize(title, pred_nodes, cur, cite_nodes, api_key)
    return {"predecessors": pred_nodes, "current": cur, "citations": cite_nodes, "lineage": lineage}


def synthesize(title: str, pred_nodes: list, cur: dict, cite_nodes: list, api_key: str) -> str:
    """让 LLM 基于前置/当前/后续，写一段「问题→尝试→瓶颈→改进」的演进叙事。"""
    def fmt(n):
        return f"- {n['title']}（{n['year']}，被引 {n['cited_by_count']}）" if n else "- （无）"

    pred_txt = "\n".join(fmt(n) for n in pred_nodes) or "（未检索到）"
    cite_txt = "\n".join(fmt(n) for n in cite_nodes) or "（未检索到）"

    system = (
        "你是科研史叙事专家。请把一组论文串成一条清晰的技术演进链，"
        "用「问题 → 尝试 → 瓶颈 → 改进 → 新问题」的框架讲清楚：每一代方法解决了什么、又留下了什么瓶颈。"
        "不神化、不堆术语，用中文，控制在 400 字以内。"
    )
    user = (
        f"目标论文：《{title}》\n\n"
        f"它的前置工作：\n{pred_txt}\n\n"
        f"它被这些后续工作引用：\n{cite_txt}\n\n"
        f"请为这条演进链写一段连贯的叙事。"
    )
    return _call([{"role": "system", "content": system}, {"role": "user", "content": user}], api_key, max_tokens=1200)
