# -*- coding: utf-8 -*-
"""
历史演进页 —— 两条外部时间线。

- 领域问题线：人类/机器人控制领域一直在解决什么问题？
- 技术演进线：解决这个问题的技术经历了哪些迭代？

（第三条「论文内部推理线」就是推理训练页的 7 步闭环本身。）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import common

st.set_page_config(page_title="历史演进", page_icon="📈", layout="wide")
common.init_state()

st.title("历史演进 · 三条时间线")
st.caption("把一篇论文放回更大的坐标系：它同时是两条历史线的交汇点。")

# 没有选中论文时，提示但仍可浏览（时间线属于论文）
if not st.session_state.paper_id:
    st.warning("尚未选择论文。可先在首页选一篇，再看它对应的历史演进。")
    st.stop()

paper = common.load_paper(st.session_state.paper_id)
meta = paper["meta"]

st.markdown(f"### {meta['title']}")
st.caption(f"{meta['field']} · {meta['year']}")

tab = st.radio(
    "选择时间线",
    ["领域问题线", "技术演进线"],
    horizontal=True,
)

if tab == "领域问题线":
    events = paper.get("timeline_domain", [])
    st.markdown("#### 领域问题线：人类一直在解决什么问题？")
else:
    events = paper.get("timeline_tech", [])
    st.markdown("#### 技术演进线：技术经历了哪些迭代？")


def render_timeline(events):
    """用简洁的垂直时间线渲染事件列表，每条带证据徽标。"""
    if not events:
        st.info("暂无时间线数据。")
        return
    for i, ev in enumerate(events):
        with st.container(border=True):
            top = st.columns([1, 4])
            with top[0]:
                st.markdown(f"**{ev.get('year', '')}**")
            with top[1]:
                st.markdown(f"**{ev.get('title', '')}**")
            badge = common.evidence_badge(ev.get("evidence", "stated"))
            st.markdown(f"{badge} {ev.get('text', '')}", unsafe_allow_html=True)


render_timeline(events)

st.divider()
if st.button("回到推理训练", type="primary"):
    st.switch_page("pages/1_推理训练.py")
