from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_skills_registry_exists_and_lists_demo_skills():
    registry = (ROOT / "skills" / "registry.yaml").read_text(encoding="utf-8")
    assert "skill_business_website_signal" in registry
    assert "skill_wayback_continuity" in registry
    assert "tool_check_business_website" in registry
    assert "tool_check_wayback_history" in registry


def test_each_demo_skill_has_docs_and_toolset():
    for skill_id, tool_id in [
        ("skill_business_website_signal", "tool_check_business_website"),
        ("skill_wayback_continuity", "tool_check_wayback_history"),
    ]:
        skill_dir = ROOT / "skills" / skill_id
        skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        toolset = (skill_dir / "toolset.yaml").read_text(encoding="utf-8")
        assert "Purpose:" in skill_md
        assert tool_id in skill_md
        assert tool_id in toolset
