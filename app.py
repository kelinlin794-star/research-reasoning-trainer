# -*- coding: utf-8 -*-
"""
首页 —— 论文选择与训练总览。

功能：
- 列出 data/ 下所有论文，展示元信息与训练入口。
- 侧边栏显示证据分层图例与全局导航提示。
"""

import streamlit as st
import common

# 页面配置必须最先调用
st.set_page_config(page_title="科研问题推理训练器", page_icon="🧠", layout="wide")

common.init_state()


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


def render_paper_card(pid, meta):
    with st.container(border=True):
        col_l, col_r = st.columns([3, 1])
        with col_l:
            st.markdown(f"#### {meta['title']}")
            st.caption(meta["subtitle"])
            st.markdown(
                f"**作者**：{meta.get('authors', '')}  \n"
                f"**领域**：{meta.get('field', '')} · **难度**：{meta.get('difficulty', '')}  \n"
                f"**年份**：{meta.get('year', '')} · {meta.get('arxiv', '')}"
            )
            tags = "　".join(f"`{t}`" for t in meta.get("tags", []))
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

    papers = common.list_papers()
    if not papers:
        st.warning("data/ 目录下还没有论文数据，请先添加论文 JSON。")
        return

    st.markdown("### 选择一篇论文开始训练")
    st.caption(f"当前共 {len(papers)} 篇论文。每一篇都走一遍完整的 7 步推理闭环。")
    for p in papers:
        render_paper_card(p["id"], p["meta"])

    st.divider()
    st.info(
        "💡 建议：先别急着看答案。进入训练后，每一步都先自己猜一猜，再点开作者的方案——"
        "这才是这套训练器的意义所在。"
    )


main()
