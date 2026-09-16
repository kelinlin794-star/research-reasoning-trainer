# -*- coding: utf-8 -*-
"""
去魅档案页 —— 我的学习记录。

完整同步训练痕迹：训练进度、我的猜想、我发现的局限、我的研究问题、去魅心得。
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
# 训练进度
# ---------------------------------------------------------------------------
step_idx = st.session_state.step_index
st.markdown("#### 训练进度")
st.progress((step_idx + 1) / len(common.STEPS))
st.caption(f"走到第 {step_idx + 1} 步 · {common.STEPS[step_idx]['label']}（共 {len(common.STEPS)} 步）")

# ---------------------------------------------------------------------------
# 训练痕迹：猜想 / 局限
# ---------------------------------------------------------------------------
st.markdown("#### 我的训练痕迹")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**我的猜想**")
    if st.session_state.guess_choice:
        st.markdown(f"> {st.session_state.guess_choice}")
    else:
        st.caption("（还没走到「如果是你」这一步）")
with c2:
    st.markdown("**我发现的局限**")
    if st.session_state.get("limitation_choice"):
        for item in st.session_state.limitation_choice:
            st.markdown(f"- {item}")
    else:
        st.caption("（还没走到「还有什么问题」这一步）")

st.divider()

# ---------------------------------------------------------------------------
# 研究问题 与 去魅心得（从 notes 里区分）
# ---------------------------------------------------------------------------
notes = st.session_state.notes.setdefault(pid, [])
research_questions = [n[len("【研究问题】"):] for n in notes if n.startswith("【研究问题】")]
insights = [n for n in notes if not n.startswith("【研究问题】")]

st.markdown("#### 我的研究问题")
if research_questions:
    for i, q in enumerate(research_questions, 1):
        st.markdown(f"**{i}.** {q}")
else:
    st.caption("（还没走到「下一个研究问题」这一步，或还没写下）")

st.markdown("#### 去魅心得")
st.caption("用一句话回答：这篇论文的「创新」，去掉光环之后，本质是什么？")
note = st.text_area("我的心得", key=f"note_input_{pid}", placeholder="例：它不是发明新模型，而是把「大模型跑不快」拆成可测量、可逐一击破的工程问题……")
if st.button("保存心得", type="primary"):
    if note.strip():
        notes.append(note.strip())
        st.session_state.notes[pid] = notes
        st.success("已保存。")
        st.rerun()
    else:
        st.warning("内容为空，先写点东西吧。")

if insights:
    st.markdown("**已保存的心得**")
    for i, n in enumerate(reversed(insights), 1):
        st.markdown(f"{i}. {n}")

st.divider()
if st.button("回到推理训练"):
    st.switch_page("pages/1_推理训练.py")
