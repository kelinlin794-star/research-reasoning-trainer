# -*- coding: utf-8 -*-
"""
对话式科研教练 Agent —— 统一入口，LLM 自主决策。

这是整个产品从「多页面工具」升级成「一个连贯 Agent」的核心：
- 用户上传 PDF 或直接说目标，都从对话开始；
- Agent 手上有论文的完整解析，根据对话历史自主决定下一步（引导训练 / 解释概念 / 追问 / 构建演进链）；
- 所有能力（解析、演进链、10 步训练、点评）都变成它可调用的技能。
"""

import json

import requests

import lineage

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def _call(messages, api_key, max_tokens=1500, temperature=0.6):
    resp = requests.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def build_coach_context(paper: dict) -> str:
    """把论文的完整解析，压缩成教练「脑子里」的背景知识（10 步要点）。"""
    t = paper.get("training", {})
    meta = paper.get("meta", {})

    def brief(step_id, n=2):
        blocks = t.get(step_id, {}).get("blocks", [])
        return "；".join(b.get("text", "") for b in blocks[:n])

    parts = [
        f"论文标题：{meta.get('title', '')}",
        f"一句话贡献：{meta.get('subtitle', '')}",
        f"为什么值得读：{brief('why_read')}",
        f"以前怎么解决：{brief('prior_work')}",
        f"以前为什么不够：{brief('prior_limits')}",
        f"它在演进中的位置：{brief('position')}",
        f"作者的真实方案：{brief('solution', 3)}",
        f"实验证明了什么：{brief('experiment', 2)}",
        f"它自己承认的局限：{brief('limitation', 2)}",
        f"后续工作方向：{brief('future')}",
    ]
    return "\n".join(parts)


COACH_SYSTEM = (
    "你是一位科研思维教练，陪一个科研新手深入理解一篇论文。"
    "你的原则：\n"
    "1. 不直接灌输答案，用「问题→需求→概念→方法」引导对方思考，先让他猜，再揭晓。\n"
    "2. 苏格拉底式追问：对方回答后，点出亮点和盲点，再追一个更深的问题。\n"
    "3. 一次只推进一小步，不要一次性把论文全部讲完。\n"
    "4. 如果对方提到「前置/演进/历史/来龙去脉」，先检索文献构建演进链，再讲解。\n"
    "5. 中文回答，控制在 200 字以内，语气温和但一针见血。\n\n"
    "你可以引导对方走这条思考链：为什么值得读 → 以前怎么解决 → 为什么不够 → 这篇处在哪 "
    "→ 如果是你会怎么办（先猜）→ 作者怎么解决 → 实验证明了什么 → 还有什么问题 → 后续怎么继续 → 你自己的下一个研究问题。"
)


AGENT_STYLE = {
    "zh": "用简体中文回答。",
    "en": "Answer in natural, academic English.",
    "mixed": "用「中英结合」的方式回答：专业术语保留英文（如 VLA、roofline、CUDA graph），叙述和衔接用中文。",
}


def coach_reply(paper: dict, current_step_id: str, history: list, api_key: str) -> str:
    """教练答疑：用户在 10 步的某一步遇到不懂的，结合「当前步骤内容」解答。

    history 形如 [{"role": "user"/"assistant", "content": "..."}]，已含最新用户消息。
    """
    context = build_coach_context(paper)

    # 当前步骤的完整内容（让教练知道用户正在看什么、卡在哪）
    step_data = paper.get("training", {}).get(current_step_id, {})
    step_title = step_data.get("title", current_step_id)
    step_brief = json.dumps(step_data, ensure_ascii=False)
    if len(step_brief) > 2200:
        step_brief = step_brief[:2200]

    # 取最后一条用户消息，判断是否在问「演进/前置」
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")

    # 如果用户问「演进/前置/历史脉络」，实际调用检索构建演进链，把结果注入上下文
    lineage_text = ""
    if any(k in last_user for k in ["前置", "演进", "历史", "来龙去脉", "脉络", "发展", "引用", "奠基"]):
        try:
            meta = paper.get("meta", {})
            r = lineage.build_lineage(meta.get("title", ""), meta.get("subtitle", ""), api_key)
            if r.get("lineage"):
                lineage_text = "【已检索到的演进链】\n" + r["lineage"] + "\n前置论文：" + \
                    "、".join(n["title"] for n in r.get("predecessors", [])[:4])
        except Exception:
            lineage_text = ""

    style = paper.get("_style", "mixed")
    style_inst = AGENT_STYLE.get(style, AGENT_STYLE["mixed"])

    messages = [
        {"role": "system", "content": COACH_SYSTEM + "\n" + style_inst
         + "\n\n【你手上这篇论文的背景】\n" + context
         + f"\n\n【用户当前正在看的步骤：{step_title}】\n{step_brief}"
         + ("\n\n【额外资料】\n" + lineage_text if lineage_text else "")},
    ]
    messages += history
    return _call(messages, api_key)


def coach_first_message(paper: dict, api_key: str) -> str:
    """用户上传论文后，教练的开场白（引导进入第一步）。"""
    context = build_coach_context(paper)
    user = (
        "用户刚上传了这篇论文，请你作为教练，用一段简短的开场白欢迎他，"
        "点出这篇论文值得关注的地方，然后引导他进入第一个思考：这篇论文为什么值得读？"
        "不要长篇大论，2~3 句即可，最后抛一个问题给他。"
    )
    messages = [
        {"role": "system", "content": COACH_SYSTEM + "\n\n【论文背景】\n" + context},
        {"role": "user", "content": user},
    ]
    return _call(messages, api_key)
