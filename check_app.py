# -*- coding: utf-8 -*-
"""一键自检：确认 10 步训练流程、首页上传、门控均正常。"""
from streamlit.testing.v1 import AppTest


def check():
    # 1. 首页渲染 + 上传区
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    print("1. 首页渲染异常:", at.exception or "无")
    texts = " ".join(str(m.value) for m in at.markdown)
    print("   含「上传论文」:", "上传论文" in texts)

    # 2. 训练页第 1 步（为什么值得读）
    at2 = AppTest.from_file("pages/1_推理训练.py", default_timeout=30)
    at2.session_state["paper_id"] = "realtime_vla"
    at2.run()
    print("2. 训练页第1步渲染异常:", at2.exception or "无")
    t2 = " ".join(str(m.value) for m in at2.markdown)
    print("   标题含「为什么值得读」:", "为什么值得读" in t2)

    # 3. 第 5 步（如果是你）渲染
    at3 = AppTest.from_file("pages/1_推理训练.py", default_timeout=30)
    at3.session_state["paper_id"] = "realtime_vla"
    at3.session_state["step_index"] = 4
    at3.run()
    print("3. 第5步「如果是你」渲染异常:", at3.exception or "无")

    # 4. 门控：第 6 步（作者怎么解决）未提交猜想应被拦截
    at4 = AppTest.from_file("pages/1_推理训练.py", default_timeout=30)
    at4.session_state["paper_id"] = "realtime_vla"
    at4.session_state["step_index"] = 5
    at4.run()
    warns = " ".join(str(w.value) for w in at4.warning)
    print("4. 防剧透门控生效:", "先完成上一步" in warns)

    # 5. 第 10 步（下一个研究问题）渲染
    at5 = AppTest.from_file("pages/1_推理训练.py", default_timeout=30)
    at5.session_state["paper_id"] = "realtime_vla"
    at5.session_state["step_index"] = 9
    at5.run()
    print("5. 第10步「下一个研究问题」渲染异常:", at5.exception or "无")


if __name__ == "__main__":
    check()
