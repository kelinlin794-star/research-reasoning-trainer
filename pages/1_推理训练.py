# -*- coding: utf-8 -*-
"""
推理训练页 —— 7 步闭环的核心向导。

这是整个产品的心脏：用户沿着
  现实问题 → 先猜 → 看作者方案 → 拆解方法 → 看实验验证 → 找局限 → 去魅 → 回归历史演进
一步步走完，每一步都有「防剧透」门控——没提交猜想，就看不到作者的方案。

状态依赖（跨页面共享，见 common.init_state）：
- paper_id / step_index       当前论文与步骤
- guess_submitted             是否已提交猜想（解锁「看作者方案」）
- limitation_submitted        是否已提交局限分析（解锁「作者自评」）
"""

import os
import sys

# 让 pages/ 下的脚本能 import 根目录的 common 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import common

st.set_page_config(page_title="推理训练", page_icon="🧠", layout="wide")
common.init_state()

# ---------------------------------------------------------------------------
# 前置检查：没有选中论文时引导回首页
# ---------------------------------------------------------------------------
if not st.session_state.paper_id:
    st.warning("请先在首页选择一篇论文。")
    if st.button("回首页"):
        st.switch_page("app.py")
    st.stop()

paper = common.load_paper(st.session_state.paper_id)
meta = paper["meta"]
training = paper["training"]
step_idx = st.session_state.step_index
step_def = common.STEPS[step_idx]
step_data = training[step_def["id"]]


# ---------------------------------------------------------------------------
# 侧边栏：证据图例 + 步骤进度
# ---------------------------------------------------------------------------
def render_sidebar():
    st.sidebar.markdown("### 证据分层")
    for key in ["stated", "reconstructed", "unknown"]:
        st.sidebar.markdown(common.evidence_badge(key) + common.EVIDENCE_MAP[key]["label"], unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.markdown("### 训练进度")
    for i, s in enumerate(common.STEPS):
        if i < step_idx:
            mark = "✅"
        elif i == step_idx:
            mark = "▶️"
        else:
            mark = "·"
        st.sidebar.markdown(f"{mark} {i + 1}. {s['label']}")
    st.sidebar.divider()
    if st.sidebar.button("重新开始本篇"):
        common.start_paper(paper["id"])
        st.rerun()


# ---------------------------------------------------------------------------
# 各步骤渲染
# ---------------------------------------------------------------------------
def render_scenario(d):
    st.markdown(d["intro"])
    common.render_blocks(d["blocks"])


def render_guess(d):
    st.markdown(d["intro"])
    st.markdown("**你已知的约束：**")
    for c in d["constraints"]:
        st.markdown(f"- {c}")
    st.divider()

    if not st.session_state.guess_submitted:
        options = [s["text"] for s in d["scaffold"]]
        choice = st.radio("你的猜想是？", options, index=None, key="guess_radio")
        if st.button("提交猜想", type="primary"):
            if choice is None:
                st.warning("请先选择一个猜想再提交。")
            else:
                st.session_state.guess_choice = choice
                st.session_state.guess_submitted = True
                st.rerun()
    else:
        st.success("猜想已提交，下面是逐项反馈。")
        chosen = st.session_state.guess_choice
        for s in d["scaffold"]:
            is_correct = s["correct"]
            is_chosen = (s["text"] == chosen)
            tag = "【正确】" if is_correct else "【不成立】"
            mine = "（← 你的选择）" if is_chosen else ""
            color = "#0F6E56" if is_correct else "#A32D2D"
            st.markdown(
                f'<span style="color:{color};font-weight:500;">{tag}</span> {s["text"]}'
                f'<span style="color:#5F5E5A;">{mine}</span><br>'
                f'<span style="color:#5F5E5A;font-size:13px;">　{material_safe(s["why"])}</span>',
                unsafe_allow_html=True,
            )
        correct = next(s for s in d["scaffold"] if s["correct"])
        st.divider()
        st.markdown("**作者的真实路线**：")
        st.info(correct["text"] + "　" + correct["why"])


def material_safe(text):
    """把内容里的 `<` `>` 转义，避免被当成 HTML 标签。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_solution(d):
    st.markdown(d["intro"])
    common.render_blocks(d["blocks"])


def render_method(d):
    st.markdown(d["intro"])
    for i, layer in enumerate(d["layers"]):
        with st.expander(f"{i + 1}. {layer['name']}", expanded=(i == 0)):
            common.render_blocks(layer["blocks"])


def render_experiment(d):
    st.markdown(d["intro"])
    common.render_blocks(d["blocks"])


def render_limitation(d):
    st.markdown(d["intro"])

    if not st.session_state.get("limitation_submitted", False):
        options = [s["text"] for s in d["scaffold"]]
        selected = st.multiselect(
            "勾选你觉得成立的软肋（可多选）：", options, key="lim_multi"
        )
        if st.button("提交我的分析", type="primary"):
            if not selected:
                st.warning("请至少勾选一项再提交。")
            else:
                st.session_state.limitation_choice = selected
                st.session_state.limitation_submitted = True
                st.rerun()
    else:
        st.success("已提交你的分析。逐项核对：")
        selected = st.session_state.limitation_choice or []
        for s in d["scaffold"]:
            is_valid = s["valid"]
            is_sel = s["text"] in selected
            tag = "【成立】" if is_valid else "【不成立】"
            mine = "（← 你选了）" if is_sel else ""
            color = "#0F6E56" if is_valid else "#A32D2D"
            st.markdown(
                f'<span style="color:{color};font-weight:500;">{tag}</span> {material_safe(s["text"])}'
                f'<span style="color:#5F5E5A;">{mine}</span><br>'
                f'<span style="color:#5F5E5A;font-size:13px;">　{material_safe(s["why"])}</span>',
                unsafe_allow_html=True,
            )
        st.divider()
        st.markdown("### 作者自己承认的局限")
        common.render_blocks(d["author_limitations"])


def render_demystify(d):
    st.markdown(d["intro"])
    for i, item in enumerate(d["chain"]):
        st.markdown(f"**{i + 1}. {item['stage']}**：{material_safe(item['text'])}")
    st.divider()
    common.render_blocks(d["blocks"])


def render_history(d):
    st.markdown(d["intro"])
    st.write("")
    if st.button("前往「历史演进」页，看三条时间线", type="primary"):
        st.switch_page("pages/2_历史演进.py")


def render_step(step_id, d):
    if step_id == "scenario":
        render_scenario(d)
    elif step_id == "guess":
        render_guess(d)
    elif step_id == "solution":
        # 门控：必须先提交猜想
        if not st.session_state.guess_submitted:
            st.warning("这一页是「作者的方案」，请先完成上一步「先猜」，提交你的猜想后再来看答案。")
            if st.button("← 回到「先猜」"):
                st.session_state.step_index = 1
                st.rerun()
        else:
            render_solution(d)
    elif step_id == "method":
        render_method(d)
    elif step_id == "experiment":
        render_experiment(d)
    elif step_id == "limitation":
        render_limitation(d)
    elif step_id == "demystify":
        render_demystify(d)
    elif step_id == "history":
        render_history(d)


def render_nav():
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if step_idx > 0:
            if st.button("← 上一步", use_container_width=True):
                st.session_state.step_index -= 1
                st.rerun()
    with col2:
        st.caption(f"第 {step_idx + 1} / {len(common.STEPS)} 步")
    with col3:
        if step_idx < len(common.STEPS) - 1:
            # 门控：guess 步未提交猜想时禁止前进
            if step_def["id"] == "guess" and not st.session_state.guess_submitted:
                st.button("下一步 →（先提交猜想）", disabled=True, use_container_width=True)
            else:
                if st.button("下一步 →", type="primary", use_container_width=True):
                    st.session_state.step_index += 1
                    st.rerun()


# ---------------------------------------------------------------------------
# 页面主体
# ---------------------------------------------------------------------------
def main():
    render_sidebar()

    st.title(meta["title"])
    st.caption(f"{meta['field']} · {meta['year']} · {meta.get('arxiv', '')}")
    st.progress((step_idx + 1) / len(common.STEPS))
    st.markdown(f"### 第 {step_idx + 1} 步 · {step_def['label']}")

    render_step(step_def["id"], step_data)
    render_nav()


main()
