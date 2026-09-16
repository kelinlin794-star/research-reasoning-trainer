# -*- coding: utf-8 -*-
"""
方法论页 —— 训练理念与证据分层规则说明。

这一页回答两个问题：
1. 为什么这个训练器要这么设计？
2. 三种证据分层分别意味着什么？
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import common

st.set_page_config(page_title="方法论", page_icon="❓", layout="wide")
common.init_state()

st.title("方法论 · 关于这套训练器")

st.markdown("### 它不做什么")
st.markdown(
    "它不是论文总结器。总结器把论文当成「最终成品」告诉你结论；"
    "这套训练器把论文还原成「问题解决的过程」，逼你先动脑，再看答案。"
)

st.markdown("### 三条核心原则")
principles = [
    ("不神化创作者", "把创新还原成「面对约束 → 测量系统 → 发现瓶颈 → 提出方案」的工程决策，而不是「天才的灵光一现」。"),
    ("不做术语→定义", "坚持「问题 → 需求 → 概念 → 方法」的逻辑链条，先讲为什么需要，再讲它是什么。"),
    ("严格证据分层", "所有内容都标注来源层级，绝不假装读心作者的真实想法。"),
]
for name, desc in principles:
    st.markdown(f"**{name}**：{desc}")

st.markdown("### 证据分层图例")
st.markdown("读内容时请始终留意每一条前面的徽标：")
for key in ["stated", "reconstructed", "unknown"]:
    info = common.EVIDENCE_MAP[key]
    desc = {
        "stated": "这句话论文白纸黑字写明了，可直接引用。",
        "reconstructed": "论文没直说，但根据其方法/实验能合理推断，属于我们的解读。",
        "unknown": "论文没提，我们也无法确定，明确标注出来，不臆测。",
    }[key]
    st.markdown(
        f'{common.evidence_badge(key)} <b>{info["label"]}</b>　{desc}',
        unsafe_allow_html=True,
    )

st.markdown("### 训练闭环")
st.markdown(
    "先猜（给脚手架）→ 看作者方案 → 拆解方法 → 看实验验证 → 找局限 → 去魅 → 回归历史演进。"
    "核心是「先猜再看答案」——你的猜想对不对不重要，重要的是你完成了一次「研究者式的思考」。"
)

st.divider()
if st.button("开始第一课", type="primary"):
    st.switch_page("app.py")
