import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"missing frontmatter: {path}")
    return match.group(1)


class SDockerPolicyTests(unittest.TestCase):
    def test_package_detection_is_not_triggered_just_by_missing_package_config(self):
        index = json.loads((ROOT / "drobotics-s" / "skill-index.json").read_text(encoding="utf-8"))
        trigger = index["paths"]["oe-package-detection"]["description"]
        frontmatter = read_frontmatter(
            ROOT / "drobotics-s" / "skills" / "drobotics-router" / "oe-package-detection" / "SKILL.md"
        )

        for text in (trigger, frontmatter):
            self.assertIn("普通 PTQ", text)
            self.assertIn("Docker", text)
            self.assertIn("明确", text)
            self.assertNotIn(".env.oe-package 不存在时触发", text)

    def test_readmes_describe_default_cached_docker_without_oe_package(self):
        readmes = {
            "README.md": ("已缓存的 S100/S600 Docker 镜像", "不要求预装 OE package 或设置 `OE_DIR`"),
            "README.en.md": (
                "Docker images already cached locally",
                "does not require an extracted OE package or `OE_DIR`",
            ),
        }
        for relative_path, required_phrases in readmes.items():
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            for phrase in required_phrases:
                with self.subTest(path=relative_path, phrase=phrase):
                    self.assertIn(phrase, content)
            self.assertNotIn("普通 PTQ/QAT 量化编译部署且`.env.oe-package` 缺失", content)
            self.assertNotIn("Normal PTQ/QAT quantization/compilation/deployment and `.env.oe-package` missing", content)

    def test_tc_ui_is_a_display_module_key_and_package_identifier_stays_unchanged(self):
        index = json.loads((ROOT / "drobotics-s" / "skill-index.json").read_text(encoding="utf-8"))
        modules = index["modules"]

        self.assertIn("tc_ui", modules)
        self.assertNotIn("horizon_tc_ui", modules)
        self.assertEqual(modules["tc_ui"]["title"], "D Robotics TC UI")
        self.assertEqual(
            {entry["module"] for entry in index["paths"].values() if entry["module"] is not None}
            - set(modules),
            set(),
        )
        self.assertIn(
            "horizon_tc_ui",
            (ROOT / "drobotics-s" / "skills" / "tc_ui" / "s-tc-ui" / "SKILL.md").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
