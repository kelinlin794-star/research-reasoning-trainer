# -*- coding: utf-8 -*-
"""
首页 —— 对话式科研教练 Agent（统一入口）。

这是整个产品的核心体验：
- 上传一篇 PDF，或直接开始对话，Agent 手上有论文的完整解析；
- 你随时提问，Agent 自主决定下一步：引导你思考、解释概念、追问、构建演进链；
- 所有能力（解析、演进链、10 步训练、点评）都通过这一个对话串起来。

侧边栏：上传 PDF（对话起点）+ 预置论文（可进结构化 10 步训练）。
"""

import streamlit as st
import common
import parser
import agent

st.set_page_config(page_title="科研问题推理训练器", page_icon="🧠", layout="wide")

common.init_state()

# 对话状态
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_paper" not in st.session_state:
    st.session_state.chat_paper = None


def render_header():
    st.title("科研问题推理训练器")
    st.caption(
        "不是帮你「总结」论文，而是陪你把一篇论文走成一次真正的科研思考。"
        "上传论文，跟教练聊聊。"
    )


def render_sidebar():
    st.sidebar.markdown("### 开始对话")
    uploaded = st.sidebar.file_uploader("上传论文 PDF", type=["pdf"], key="pdf_uploader")

    if uploaded is not None:
        if st.sidebar.button("解析并开始对话", type="primary", use_container_width=True):
            api_key = common.get_api_key()
            if not api_key:
                st.sidebar.error("未配置 DeepSeek API Key，请检查 .streamlit/secrets.toml。")
            else:
                with st.spinner("正在解析论文（约 30~60 秒）..."):
                    try:
                        paper = parser.parse_paper(uploaded.getvalue(), api_key)
                        common.save_dynamic_paper(paper)
                        st.session_state.chat_paper = paper
                        opening = agent.coach_first_message(paper, api_key)
                        st.session_state.chat_history = [{"role": "assistant", "content": opening}]
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"解析失败：{e}")

    st.sidebar.divider()
    st.sidebar.markdown("### 证据分层")
    for key in ["stated", "reconstructed", "unknown"]:
        st.sidebar.markdown(common.evidence_badge(key) + common.EVIDENCE_MAP[key]["label"], unsafe_allow_html=True)

    st.sidebar.divider()
    st.sidebar.markdown("### 预置论文（结构化 10 步训练）")
    papers = common.list_papers()
    for p in papers:
        meta = p.get("meta", {})
        if st.sidebar.button(f"训练：{meta.get('title', p['id'])[:20]}", key=f"train_{p['id']}"):
            common.start_paper(p["id"])
            st.switch_page("pages/1_推理训练.py")

    st.sidebar.divider()
    if st.sidebar.button("清空对话"):
        st.session_state.chat_history = []
        st.session_state.chat_paper = None
        st.rerun()


def render_chat():
    # 对话历史
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 空状态引导
    if not st.session_state.chat_history:
        st.info("👈 先在左侧上传一篇论文 PDF，教练会从这里开始陪你。")

    # 输入框
    prompt = st.chat_input("跟教练聊聊这篇论文……")

    if prompt:
        if not st.session_state.chat_paper:
            st.warning("请先在左侧上传一篇论文 PDF。")
        else:
            api_key = common.get_api_key()
            if not api_key:
                st.error("未配置 DeepSeek API Key。")
            else:
                # 追加用户消息
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                # 教练回应
                with st.spinner("教练思考中..."):
                    try:
                        reply = agent.coach_reply(
                            st.session_state.chat_paper,
                            st.session_state.chat_history,
                            api_key,
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})
                    except Exception as e:
                        st.session_state.chat_history.append({"role": "assistant", "content": f"（教练暂时走神了：{e}）"})
                st.rerun()


def main():
    render_header()
    render_sidebar()
    render_chat()


main()
