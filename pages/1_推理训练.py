# -*- coding: utf-8 -*-
"""
推理训练页 —— 10 步闭环的核心向导。

这是整个产品的心脏。用户沿着
  为什么值得读 → 以前怎么解决 → 为什么以前不够 → 这篇论文处在哪
  → 如果是你，你会怎么办 → 作者怎么解决 → 实验到底证明了什么
  → 还有什么问题 → 后续论文怎么继续 → 下一个研究问题是什么
一步步走完。「防剧透」门控：没提交猜想，就看不到「作者怎么解决」。

状态依赖（跨页面共享，见 common.init_state）：
- paper_id / step_index       当前论文与步骤
- guess_submitted             是否已提交猜想（解锁「作者怎么解决」）
- limitation_submitted        是否已提交局限分析（解锁「作者自评」）
"""

import os
import sys

# 让 pages/ 下的脚本能 import 根目录的 common 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import common
import tutor
import agent
import lineage

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
# 工具函数
# ---------------------------------------------------------------------------
def material_safe(text):
    """把内容里的 `<` `>` 转义，避免被当成 HTML 标签。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
def render_blocks_step(d):
    """通用步骤：intro + blocks（用于 why_read / prior_work / prior_limits / experiment / future）。"""
    st.markdown(d["intro"])
    common.render_blocks(d.get("blocks", []))


def render_position(d):
    """第 4 步「这篇论文处在哪」：内容 + 自动构建演进链（前置→当前→后续）。"""
    st.markdown(d["intro"])
    common.render_blocks(d.get("blocks", []))

    st.divider()
    st.markdown("**看它的演进链全景**")
    api_key = common.get_api_key()
    fb_key = f"lineage_{st.session_state.paper_id}"

    if st.button("构建这篇论文的演进链"):
        if not api_key:
            st.warning("未配置 API Key，无法构建。")
        else:
            with st.spinner("正在检索文献并构建演进链（约 1~2 分钟）..."):
                try:
                    result = lineage.build_lineage(meta["title"], meta.get("subtitle", ""), api_key)
                    st.session_state[fb_key] = result
                    st.rerun()
                except Exception as e:
                    st.error(f"构建失败：{e}")

    if st.session_state.get(fb_key):
        common.render_lineage_cards(st.session_state[fb_key])
        with st.expander("查看演进链完整叙事"):
            st.write(st.session_state[fb_key].get("lineage", ""))


def render_prior_work(d):
    """第 2 步「以前怎么解决」：内容 + 技术演进线。"""
    st.markdown(d["intro"])
    common.render_blocks(d.get("blocks", []))
    st.divider()
    st.markdown("**技术演进线**")
    common.render_timeline(paper.get("timeline_tech", []))


def render_prior_limits(d):
    """第 3 步「为什么以前不够」：内容 + 领域问题线。"""
    st.markdown(d["intro"])
    common.render_blocks(d.get("blocks", []))
    st.divider()
    st.markdown("**领域问题线**")
    common.render_timeline(paper.get("timeline_domain", []))


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
                f'<span style="color:{color};font-weight:500;">{tag}</span> {material_safe(s["text"])}'
                f'<span style="color:#5F5E5A;">{mine}</span><br>'
                f'<span style="color:#5F5E5A;font-size:13px;">　{material_safe(s["why"])}</span>',
                unsafe_allow_html=True,
            )
        correct = next(s for s in d["scaffold"] if s["correct"])
        st.divider()
        st.markdown("**作者的真实路线**：")
        st.info(correct["text"] + "　" + correct["why"])

        # Agent 决策层：让 AI 教练点评用户的猜想
        st.divider()
        st.markdown("**让 AI 教练点评你的思路**")
        fb_key = f"guess_fb_{st.session_state.paper_id}"
        if st.button("点评我的猜想"):
            api_key = common.get_api_key()
            if not api_key:
                st.warning("未配置 API Key，无法点评。")
            else:
                with st.spinner("AI 正在点评你的思路..."):
                    try:
                        fb = tutor.comment_guess(meta["title"], d["constraints"], chosen, correct["text"], api_key)
                        st.session_state[fb_key] = fb
                        st.rerun()
                    except Exception as e:
                        st.error(f"点评失败：{e}")
        if st.session_state.get(fb_key):
            st.info(st.session_state[fb_key])


def render_solution(d):
    st.markdown(d["intro"])
    # 工程决策链（去魅：把创新还原成 约束→测量→瓶颈→方案）
    chain = d.get("chain", [])
    if chain:
        st.markdown("**作者的工程决策链：**")
        for i, item in enumerate(chain):
            st.markdown(f"**{i + 1}. {item['stage']}**：{material_safe(item['text'])}")
        st.divider()
    common.render_blocks(d.get("blocks", []))


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

        # Agent 决策层：让 AI 教练点评用户的分析
        st.divider()
        st.markdown("**让 AI 教练点评你的分析**")
        fb_key = f"lim_fb_{st.session_state.paper_id}"
        if st.button("点评我的分析"):
            api_key = common.get_api_key()
            if not api_key:
                st.warning("未配置 API Key，无法点评。")
            else:
                with st.spinner("AI 正在点评..."):
                    try:
                        fb = tutor.comment_limitation(meta["title"], selected, api_key)
                        st.session_state[fb_key] = fb
                        st.rerun()
                    except Exception as e:
                        st.error(f"点评失败：{e}")
        if st.session_state.get(fb_key):
            st.info(st.session_state[fb_key])


def render_next_question(d):
    st.markdown(d["intro"])
    prompts = d.get("prompts", [])
    if prompts:
        st.markdown("**可以从这些角度想：**")
        for p in prompts:
            st.markdown(f"- {p}")
    if d.get("blocks"):
        st.divider()
        common.render_blocks(d["blocks"])

    st.divider()
    st.markdown("**你的下一个研究问题：**")
    q = st.text_area(
        "试着写下一个你想研究的问题（一句话即可）",
        key="next_q_input",
        placeholder="例：能不能让这套优化方法在换硬件时自动重调，而不是每次手调 kernel？",
    )
    if st.button("保存我的研究问题", type="primary"):
        if q.strip():
            pid = st.session_state.paper_id
            notes = st.session_state.notes.setdefault(pid, [])
            notes.append("【研究问题】" + q.strip())
            st.session_state.notes[pid] = notes
            st.success("已保存到「去魅档案」！")
        else:
            st.warning("先写点东西再保存吧。")

    # Agent 决策层：让 AI 打磨用户的研究问题
    st.divider()
    st.markdown("**让 AI 帮你把问题打磨得更尖锐**")
    if st.button("打磨我的问题"):
        api_key = common.get_api_key()
        if not q.strip():
            st.warning("先在上面写下你的研究问题。")
        elif not api_key:
            st.warning("未配置 API Key，无法打磨。")
        else:
            with st.spinner("AI 正在打磨你的问题..."):
                try:
                    fb_key = f"polish_{st.session_state.paper_id}"
                    st.session_state[fb_key] = tutor.polish_question(meta["title"], q.strip(), api_key)
                    st.rerun()
                except Exception as e:
                    st.error(f"打磨失败：{e}")
    if st.session_state.get(f"polish_{st.session_state.paper_id}"):
        st.info(st.session_state[f"polish_{st.session_state.paper_id}"])


def render_step(step_id, d):
    if step_id == "guess":
        render_guess(d)
    elif step_id == "solution":
        # 门控：必须先提交猜想
        if not st.session_state.guess_submitted:
            st.warning("这一步是「作者怎么解决」，请先完成上一步「如果是你，你会怎么办」，提交你的猜想后再来看答案。")
            if st.button("← 回到「如果是你」"):
                st.session_state.step_index = 4
                st.rerun()
        else:
            render_solution(d)
    elif step_id == "position":
        render_position(d)
    elif step_id == "prior_work":
        render_prior_work(d)
    elif step_id == "prior_limits":
        render_prior_limits(d)
    elif step_id == "limitation":
        render_limitation(d)
    elif step_id == "next_question":
        render_next_question(d)
    else:
        # why_read / prior_work / prior_limits / position / experiment / future
        render_blocks_step(d)


def render_source():
    """每一步都能展开查看论文原文，对照 AI 拆解内容验证。"""
    src = paper.get("_source_text", "").strip()
    pdf_path = common.get_pdf_path(st.session_state.paper_id)
    if not src and not pdf_path:
        return
    with st.expander("📄 查看论文原文（对照验证）"):
        if pdf_path:
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ 下载原始 PDF", f.read(),
                                   file_name=f"{st.session_state.paper_id}.pdf",
                                   mime="application/pdf", key="source_pdf")
        if src:
            st.text_area("论文原文（清洗后文本）", src, height=400, key="source_view")


def render_coach():
    """每一步底部的「问教练」答疑区：读者不懂就问，教练结合当前步骤解答，不打断主线。"""
    st.divider()
    st.markdown("### 有不懂的？问教练")

    coach_key = f"coach_history_{st.session_state.paper_id}"
    if coach_key not in st.session_state:
        st.session_state[coach_key] = []
    history = st.session_state[coach_key]

    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    q = st.chat_input(f"这一步（{step_def['label']}）哪里不懂？")
    if q:
        api_key = common.get_api_key()
        if not api_key:
            st.warning("未配置 API Key，无法答疑。")
        else:
            history.append({"role": "user", "content": q})
            with st.spinner("教练思考中..."):
                try:
                    reply = agent.coach_reply(paper, step_def["id"], history, api_key)
                    history.append({"role": "assistant", "content": reply})
                    st.session_state[coach_key] = history
                except Exception as e:
                    st.error(f"教练走神了：{e}")
            st.rerun()


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
    render_source()
    render_coach()
    render_nav()


main()
