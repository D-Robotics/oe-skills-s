import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


class PTQFirstInstallContractTests(unittest.TestCase):
    def test_installed_skills_route_exportable_float_models_through_ptq(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            subprocess.run(
                ["bash", "setup.sh", str(project)],
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            )

            workspace = project / ".drobotics-s"
            router = (workspace / "skills/drobotics-router/SKILL.md").read_text(encoding="utf-8")
            decision = router.split("### 量化路径判定门禁", 1)[1].split(
                "### ⛔ 路由后强制读取门禁", 1
            )[0]

            self.assertIn("普通浮点 Caffe / ONNX", decision)
            self.assertIn("默认 PTQ", decision)
            self.assertIn("`.pt` / `.pth`", decision)
            self.assertIn("导出 ONNX", decision)
            self.assertIn("PTQ", decision)
            self.assertIn("明确 QAT 请求", decision)
            self.assertNotIn("必须有用户明确指示才能走 PTQ", decision)
            self.assertNotIn('未说"导出 ONNX" → QAT', decision)

            index = json.loads((workspace / "skill-index.json").read_text(encoding="utf-8"))
            ptq_description = index["paths"]["hmct-workflow"]["description"]
            qat_codegen_description = index["paths"]["s-plugin-hbdk-generating"]["description"]
            self.assertIn("hb_config_generator", ptq_description)
            self.assertIn("hb_compile -c", ptq_description)
            self.assertIn("ONNX", ptq_description)
            self.assertIn("QAT", qat_codegen_description)
            self.assertNotIn("即使用户没有明确说", qat_codegen_description)
            self.assertNotIn("只要涉及从量化到编译的多个步骤都应触发", qat_codegen_description)
            self.assertIn("明确要求 QAT", qat_codegen_description)
            tc_ui_router = (workspace / "skills/tc_ui/s-tc-ui/SKILL.md").read_text(encoding="utf-8")
            accuracy_debug = (workspace / "skills/tc_ui/s-tc-ui/references/tasks/task-accuracy-debug.md").read_text(encoding="utf-8")
            self.assertIn("s-hmct-cosine-similarity-tuning", tc_ui_router)
            self.assertIn("s-plugin-precision-tuning", accuracy_debug)
            self.assertNotIn("horizon-model-cosine-analyzer", tc_ui_router + accuracy_debug)

            package_detection = (workspace / "skills/drobotics-router/oe-package-detection/SKILL.md").read_text(encoding="utf-8")
            deployment = (workspace / "skills/drobotics-router/references/deployment-workflow.md").read_text(encoding="utf-8")
            self.assertIn("默认 `EXECUTION_MODE=docker`", package_detection)
            self.assertIn("OE_VERSION=3.7.0", package_detection)
            self.assertIn('OE_VERSION_TAG="${OE_VERSION#v}"', package_detection)
            self.assertIn("ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0", package_detection)
            self.assertIn('OE_VERSION_TAG="${OE_VERSION#v}"', deployment)
            self.assertNotIn("torch.cuda.is_available() = True", package_detection + deployment)


if __name__ == "__main__":
    unittest.main()
