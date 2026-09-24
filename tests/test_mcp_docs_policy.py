from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class McpDocsPolicyTests(unittest.TestCase):
    def test_workspace_rules_require_official_docs_mcp_without_local_doc_fallback(self):
        rules = (ROOT / "drobotics-s" / "DROBOTICS-S.md").read_text(encoding="utf-8")

        for required in (
            "mcp__rdk_docs__search_docs",
            "manual=oe-s",
            "source=docs",
            "mcp__rdk_docs__get_page",
            "MCP 工具不可用",
            "报告阻塞",
            "路由",
            "流程",
        ):
            self.assertIn(required, rules)
        self.assertNotIn("oe-mcp", rules)
        self.assertNotIn("本地 references、examples 或 scripts", rules)

    def test_legacy_toolchain_guide_does_not_require_missing_local_manual_index(self):
        guide = (ROOT / "drobotics-s" / "docs" / "DROBOTICS-S.md").read_text(encoding="utf-8")

        self.assertNotIn("oe_docs_3_9_0_rc4", guide)
        self.assertNotIn("oe-mcp", guide)
        self.assertIn("mcp__rdk_docs__search_docs", guide)
        self.assertIn("mcp__rdk_docs__get_page", guide)
        self.assertIn("报告阻塞", guide)

    def test_router_uses_skill_index_for_routing_and_mcp_for_official_facts(self):
        router = (ROOT / "drobotics-s" / "skills" / "drobotics-router" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("mcp__rdk_docs__search_docs", router)
        self.assertIn("MCP 工具不可用", router)
        self.assertIn("skill-index.json", router)
        self.assertNotIn("oe-mcp", router)
        self.assertNotIn("最高权威", router)

    def test_official_docs_reference_is_only_a_link_directory(self):
        reference = (
            ROOT / "drobotics-s" / "skills" / "drobotics-router" / "references" / "oe-s-official-docs.md"
        ).read_text(encoding="utf-8")

        self.assertIn("链接目录", reference)
        self.assertIn("不是官方事实来源", reference)
        self.assertIn("mcp__rdk_docs__search_docs", reference)

    def test_code_snapshot_index_is_not_an_authoritative_doc_route(self):
        index = (ROOT / "drobotics-s" / "docs" / "index.md").read_text(encoding="utf-8")

        self.assertNotIn("oe-mcp", index)
        self.assertNotIn("search_code", index)
        self.assertIn("本地代码快照", index)
        self.assertIn("不能作为官方文档依据", index)

    def test_onboarding_does_not_configure_the_retired_mcp_endpoint(self):
        for relative_path in ("README.md", "README.en.md", "agent-setup.md"):
            with self.subTest(path=relative_path):
                content = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertNotIn("mcp.oe.horizon.auto", content)
                self.assertNotIn('"oe-mcp"', content)
                self.assertIn("mcp__rdk_docs__search_docs", content)

    def test_setup_injects_current_mcp_rule_and_replaces_it_without_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            agents = project / "AGENTS.md"
            agents.write_text("# User rules\nKeep these settings.\n", encoding="utf-8")

            for _ in range(2):
                subprocess.run(
                    ["bash", str(ROOT / "setup.sh"), str(project)],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            installed = agents.read_text(encoding="utf-8")
            self.assertIn("mcp__rdk_docs__search_docs", installed)
            self.assertIn("mcp__rdk_docs__get_page", installed)
            self.assertIn("report a blocker", installed)
            self.assertNotIn("oe-mcp", installed)
            self.assertEqual(installed.count("# D Robotics S Workspace Rules"), 1)
            self.assertIn("# User rules\nKeep these settings.", installed)


if __name__ == "__main__":
    unittest.main()
