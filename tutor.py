# -*- coding: utf-8 -*-
"""
科研教练点评模块 —— Agent 化的「决策层」雏形。

让 LLM 不只是「生成训练内容」，而是根据用户的实际回答，动态地点评、追问、打磨。
这是从「固定 Workflow」走向「自主决策 Agent」的最小改动：三个关键步骤各加一次动态反馈。

三个能力：
1. comment_guess      —— 点评用户在「如果是你」步的猜想
2. comment_limitation —— 点评用户在「还有什么问题」步挑出的局限
3. polish_question    —— 打磨用户在「下一个研究问题」步写下的问题
"""

import requests

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

COACH_SYSTEM = (
    "你是一位科研思维教练，擅长用苏格拉底式提问引导科研新手思考。"
    "你的原则：不直接给答案、不居高临下，而是点出对方思路里的亮点和盲点，再追问一个更有深度的问题。"
    "回答用中文，控制在 150 字以内，语气温和但一针见血。"
)


def _call(system: str, user: str, api_key: str) -> str:
    resp = requests.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.6,
            "max_tokens": 400,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def comment_guess(title: str, constraints: list, user_guess: str, author_route: str, api_key: str) -> str:
    """点评用户的猜想：亮点、盲点、追问。"""
    user = (
        f"论文：《{title}》\n"
        f"作者面对的约束：\n" + "\n".join(f"- {c}" for c in constraints) + "\n"
        f"用户的猜想：「{user_guess}」\n"
        f"作者的真实路线：「{author_route}」\n\n"
        f"请点评用户的猜想：他哪里想对了、哪里是盲点，然后追问他一个更深的问题（不要直接复述答案）。"
    )
    return _call(COACH_SYSTEM, user, api_key)


def comment_limitation(title: str, user_limits: list, api_key: str) -> str:
    """点评用户挑出的局限。"""
    user = (
        f"论文：《{title}》\n"
        f"用户挑出的局限：\n" + "\n".join(f"- {x}" for x in user_limits) + "\n\n"
        f"请点评：这些局限抓得准不准？有没有更本质的局限他没提到？追问一个。"
    )
    return _call(COACH_SYSTEM, user, api_key)


def polish_question(title: str, user_question: str, api_key: str) -> str:
    """把用户的研究问题打磨得更尖锐、可验证。"""
    user = (
        f"论文：《{title}》\n"
        f"用户提出的研究问题：「{user_question}」\n\n"
        f"请帮他把这个问题打磨得更尖锐、更可验证（给出打磨后的版本 + 一两句为什么这样改）。"
    )
    return _call(COACH_SYSTEM, user, api_key)
