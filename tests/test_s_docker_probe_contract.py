from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SDockerProbeContractTests(unittest.TestCase):
    def test_default_docker_path_probes_cached_image_without_local_package_config(self):
        policy = (ROOT / "drobotics-s" / "DROBOTICS-S.md").read_text(encoding="utf-8")
        router = (ROOT / "drobotics-s" / "skills" / "drobotics-router" / "SKILL.md").read_text(encoding="utf-8")
        detection = (
            ROOT
            / "drobotics-s"
            / "skills"
            / "drobotics-router"
            / "oe-package-detection"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        for document in (policy, router, detection):
            self.assertIn("probe_environment.py", document)
            self.assertIn("缓存镜像", document)
        self.assertIn("--workflow ptq", router)
        self.assertIn("不要求", router)
        self.assertNotIn("未检测到 OE 包环境配置", router)
        self.assertIn("不要求实际 OE 包或 `OE_DIR`", policy)
        self.assertIn("明确选择在宿主机执行", detection)
        self.assertIn("仅需 OE 包内资产", detection)
        self.assertIn("不要因为需要本地路径就设 `EXECUTION_MODE=local`", detection)
        self.assertIn("OE_DIR", detection)
        self.assertNotIn("`.env.oe-package` 不存在或不完整", router)

    def test_setup_installs_and_verifies_the_environment_probe_script(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")

        self.assertIn('"$DROBOTICS_SRC/scripts"', setup)
        self.assertIn('"$DROBOTICS_DST/scripts/probe_environment.py"', setup)
        self.assertIn("probe_environment.py", setup)

        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory)
            subprocess.run(
                ["bash", str(ROOT / "setup.sh"), str(project)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            installed = project / ".drobotics-s" / "scripts" / "probe_environment.py"
            self.assertTrue(installed.is_file())
            self.assertFalse((project / ".drobotics-s" / "scripts" / "__pycache__").exists())
            self.assertEqual(
                installed.read_bytes(),
                (ROOT / "drobotics-s" / "scripts" / "probe_environment.py").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
