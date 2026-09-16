# -*- coding: utf-8 -*-
"""用 Streamlit 官方 AppTest 框架做无头验证，确保页面能真正渲染。"""
from streamlit.testing.v1 import AppTest


def test_home():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"首页报错: {at.exception}"
    texts = " ".join(str(m.value) for m in at.markdown)
    assert "Running VLAs at Real-time Speed" in texts, "首页未显示论文标题"
    print("[OK] 首页渲染正常，论文卡片已显示")


def test_training_scenario():
    at = AppTest.from_file("pages/1_推理训练.py", default_timeout=30)
    at.session_state["paper_id"] = "realtime_vla"
    at.run()
    assert not at.exception, f"训练页报错: {at.exception}"
    texts = " ".join(str(m.value) for m in at.markdown)
    assert "现实问题" in texts, "训练页第一步标题缺失"
    assert "延迟" in texts or "33" in texts, "情境内容未渲染"
    print("[OK] 训练页第 1 步「现实问题」渲染正常")


def test_training_guess_gate():
    # 未提交猜想时，看作者方案应该被门控拦截
    at = AppTest.from_file("pages/1_推理训练.py", default_timeout=30)
    at.session_state["paper_id"] = "realtime_vla"
    at.session_state["step_index"] = 2  # 直接跳到「看作者方案」
    at.run()
    assert not at.exception, f"门控页报错: {at.exception}"
    warnings = " ".join(str(w.value) for w in at.warning)
    assert "先完成上一步" in warnings, f"门控未生效，实际 warning: {warnings}"
    print("[OK] 防剧透门控生效：未提交猜想时，作者方案被拦截")


if __name__ == "__main__":
    test_home()
    test_training_scenario()
    test_training_guess_gate()
    print("\n全部测试通过")
