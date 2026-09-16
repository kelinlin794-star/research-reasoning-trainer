# -*- coding: utf-8 -*-
"""
首页 —— 选择论文，进入 10 步科研训练。

主线是固定的 10 步训练工作流（防剧透、证据分层），
上传任意 PDF 可自动拆解成训练数据。每一步里都能「问教练」答疑。
"""

import streamlit as st
import common
import parser

st.set_page_config(page_title="科研问题推理训练器", page_icon="🧠", layout="wide")

common.init_state()


def render_header():
    st.title("科研问题推理训练器")
    st.caption(
        "不帮你「总结」论文，而是陪你把一篇论文走成一次真正的科研思考。"
        "固定 10 步工作流，不懂随时问教练。"
    )


def render_legend():
    st.sidebar.markdown("### 证据分层图例")
    for key in ["stated", "reconstructed", "unknown"]:
        st.sidebar.markdown(common.evidence_badge(key) + common.EVIDENCE_MAP[key]["label"], unsafe_allow_html=True)
    st.sidebar.divider()


def render_upload():
    """上传 PDF → 自动解析为训练数据。"""
    st.markdown("### 上传论文，自动拆解训练")
    st.caption("丢一篇 PDF 论文进来，AI 自动把它拆解成完整的 10 步训练，然后带你一步步走。")

    uploaded = st.file_uploader("选择 PDF 文件", type=["pdf"], key="pdf_uploader")

    if uploaded is not None:
        if st.button("开始解析", type="primary"):
            api_key = common.get_api_key()
            if not api_key:
                st.error(
                    "未配置 DeepSeek API Key。请在项目 `.streamlit/secrets.toml` 里添加一行 "
                    "`DEEPSEEK_API_KEY = \"你的key\"`，然后重启应用。"
                )
            else:
                with st.spinner("正在解析论文：提取文本 → AI 拆解 → 生成训练数据（约 30~60 秒）..."):
                    try:
                        data = parser.parse_paper(uploaded.getvalue(), api_key)
                        pid = common.save_dynamic_paper(data)
                        st.success(f"解析成功！论文《{data['meta'].get('title', pid)}》已就绪，可在下方开始训练。")
                    except Exception as e:
                        st.error(f"解析失败：{e}")


def render_paper_card(pid, meta, is_dynamic=False):
    with st.container(border=True):
        col_l, col_r = st.columns([3, 1])
        with col_l:
            title = meta.get("title", pid)
            if is_dynamic:
                st.markdown(f"#### {title}　`你上传的`")
            else:
                st.markdown(f"#### {title}")
            st.caption(meta.get("subtitle", ""))
            st.markdown(
                f"**作者**：{meta.get('authors', '')}  \n"
                f"**领域**：{meta.get('field', '')} · **难度**：{meta.get('difficulty', '')}  \n"
                f"**年份**：{meta.get('year', '')} · {meta.get('arxiv', '')}"
            )
            tags = "　".join(f"`{t}`" for t in meta.get("tags", []))
            if tags:
                st.markdown(tags)
        with col_r:
            st.write("")
            st.write("")
            if st.button("开始训练", key=f"start_{pid}", type="primary", use_container_width=True):
                common.start_paper(pid)
                st.switch_page("pages/1_推理训练.py")


def main():
    render_header()
    render_legend()

    render_upload()
    st.divider()

    papers = common.list_papers()
    if not papers:
        st.info("下方还没有可用论文。你可以上传一篇 PDF 开始。")
        return

    st.markdown("### 选择一篇论文开始训练")
    st.caption(f"当前共 {len(papers)} 篇论文。每一篇都走一遍完整的 10 步推理闭环。")
    for p in papers:
        render_paper_card(p["id"], p["meta"], is_dynamic=p.get("dynamic", False))

    st.divider()
    st.info(
        "💡 先别急着看答案。每一步先自己想一想，卡住了就点「问教练」。"
    )


main()
