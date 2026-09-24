import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "drobotics-s" / "scripts" / "probe_environment.py"
CPU_37 = "registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0"
GPU_37 = "registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_gpu:v3.7.0"
CPU_38 = "registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.8.0"


class SEnvironmentProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        self.docker_log = self.root / "docker-calls.jsonl"
        self._write_executable(
            self.bin_dir / "docker",
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

Path(os.environ["PROBE_DOCKER_LOG"]).open("a").write(
    json.dumps(sys.argv[1:]) + "\\n"
)
args = sys.argv[1:]
if args[:2] == ["image", "ls"]:
    print(os.environ.get("PROBE_DOCKER_IMAGES", ""), end="")
elif args[:2] == ["image", "inspect"]:
    if os.environ.get("PROBE_DOCKER_INSPECT_FAIL"):
        print("registry credential=do-not-print", file=sys.stderr)
        raise SystemExit(1)
    print("sha256:0123456789abcdef")
elif args[:1] == ["run"]:
    if os.environ.get("PROBE_DOCKER_RUN_FAIL"):
        print("private token=do-not-print", file=sys.stderr)
        raise SystemExit(7)
    command = args[-1]
    if "horizon_plugin_pytorch" in command:
        qat_rc = "0"
        device = "gpu" if "--gpus" in args else "cpu"
    else:
        qat_rc = "not_checked"
        device = "not_checked"
    print(f"S_OE_PROBE:compile=0:config=0:qat={qat_rc}:device={device}")
else:
    print("unexpected docker operation", file=sys.stderr)
    raise SystemExit(2)
""",
        )
        self.base_env = os.environ.copy()
        self.base_env.update(
            {
                "PATH": f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                "PROBE_DOCKER_LOG": str(self.docker_log),
                "PROBE_DOCKER_IMAGES": f"{CPU_37}\n{GPU_37}\n",
            }
        )
        self.base_env.pop("OE_DIR", None)
        self.base_env.pop("OE_DROBOTICS_DOCKER_IMAGE", None)
        self.base_env.pop("OE_DROBOTICS_EXECUTION_MODE", None)

    def tearDown(self):
        self.temporary.cleanup()

    def _write_executable(self, path, content):
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def _run_probe(self, *args, **env_updates):
        env = self.base_env.copy()
        env.update({key: str(value) for key, value in env_updates.items()})
        return subprocess.run(
            [sys.executable, "-B", str(PROBE), *args],
            cwd=self.project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _result(self, process):
        if not process.stdout.strip():
            self.fail(f"probe must emit JSON on stdout; exit={process.returncode}, stderr={process.stderr!r}")
        result = json.loads(process.stdout)
        expected_code = 0 if result["status"] == "ready" else 2
        self.assertEqual(process.returncode, expected_code, process.stderr)
        return result

    def _docker_calls(self):
        if not self.docker_log.exists():
            return []
        return [json.loads(line) for line in self.docker_log.read_text().splitlines()]

    def test_ptq_can_use_cached_image_without_oe_package_or_host_tools(self):
        result = self._result(self._run_probe())

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["execution_mode"], "docker")
        self.assertEqual(result["image"], CPU_37)
        self.assertEqual(result["missing"], [])
        self.assertTrue(result["checks"]["hb_compile"]["ok"])
        self.assertTrue(result["checks"]["hb_config_generator"]["ok"])
        self.assertFalse((self.project / ".drobotics-s" / ".env.oe-package").exists())

        run_call = next(call for call in self._docker_calls() if call[0] == "run")
        self.assertIn("--network", run_call)
        self.assertIn("none", run_call)
        self.assertIn("--read-only", run_call)
        self.assertIn("--pull=never", run_call)
        self.assertNotIn("--gpus", run_call)
        command = run_call[-1]
        self.assertIn("hb_compile --help", command)
        self.assertIn("hb_config_generator --help", command)
        self.assertFalse(any(call and call[0] == "pull" for call in self._docker_calls()))

    def test_environment_version_selects_matching_cached_image_without_oe_dir(self):
        env_file = self.project / ".drobotics-s" / ".env.oe-package"
        env_file.parent.mkdir()
        env_file.write_text(
            "OE_VERSION=3.7.0\nEXECUTION_MODE=docker\n"
            "DOCKER_EXEC_PREFIX=docker run --password=private-value\n",
            encoding="utf-8",
        )
        process = self._run_probe(
            "--workflow",
            "ptq",
            PROBE_DOCKER_IMAGES=f"{CPU_37}\n{CPU_38}\n",
        )
        result = self._result(process)

        self.assertEqual(result["image"], CPU_37)
        self.assertEqual(result["status"], "ready")
        self.assertNotIn("private-value", process.stdout)
        self.assertNotIn("DOCKER_EXEC_PREFIX", process.stdout)

    def test_multiple_cached_versions_are_blocked_without_an_oe_version_hint(self):
        result = self._result(
            self._run_probe(PROBE_DOCKER_IMAGES=f"{CPU_37}\n{CPU_38}\n")
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["image"])
        self.assertTrue(result["missing"])
        self.assertFalse(any(call[0] == "run" for call in self._docker_calls()))

    def test_explicit_image_overrides_ambiguous_cache_and_is_checked_without_listing(self):
        result = self._result(
            self._run_probe(
                "--image",
                CPU_37,
                PROBE_DOCKER_IMAGES=f"{CPU_37}\n{CPU_38}\n",
            )
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["image"], CPU_37)
        calls = self._docker_calls()
        self.assertFalse(any(call[:2] == ["image", "ls"] for call in calls))
        self.assertTrue(any(call[:2] == ["image", "inspect"] for call in calls))

    def test_qat_alone_selects_gpu_image_and_requests_gpu_visibility(self):
        result = self._result(
            self._run_probe(
                "--workflow",
                "qat",
                OE_DROBOTICS_DOCKER_IMAGE=GPU_37,
            )
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["image"], GPU_37)
        self.assertTrue(result["checks"]["qat_cuda"]["ok"])
        run_call = next(call for call in self._docker_calls() if call[0] == "run")
        self.assertIn("--gpus", run_call)
        self.assertIn("all", run_call)
        self.assertIn("torch.cuda.is_available()", run_call[-1])

    def test_qat_cpu_image_checks_packages_without_requesting_gpu(self):
        result = self._result(
            self._run_probe("--workflow", "qat", "--image", CPU_37)
        )

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["checks"]["qat_packages"]["ok"])
        run_call = next(call for call in self._docker_calls() if call[0] == "run")
        self.assertNotIn("--gpus", run_call)
        self.assertIn("import torch, horizon_plugin_pytorch", run_call[-1])

    def test_explicit_local_mode_validates_package_and_host_tools_without_docker(self):
        oe_dir = self.root / "oe-package"
        (oe_dir / "package").mkdir(parents=True)
        (oe_dir / "samples").mkdir()
        for command in ("hb_compile", "hb_config_generator"):
            self._write_executable(self.bin_dir / command, "#!/bin/sh\nexit 0\n")

        result = self._result(
            self._run_probe(
                "--execution-mode",
                "local",
                OE_DIR=oe_dir,
                OE_VERSION="3.7.0",
            )
        )

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["execution_mode"], "local")
        self.assertTrue(result["checks"]["oe_package"]["ok"])
        self.assertTrue(result["checks"]["hb_compile"]["ok"])
        self.assertFalse(self._docker_calls())
        self.assertNotIn(str(oe_dir), json.dumps(result))

    def test_explicit_local_mode_without_package_is_blocked_and_does_not_fall_back_to_docker(self):
        result = self._result(
            self._run_probe("--execution-mode", "local")
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["execution_mode"], "local")
        self.assertIn("OE package", " ".join(result["missing"]))
        self.assertFalse(self._docker_calls())

    def test_malformed_local_package_path_is_blocked_without_echoing_config(self):
        env_file = self.project / ".drobotics-s" / ".env.oe-package"
        env_file.parent.mkdir()
        env_file.write_bytes(
            b"EXECUTION_MODE=local\nOE_VERSION=3.7.0\nOE_DIR=/tmp/private\x00token\n"
        )
        process = self._run_probe()
        result = self._result(process)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("OE package", " ".join(result["missing"]))
        self.assertNotIn("private", process.stdout)
        self.assertNotIn("token", process.stdout)
        self.assertFalse(self._docker_calls())

    def test_probe_output_hides_docker_error_details_and_invalid_image_values(self):
        process = self._run_probe(
            "--image",
            "registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_22_s100_s600_cpu:v3.7.0?token=private-value",
        )
        result = self._result(process)

        self.assertEqual(result["status"], "blocked")
        self.assertNotIn("private-value", process.stdout)
        self.assertNotIn("private-value", process.stderr)

        process = self._run_probe(PROBE_DOCKER_RUN_FAIL="1")
        result = self._result(process)
        self.assertEqual(result["status"], "blocked")
        self.assertNotIn("do-not-print", process.stdout)
        self.assertNotIn("do-not-print", process.stderr)


if __name__ == "__main__":
    unittest.main()
