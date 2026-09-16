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
UPLOADED_DIR = os.path.join(DATA_DIR, "uploaded")  # 用户上传解析的论文持久化目录

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
# 训练闭环的 10 个阶段（顺序即核心体验，不可打乱）
#   前 4 步「纵向定位」→ 中 4 步「横向拆解」→ 后 2 步「向前延伸」
#   第 5 步「如果是你」是防剧透的关键：先猜，才能看第 6 步作者方案
# ---------------------------------------------------------------------------
STEPS = [
    {"id": "why_read",      "label": "为什么值得读"},
    {"id": "prior_work",    "label": "以前怎么解决"},
    {"id": "prior_limits",  "label": "为什么以前不够"},
    {"id": "position",      "label": "这篇论文处在哪"},
    {"id": "guess",         "label": "如果是你，你会怎么办"},
    {"id": "solution",      "label": "作者怎么解决"},
    {"id": "experiment",    "label": "实验到底证明了什么"},
    {"id": "limitation",    "label": "还有什么问题"},
    {"id": "future",        "label": "后续论文怎么继续"},
    {"id": "next_question", "label": "下一个研究问题是什么"},
]

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------
def list_papers():
    """返回所有可用论文的 {id, meta} 列表（预置 + 用户上传持久化的动态论文）。"""
    papers = []
    # 预置论文（data/ 根目录）
    if os.path.isdir(DATA_DIR):
        for fn in sorted(os.listdir(DATA_DIR)):
            if fn.endswith(".json"):
                with open(os.path.join(DATA_DIR, fn), "r", encoding="utf-8") as f:
                    data = json.load(f)
                papers.append({"id": data["id"], "meta": data.get("meta", {}), "dynamic": False})
    # 上传的论文（data/uploaded/ 子目录，持久化，刷新/重启不丢）
    if os.path.isdir(UPLOADED_DIR):
        for fn in sorted(os.listdir(UPLOADED_DIR)):
            if fn.endswith(".json"):
                with open(os.path.join(UPLOADED_DIR, fn), "r", encoding="utf-8") as f:
                    data = json.load(f)
                papers.append({"id": data["id"], "meta": data.get("meta", {}), "dynamic": True})
    return papers


def load_paper(paper_id):
    """按 id 加载单篇论文（优先内存动态论文，其次磁盘 uploaded/，最后预置 data/）。"""
    dyn = st.session_state.get("dynamic_papers", {})
    if paper_id in dyn:
        return dyn[paper_id]
    upath = os.path.join(UPLOADED_DIR, f"{paper_id}.json")
    if os.path.exists(upath):
        with open(upath, "r", encoding="utf-8") as f:
            return json.load(f)
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
# 演进链可视化（前置 → 当前 → 后续 的卡片图）
# ---------------------------------------------------------------------------
def _paper_card(title, year, cited, bg, border, fg):
    """生成一张论文小卡片（HTML）。"""
    import html as _html
    t = _html.escape(title if len(title) <= 26 else title[:26] + "…")
    return (
        f'<div style="background:{bg};border:1px solid {border};border-radius:10px;'
        f'padding:10px 12px;width:150px;text-align:center;">'
        f'<div style="font-size:13px;font-weight:500;color:{fg};line-height:1.4;">{t}</div>'
        f'<div style="font-size:11px;color:#5F5E5A;margin-top:5px;">{year} · 被引 {cited}</div>'
        f'</div>'
    )


def render_lineage_cards(result: dict):
    """渲染演进链全景卡片图：前置（蓝）→ 当前（绿）→ 后续（紫）。"""
    pred = result.get("predecessors", [])
    cur = result.get("current")
    cites = result.get("citations", [])

    def _row(items, bg, border, fg):
        if not items:
            return '<div style="color:#5F5E5A;font-size:13px;text-align:center;">（未检索到）</div>'
        cards = "".join(_paper_card(n["title"], n["year"], n["cited_by_count"], bg, border, fg) for n in items)
        return f'<div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap;">{cards}</div>'

    def _label(text):
        return f'<div style="text-align:center;font-size:12px;color:#5F5E5A;margin:2px 0 6px;">{text}</div>'

    arrow = '<div style="text-align:center;color:#888780;font-size:20px;line-height:1;margin:4px 0;">▼</div>'

    html_block = (
        '<div style="font-family:sans-serif;padding:8px 0;">'
        + _label("前置工作（它建立在什么之上）")
        + _row(pred, "#E6F1FB", "#185FA5", "#0C447C")
        + arrow
        + _label("当前论文")
        + _row([cur] if cur else [], "#E1F5EE", "#0F6E56", "#085041")
        + arrow
        + _label("后续工作（谁在它基础上继续）")
        + _row(cites, "#EEEDFE", "#534AB7", "#3C3489")
        + '</div>'
    )
    st.markdown(html_block, unsafe_allow_html=True)


def render_timeline(events):
    """渲染一条时间线（事件列表，每条带证据徽标）。"""
    if not events:
        st.caption("（暂无时间线数据）")
        return
    for ev in events:
        with st.container(border=True):
            top = st.columns([1, 4])
            with top[0]:
                st.markdown(f"**{ev.get('year', '')}**")
            with top[1]:
                st.markdown(f"**{ev.get('title', '')}**")
            badge = evidence_badge(ev.get("evidence", "stated"))
            st.markdown(f"{badge} {ev.get('text', '')}", unsafe_allow_html=True)


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
    """把上传解析出的论文持久化到磁盘（data/uploaded/），刷新/重启/切换页面都不丢。"""
    import time

    base = (paper_data.get("id") or "uploaded").strip() or "uploaded"
    pid = base
    # 避免覆盖已有文件（同名则加时间戳）
    if os.path.exists(os.path.join(UPLOADED_DIR, f"{pid}.json")):
        pid = f"{base}_{int(time.time())}"

    paper_data["id"] = pid
    paper_data["_dynamic"] = True

    os.makedirs(UPLOADED_DIR, exist_ok=True)
    with open(os.path.join(UPLOADED_DIR, f"{pid}.json"), "w", encoding="utf-8") as f:
        json.dump(paper_data, f, ensure_ascii=False, indent=2)

    # 同时存内存，供当前会话快速访问
    st.session_state.dynamic_papers[pid] = paper_data
    return pid


def start_paper(paper_id):
    """开始/进入一篇论文：重置训练进度。"""
    st.session_state.paper_id = paper_id
    st.session_state.step_index = 0
    st.session_state.guess_submitted = False
    st.session_state.guess_choice = None
    st.session_state.limitation_choice = None


# ---------------------------------------------------------------------------
# API Key 读取（供各页面调用 DeepSeek）
# ---------------------------------------------------------------------------
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

    # 方式二：直接读本地 .streamlit/secrets.toml（兜底）
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
