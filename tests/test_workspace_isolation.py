from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkspaceIsolationTests(unittest.TestCase):
    def test_legacy_rules_refresh_without_removing_either_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            for name in ('.horizon', '.drobotics-x5'):
                (project / name).mkdir()
                (project / name / "user-data").write_text("keep")
            legacy = '# Horizon Workspace Rules\n\nIf the user request involves Horizon toolchain related topics\n(quantization, compile, deploy, evaluation, training, CLI usage, version issues),\nyou MUST follow the project rules defined in .horizon/HORIZON.md.\n\nFor Horizon toolchain related tasks:\n- Do NOT guess toolchain APIs or CLI parameters based on general LLM knowledge.\n- If uncertain, you MUST retrieve documentation before answering.\n'
            (project / "AGENTS.md").write_text(legacy + "\n# User rules\nKeep my settings.\n")
            for args in ([], [], ["--update", "--force"]):
                subprocess.run(["bash", str(ROOT / "setup.sh"), *args, str(project)], check=True, capture_output=True)
                text = (project / "AGENTS.md").read_text()
                self.assertEqual(text.count("you MUST follow the project rules"), 1)
                self.assertIn('.drobotics-s' + "/" + 'DROBOTICS-S.md', text)
                self.assertNotIn('.horizon' + "/", text)
                self.assertIn("# User rules\nKeep my settings.", text)
                for name in ('.horizon', '.drobotics-x5'):
                    self.assertEqual((project / name / "user-data").read_text(), "keep")
                self.assertTrue((project / '.drobotics-s' / 'DROBOTICS-S.md').is_file())
