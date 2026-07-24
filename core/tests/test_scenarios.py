from core.scenarios.schema import load_scenario, list_scenarios
from core.scenarios.engine import ACTIONS


def test_tiktok_scenario_loads():
    sc = load_scenario("tiktok_upload")
    assert sc.name == "tiktok_upload"
    assert sc.platform == "tiktok"
    assert sc.total_steps == 13
    assert sc.steps[0].action == "ensure_vpn"
    assert sc.steps[-1].action == "verify"


def test_all_scenario_actions_are_known():
    for name in list_scenarios():
        for step in load_scenario(name).steps:
            assert step.action in ACTIONS, f"unknown action {step.action} in {name}"


def test_scenarios_listed():
    assert "tiktok_upload" in list_scenarios()
