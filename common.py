# -*- coding: utf-8 -*-
"""
科研问题推理训练器 —— 共享工具模块。

职责：
1. 加载 data/ 目录下的论文训练数据（JSON）。
2. 渲染「证据分层」徽标：论文明确陈述 / 合理重建 / 无法确定。
3. 管理跨页面的会话状态（st.session_state）。

设计说明：
- 训练数据与界面逻辑分离：每篇论文一个 JSON 文件，方便后续扩展多篇论文。
- 证据分层是产品的灵魂，所有内容块都必须带 evidence 字段。
"""

import os
import json

import streamlit as st

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")

# ---------------------------------------------------------------------------
# 证据分层定义（颜色 = 徽标配色）
#   stated         论文明确陈述（绿）
#   reconstructed  根据实验合理重建（琥珀）
#   unknown        无法确定（灰）
# ---------------------------------------------------------------------------
EVIDENCE_MAP = {
    "stated":        {"label": "论文明确陈述", "fg": "#0F6E56", "bg": "#E1F5EE"},
    "reconstructed": {"label": "合理重建",     "fg": "#854F0B", "bg": "#FAEEDA"},
    "unknown":       {"label": "无法确定",     "fg": "#5F5E5A", "bg": "#F1EFE8"},
}

# ---------------------------------------------------------------------------
# 训练闭环的 8 个阶段（顺序即交互闭环，不可打乱）
#   scenario 是「情境导入」，之后 7 步对应 先猜→方案→拆解→实验→局限→去魅→历史
# ---------------------------------------------------------------------------
STEPS = [
    {"id": "scenario",   "label": "现实问题"},
    {"id": "guess",      "label": "先猜"},
    {"id": "solution",   "label": "看作者方案"},
    {"id": "method",     "label": "拆解方法"},
    {"id": "experiment", "label": "看实验验证"},
    {"id": "limitation", "label": "找局限"},
    {"id": "demystify",  "label": "去魅"},
    {"id": "history",    "label": "回归历史演进"},
]

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------
def list_papers():
    """返回所有可用论文的 {id, meta} 列表（预置 + 用户上传的动态论文）。"""
    papers = []
    # 预置论文（data/ 目录）
    if os.path.isdir(DATA_DIR):
        for fn in sorted(os.listdir(DATA_DIR)):
            if fn.endswith(".json"):
                with open(os.path.join(DATA_DIR, fn), "r", encoding="utf-8") as f:
                    data = json.load(f)
                papers.append({"id": data["id"], "meta": data.get("meta", {}), "dynamic": False})
    # 动态论文（本次会话上传解析的）
    for pid, data in st.session_state.get("dynamic_papers", {}).items():
        papers.append({"id": pid, "meta": data.get("meta", {}), "dynamic": True})
    return papers


def load_paper(paper_id):
    """按 id 加载单篇论文的完整训练数据（优先动态论文，其次预置 JSON）。"""
    dyn = st.session_state.get("dynamic_papers", {})
    if paper_id in dyn:
        return dyn[paper_id]
    path = os.path.join(DATA_DIR, f"{paper_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 证据徽标渲染
# ---------------------------------------------------------------------------
def evidence_badge(level):
    """返回某证据层级对应的 HTML 徽标。"""
    info = EVIDENCE_MAP.get(level, EVIDENCE_MAP["unknown"])
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:10px;'
        f'font-size:12px;color:{info["fg"]};background:{info["bg"]};'
        f'border:1px solid {info["fg"]}33;margin-right:6px;">'
        f'{info["label"]}</span>'
    )


def render_blocks(blocks):
    """渲染一组内容块，每块前面带证据分层徽标。

    每个 block 形如 {"evidence": "stated", "text": "..."}。
    """
    for b in blocks:
        badge = evidence_badge(b.get("evidence", "stated"))
        st.markdown(f"{badge} {b['text']}", unsafe_allow_html=True)


def render_evidence_legend():
    """渲染证据分层图例（用于方法论页等）。"""
    legend = " ".join(evidence_badge(k) for k in ["stated", "reconstructed", "unknown"])
    st.markdown(legend, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 会话状态管理
# ---------------------------------------------------------------------------
def init_state():
    """初始化跨页面共享的会话状态。所有页面渲染前都应调用一次。"""
    defaults = {
        "paper_id": None,          # 当前选中的论文 id
        "step_index": 0,           # 当前训练步骤索引（0~7）
        "guess_submitted": False,  # 是否已提交猜想（门控：解锁「看作者方案」）
        "guess_choice": None,      # 用户在「先猜」步的选择
        "limitation_choice": None, # 用户在「找局限」步的选择
        "notes": {},               # 去魅笔记 {paper_id: [str, ...]}
        "dynamic_papers": {},      # 用户上传解析的动态论文 {paper_id: paper_data}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def save_dynamic_paper(paper_data):
    """把上传解析出的论文存入会话，使其可被训练流程加载。"""
    pid = paper_data.get("id") or f"uploaded_{len(st.session_state.dynamic_papers) + 1}"
    paper_data["id"] = pid
    paper_data["_dynamic"] = True
    st.session_state.dynamic_papers[pid] = paper_data
    return pid


def start_paper(paper_id):
    """开始/进入一篇论文：重置训练进度。"""
    st.session_state.paper_id = paper_id
    st.session_state.step_index = 0
    st.session_state.guess_submitted = False
    st.session_state.guess_choice = None
    st.session_state.limitation_choice = None
