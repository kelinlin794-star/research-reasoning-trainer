# -*- coding: utf-8 -*-
"""
论文自动解析模块 —— 把任意 PDF 论文拆解成「科研训练数据」。

流程：提取 PDF 文本 → 调用 DeepSeek 大模型 → 输出结构化 JSON → 校验。
生成的 JSON 结构与 data/ 下的预置论文完全一致，可直接进入 7 步训练流程。
"""

import io
import json
import re

import requests
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# DeepSeek 配置（兼容 OpenAI 风格的 REST 调用）
# ---------------------------------------------------------------------------
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# ---------------------------------------------------------------------------
# 系统提示词：定义角色、原则、输出 JSON 结构
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是一位资深的科研方法解构专家，擅长把论文从「最终成品」还原成「问题解决的过程」。

## 三条铁律（必须遵守）
1. 不神化创作者：把创新还原成「面对约束 → 测量系统 → 发现瓶颈 → 提出方案」的工程决策，而不是天才灵光一现。
2. 不做术语堆砌：坚持「问题 → 需求 → 概念 → 方法」的逻辑链条，讲清为什么需要，而不是干巴巴下定义。
3. 严格证据分层：每条内容都要带 evidence 字段，取值只能是以下三种之一：
   - "stated"：论文明确陈述的内容
   - "reconstructed"：根据论文方法/实验合理重建的推断
   - "unknown"：论文未提及、无法确定的内容
   凡是推断都必须标 "reconstructed"，绝不允许假装读心作者的真实想法。

## 解释深度要求（面向没读过论文的读者）
- 所有专业术语在第一次出现时，用括号加一句简短的中文解释（例：roofline 模型（估算计算性能理论上限的工具））。
- 核心概念配一个生活化类比，帮读者建立直觉（例：kernel 就像 GPU 上执行的一小段任务）。
- 但绝不降低专业深度：关键数据、公式、工程决策链、论证逻辑必须完整保留。
- 目标：一个完全没读过这篇论文、也不熟悉该领域的人，读完后能理解「它解决了什么问题、怎么解决、为什么这么做」。

## 任务
阅读用户提供的论文全文，输出一个 JSON 对象（只输出 JSON 本身，不要任何解释文字、不要 markdown 代码块标记）。JSON 结构如下：

{
  "id": "英文短id",
  "meta": {
    "title": "论文标题",
    "subtitle": "一句话概括核心贡献",
    "authors": "作者",
    "affiliation": "机构",
    "year": 2025,
    "arxiv": "arXiv编号或空字符串",
    "field": "研究领域",
    "difficulty": "入门/进阶/专家",
    "tags": ["标签1", "标签2"]
  },
  "training": {
    "why_read": {"title": "为什么值得读", "intro": "引导语", "blocks": [{"evidence": "stated", "text": "内容"}]},
    "prior_work": {"title": "以前怎么解决", "intro": "引导语", "blocks": [{"evidence": "stated", "text": "内容"}]},
    "prior_limits": {"title": "为什么以前不够", "intro": "引导语", "blocks": [{"evidence": "stated", "text": "内容"}]},
    "position": {"title": "这篇论文处在哪", "intro": "引导语", "blocks": [{"evidence": "stated", "text": "内容"}]},
    "guess": {
      "title": "如果是你，你会怎么办", "intro": "引导语",
      "constraints": ["约束1", "约束2"],
      "scaffold": [{"id": "a", "text": "选项A", "correct": false, "why": "为什么不对"}]
    },
    "solution": {"title": "作者怎么解决", "intro": "引导语", "chain": [{"stage": "约束", "text": "内容"}], "blocks": [{"evidence": "stated", "text": "内容"}]},
    "experiment": {"title": "实验到底证明了什么", "intro": "引导语", "blocks": [{"evidence": "stated", "text": "内容"}]},
    "limitation": {
      "title": "还有什么问题", "intro": "引导语",
      "scaffold": [{"id": "a", "text": "可能的局限A", "valid": true, "why": "说明"}],
      "author_limitations": [{"evidence": "stated", "text": "论文自己承认的局限"}]
    },
    "future": {"title": "后续论文怎么继续", "intro": "引导语", "blocks": [{"evidence": "stated", "text": "内容"}]},
    "next_question": {"title": "下一个研究问题是什么", "intro": "引导语", "prompts": ["提示角度1"], "blocks": [{"evidence": "reconstructed", "text": "内容"}]}
  },
  "timeline_domain": [{"year": "时间", "title": "标题", "text": "内容", "evidence": "stated"}],
  "timeline_tech": [{"year": "时间", "title": "标题", "text": "内容", "evidence": "stated"}]
}

## 字段要点
- 前 4 步（why_read / prior_work / prior_limits / position）是「纵向定位」：讲清为什么读、历史方法、历史局限、本文位置，层层铺垫。
- guess.scaffold：给 3~4 个选项，只有 1 个 correct=true（作者真实路线），其余是易混淆的干扰项，每个选项都要有 why 说明。guess.constraints 只给「作者面对的约束」，绝不能泄露答案。
- solution.chain：还原「约束 → 测量 → 瓶颈 → 方案」的工程决策链（3~5 个环节），体现「不神化」原则；solution.blocks 具体讲方案。
- experiment 要讲清「证明了什么、又没证明什么」的边界。
- limitation.scaffold：给 3~4 个可能的局限，用 valid 标对错；author_limitations 是论文自己承认的局限。
- future：论文自己指出的后续工作与展望方向。
- next_question.prompts：给 2~4 个引导用户思考「下一个研究问题」的角度（基于论文的局限与未来方向）。
- timeline_domain：领域问题演进线，3~5 条；timeline_tech：技术演进线，3~5 条。
- 所有中文内容必须准确、具体、基于论文事实，杜绝空洞套话。""".strip()


# ---------------------------------------------------------------------------
# 语言风格（用户可选：纯中文 / 纯英文 / 中英结合）
# ---------------------------------------------------------------------------
STYLE_INSTRUCTIONS = {
    "zh": "语言风格：全部用简体中文表达。",
    "en": "Language style: write all content in natural, academic English.",
    "mixed": (
        "语言风格：采用「中英结合」的表达方式——专业术语、方法名、模型名、概念保留英文原文"
        "（如 VLA、roofline model、CUDA graph、flow matching、kernel），"
        "而叙述、解释、衔接用语用中文。类似香港学术圈自然的表达习惯，"
        "例如：「这篇 paper 的核心 contribution 是……」「作者用 CUDA graph 来 eliminate 掉 CPU 的 overhead」。"
    ),
}


# ---------------------------------------------------------------------------
# 文本提取
# ---------------------------------------------------------------------------
def extract_pdf_text(pdf_bytes: bytes) -> str:
    """从 PDF 字节流提取全文。"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t)
    return "\n\n".join(parts)


def build_user_prompt(text: str) -> str:
    """构造用户提示词，限制输入长度避免超上下文。"""
    max_chars = 60000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[论文过长，后续内容已截断]"
    return f"请把下面这篇论文拆解成训练数据（严格按 system 里给定的 JSON 结构输出）：\n\n<论文全文>\n{text}\n</论文全文>"


# ---------------------------------------------------------------------------
# JSON 清洗与校验
# ---------------------------------------------------------------------------
def strip_code_fence(s: str) -> str:
    """去掉 LLM 可能包裹的 markdown 代码块、定位到 JSON 主体。"""
    s = s.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]
    return s


def validate(data: dict):
    """校验解析结果是否包含训练流程所需的全部关键字段。"""
    required = ["meta", "training", "timeline_domain", "timeline_tech"]
    for k in required:
        if k not in data:
            raise ValueError(f"解析结果缺少字段：{k}")
    steps = ["why_read", "prior_work", "prior_limits", "position", "guess", "solution", "experiment", "limitation", "future", "next_question"]
    for s in steps:
        if s not in data["training"]:
            raise ValueError(f"训练数据缺少阶段：{s}")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def call_deepseek(system: str, user: str, api_key: str) -> str:
    resp = requests.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
            "max_tokens": 8192,
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def parse_paper(pdf_bytes: bytes, api_key: str, style: str = "mixed") -> dict:
    """把 PDF 论文拆解为训练数据字典。

    style: "zh" 纯中文 / "en" 纯英文 / "mixed" 中英结合（默认）。
    """
    text = extract_pdf_text(pdf_bytes)
    if len(text.strip()) < 200:
        raise ValueError("PDF 文本提取失败或内容过少。请确认是文字版 PDF（扫描图片版暂不支持）。")

    style_inst = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["mixed"])
    system = SYSTEM_PROMPT + "\n\n## 语言要求\n" + style_inst

    content = call_deepseek(system, build_user_prompt(text), api_key)
    data = json.loads(strip_code_fence(content))
    validate(data)
    data["_style"] = style
    return data


def restyle_paper(paper_data: dict, target_style: str, api_key: str) -> dict:
    """把已解析论文的所有文本内容改写成目标语言风格（无需重新上传 PDF）。

    保持 JSON 结构、字段名、evidence 枚举不变，只改写各文本字段的值。
    """
    style_inst = STYLE_INSTRUCTIONS.get(target_style, STYLE_INSTRUCTIONS["mixed"])

    payload = {k: v for k, v in paper_data.items() if k != "_style"}
    text = json.dumps(payload, ensure_ascii=False)

    system = (
        "你是语言风格改写专家。把下面这个 JSON 里所有「文本值」改写为指定的语言风格。"
        "必须保持：JSON 结构、所有字段名、以及 evidence 等枚举取值完全不变，只改写各文本字段的值。"
        "只输出改写后的 JSON，不要任何解释、不要 markdown 代码块。"
    )
    user = f"目标语言风格：{style_inst}\n\n原始 JSON：\n{text}"

    content = call_deepseek(system, user, api_key)
    data = json.loads(strip_code_fence(content))
    validate(data)
    data["_style"] = target_style
    return data
