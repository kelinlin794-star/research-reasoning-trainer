# -*- coding: utf-8 -*-
"""
历史演进页 —— 自动构建演进链 + 预置时间线。

- 自动构建演进链：输入任意论文标题，自动检索前置/后续论文，构建技术演进链（Agent 的核心能力）。
- 预置时间线：当前选中论文的领域问题线 / 技术演进线。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import common
import lineage

st.set_page_config(page_title="历史演进", page_icon="📈", layout="wide")
common.init_state()

st.title("历史演进")
st.caption("把一篇论文放回更大的坐标系——自动检索它的来龙去脉，构建技术演进链。")


# ---------------------------------------------------------------------------
# 一、自动构建演进链（独立功能，不依赖选中论文）
# ---------------------------------------------------------------------------
st.markdown("### 自动构建演进链")
st.caption("输入任意论文标题，AI 自动检索它的前置工作、后续引用，串成一条「问题→尝试→瓶颈→改进」的演进链。")

col_title, col_abs = st.columns([3, 2])
with col_title:
    title_input = st.text_input(
        "论文标题",
        placeholder="例：OpenVLA: An Open-Source Vision-Language-Action Model",
    )
with col_abs:
    abstract_input = st.text_area("摘要（可选，帮 AI 判断前置）", height=100)

if st.button("构建演进链", type="primary"):
    if not title_input.strip():
        st.warning("请先输入论文标题。")
    else:
        api_key = common.get_api_key()
        if not api_key:
            st.warning("未配置 API Key，无法构建。")
        else:
            with st.spinner("正在检索文献并构建演进链（约 1~2 分钟）..."):
                try:
                    result = lineage.build_lineage(title_input.strip(), abstract_input.strip(), api_key)
                    st.session_state["lineage_result"] = result
                    st.rerun()
                except Exception as e:
                    st.error(f"构建失败：{e}")


def render_lineage_result(r):
    st.markdown("#### 演进链叙事")
    st.info(r.get("lineage", ""))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**前置工作**")
        for n in r.get("predecessors", []):
            st.markdown(f"- {n['title']}（{n['year']}）")
    with c2:
        st.markdown("**当前论文**")
        cur = r.get("current")
        if cur:
            st.markdown(f"- {cur['title']}（{cur['year']}）")
        else:
            st.caption("（未检索到）")
    with c3:
        st.markdown("**后续工作**")
        for n in r.get("citations", []):
            st.markdown(f"- {n['title']}（{n['year']}）")


if st.session_state.get("lineage_result"):
    render_lineage_result(st.session_state["lineage_result"])

st.divider()


# ---------------------------------------------------------------------------
# 二、预置时间线（依赖当前选中论文）
# ---------------------------------------------------------------------------
if not st.session_state.paper_id:
    st.info("先回首页选一篇论文，这里还能查看它预置的领域问题线 / 技术演进线。")
else:
    paper = common.load_paper(st.session_state.paper_id)
    meta = paper["meta"]

    st.markdown(f"### {meta['title']} · 预置时间线")
    tab = st.radio("选择时间线", ["领域问题线", "技术演进线"], horizontal=True)
    events = paper.get("timeline_domain", []) if tab == "领域问题线" else paper.get("timeline_tech", [])

    for ev in events:
        with st.container(border=True):
            top = st.columns([1, 4])
            with top[0]:
                st.markdown(f"**{ev.get('year', '')}**")
            with top[1]:
                st.markdown(f"**{ev.get('title', '')}**")
            badge = common.evidence_badge(ev.get("evidence", "stated"))
            st.markdown(f"{badge} {ev.get('text', '')}", unsafe_allow_html=True)

st.divider()
if st.button("回到推理训练", type="primary"):
    st.switch_page("pages/1_推理训练.py")
