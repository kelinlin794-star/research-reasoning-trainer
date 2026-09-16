# -*- coding: utf-8 -*-
"""
去魅档案页 —— 我的学习记录。

- 回顾当前论文的训练痕迹（我的猜想、我发现的局限）。
- 写下「去魅心得」，沉淀成自己的知识资产。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import common

st.set_page_config(page_title="去魅档案", page_icon="📚", layout="wide")
common.init_state()

st.title("去魅档案 · 我的学习记录")
st.caption("训练不是为了记住结论，而是为了留下「我是怎么想通的」这条线索。")

if not st.session_state.paper_id:
    st.warning("尚未开始训练。先回首页选一篇论文吧。")
    if st.button("回首页"):
        st.switch_page("app.py")
    st.stop()

paper = common.load_paper(st.session_state.paper_id)
meta = paper["meta"]
pid = paper["id"]

st.markdown(f"### {meta['title']}")

# ---------------------------------------------------------------------------
# 训练痕迹回顾
# ---------------------------------------------------------------------------
st.markdown("#### 我的训练痕迹")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**我的猜想**")
    if st.session_state.guess_choice:
        st.markdown(f"> {st.session_state.guess_choice}")
    else:
        st.caption("（还没走到「先猜」这一步）")
with c2:
    st.markdown("**我发现的局限**")
    if st.session_state.get("limitation_choice"):
        for item in st.session_state.limitation_choice:
            st.markdown(f"- {item}")
    else:
        st.caption("（还没走到「找局限」这一步）")

st.divider()

# ---------------------------------------------------------------------------
# 去魅心得笔记
# ---------------------------------------------------------------------------
st.markdown("#### 写下去魅心得")
st.caption("用一句话回答：这篇论文的「创新」，去掉光环之后，本质是什么？")

notes = st.session_state.notes.setdefault(pid, [])
note = st.text_area("我的心得", key=f"note_input_{pid}", placeholder="例：它不是发明新模型，而是把「大模型跑不快」拆成可测量、可逐一击破的工程问题……")

col_a, col_b = st.columns([1, 1])
with col_a:
    if st.button("保存心得", type="primary"):
        if note.strip():
            notes.append(note.strip())
            st.session_state.notes[pid] = notes
            st.success("已保存。")
            st.rerun()
        else:
            st.warning("内容为空，先写点东西吧。")

# ---------------------------------------------------------------------------
# 历史心得列表
# ---------------------------------------------------------------------------
if notes:
    st.markdown("#### 历史心得")
    for i, n in enumerate(reversed(notes), 1):
        st.markdown(f"**{i}.** {n}")
else:
    st.caption("还没有心得记录。")

st.divider()
if st.button("回到推理训练"):
    st.switch_page("pages/1_推理训练.py")
