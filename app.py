# -*- coding: utf-8 -*-
"""
首页 —— 论文选择、上传解析与训练总览。

功能：
- 上传任意 PDF 论文，调用 DeepSeek 自动拆解成 7 步训练数据。
- 列出 data/ 下预置论文 + 本次上传解析的动态论文。
- 侧边栏显示证据分层图例。
"""

import streamlit as st
import common
import parser

# 页面配置必须最先调用
st.set_page_config(page_title="科研问题推理训练器", page_icon="🧠", layout="wide")

common.init_state()


def get_api_key():
    """读取 DeepSeek API Key（优先 st.secrets，失败则读本地 secrets.toml 文件）。"""

    def _valid(k):
        return bool(k) and "填你的" not in k and "在这里" not in k

    # 方式一：从 Streamlit secrets 读
    try:
        k = (st.secrets.get("DEEPSEEK_API_KEY", "") or "").strip()
        if _valid(k):
            return k
    except Exception:
        pass

    # 方式二：直接读本地 .streamlit/secrets.toml（兜底，本地开发更稳）
    try:
        import os
        import tomllib
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
        with open(path, "rb") as f:
            s = tomllib.load(f)
        k = (s.get("DEEPSEEK_API_KEY") or "").strip()
        if _valid(k):
            return k
    except Exception:
        pass

    return ""


def render_header():
    st.title("科研问题推理训练器")
    st.caption(
        "不帮你「总结」论文，而是把论文从「最终成品」还原成「问题解决的过程」，"
        "训练你像研究者一样思考。"
    )


def render_legend():
    st.sidebar.markdown("### 证据分层图例")
    for key in ["stated", "reconstructed", "unknown"]:
        st.sidebar.markdown(common.evidence_badge(key) + common.EVIDENCE_MAP[key]["label"], unsafe_allow_html=True)
    st.sidebar.divider()


def render_upload():
    """上传 PDF → 自动解析为训练数据。"""
    st.markdown("### 上传论文，自动拆解训练")
    st.caption("丢一篇 PDF 论文进来，AI 会自动把它拆解成完整的 7 步推理训练。")

    uploaded = st.file_uploader("选择 PDF 文件", type=["pdf"], key="pdf_uploader")

    if uploaded is not None:
        if st.button("开始解析", type="primary"):
            api_key = get_api_key()
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
                        st.success(f"解析成功！论文《{data['meta'].get('title', pid)}》已生成训练数据，可在下方直接开始训练。")
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
        st.info("下方还没有可用论文。你可以上传一篇 PDF，或等待预置论文加载。")
        return

    st.markdown("### 选择一篇论文开始训练")
    st.caption(f"当前共 {len(papers)} 篇论文。每一篇都走一遍完整的 7 步推理闭环。")
    for p in papers:
        render_paper_card(p["id"], p["meta"], is_dynamic=p.get("dynamic", False))

    st.divider()
    st.info(
        "💡 建议：先别急着看答案。进入训练后，每一步都先自己猜一猜，再点开作者的方案——"
        "这才是这套训练器的意义所在。"
    )


main()
