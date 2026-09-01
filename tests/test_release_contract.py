import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROOT / "horizon" / "skills"
CREATE_APP_TOKEN_ACTION = (
    "actions/create-github-app-token@"
    "fee1f7d63c2ff003460e3d139729b119787bc349"
)


def frontmatter(text: str, path: Path) -> str:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"missing YAML frontmatter: {path}")
    return match.group(1)


def shell_path(path: Path) -> str:
    if path.drive:
        return f"/mnt/{path.drive[0].lower()}{path.as_posix()[2:]}"
    return str(path)


class ReleaseContractTests(unittest.TestCase):
    def test_every_s_skill_has_v1_release_frontmatter(self):
        skill_paths = sorted(SKILLS_ROOT.rglob("SKILL.md"))
        self.assertTrue(skill_paths, "expected packaged S skills")

        for path in skill_paths:
            header = frontmatter(path.read_text(encoding="utf-8"), path)
            self.assertRegex(header, r"(?m)^name:\s*[^\s].*$", path)
            self.assertRegex(header, r"(?m)^description:\s*[^\s].*$", path)
            self.assertRegex(header, r"(?m)^version:\s*1\.0\.0\s*$", path)
            self.assertRegex(header, r"(?m)^license:\s*Apache-2\.0\s*$", path)

    def test_source_version_is_v1_release(self):
        self.assertEqual((ROOT / "horizon" / "VERSION").read_text(encoding="utf-8").strip(), "1.0.0")

    def test_skill_index_versions_match_indexed_skill_frontmatter(self):
        index = json.loads((ROOT / "horizon" / "skill-index.json").read_text(encoding="utf-8"))
        skill_paths = sorted(SKILLS_ROOT.rglob("SKILL.md"))

        for name, entry in index["paths"].items():
            skill_path = ROOT / "horizon" / entry["skillFile"].removeprefix(".horizon/")
            if not skill_path.exists():
                skill_path = next(
                    (
                        path
                        for path in skill_paths
                        if re.search(r"(?m)^name:\s*" + re.escape(name) + r"\s*$", frontmatter(path.read_text(encoding="utf-8"), path))
                    ),
                    skill_path,
                )
            self.assertTrue(skill_path.exists(), name)
            header = frontmatter(skill_path.read_text(encoding="utf-8"), skill_path)
            version = re.search(r"(?m)^version:\s*(\S+)\s*$", header)
            self.assertIsNotNone(version, name)
            self.assertEqual(entry["version"], version.group(1), name)
            self.assertEqual(entry["version"], "1.0.0", name)

    def test_setup_records_the_requested_release_ref(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            (project / "AGENTS.md").write_text("# Project rules\n", encoding="utf-8")

            result = subprocess.run(
                ["bash", "setup.sh", "--ref", "v1.0.0", shell_path(project)],
                cwd=ROOT,
                check=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )

            self.assertEqual((project / ".horizon" / "VERSION").read_text(encoding="utf-8").strip(), "1.0.0")
            self.assertEqual((project / ".horizon" / "INSTALLED_REF").read_text(encoding="utf-8").strip(), "v1.0.0")
            self.assertNotIn("No such file", result.stderr)

    def test_setup_update_treats_a_crlf_version_as_current(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            (project / "AGENTS.md").write_text("# Project rules\n", encoding="utf-8")

            subprocess.run(
                ["bash", "setup.sh", shell_path(project)],
                cwd=ROOT,
                check=True,
            )
            destination = project / ".horizon"
            (destination / "VERSION").write_bytes(b"1.0.0\r\n")
            retained = destination / "retained-on-noop"
            retained.write_text("keep", encoding="utf-8")

            result = subprocess.run(
                ["bash", "setup.sh", "--update", shell_path(project)],
                cwd=ROOT,
                check=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )

            self.assertIn("Already up to date (1.0.0)", result.stdout)
            self.assertTrue(retained.exists())

    def test_published_release_notifies_hub_with_verified_payload(self):
        workflow_path = ROOT / ".github" / "workflows" / "notify-hub-release.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        document = yaml.load(workflow, Loader=yaml.BaseLoader)

        self.assertEqual(document["on"], {"release": {"types": ["published"]}})
        self.assertEqual(document["permissions"], {"contents": "read"})
        self.assertIn("RDK_RELEASE_DISPATCHER_PRIVATE_KEY", workflow)
        self.assertIn("github.event.release.prerelease", workflow)
        self.assertIn(CREATE_APP_TOKEN_ACTION, workflow)
        self.assertIn(
            "repos/D-Robotics/rdk-skills/actions/workflows/component-upgrade.yml/dispatches",
            workflow,
        )
        self.assertIn("^[0-9a-fA-F]{40}$", workflow)

        token_step = next(
            step
            for step in document["jobs"]["notify-hub"]["steps"]
            if step.get("uses") == CREATE_APP_TOKEN_ACTION
        )
        self.assertEqual(
            token_step["with"]["app-id"],
            "${{ vars.RDK_RELEASE_DISPATCHER_APP_ID }}",
        )
        self.assertEqual(
            token_step["with"]["private-key"],
            "${{ secrets.RDK_RELEASE_DISPATCHER_PRIVATE_KEY }}",
        )
        self.assertEqual(token_step["with"]["permission-actions"], "write")
        self.assertNotIn("permission-contents", token_step["with"])

        expected_payload_fields = {
            "schema_version",
            "source_repo",
            "tag",
            "release_url",
            "target_sha",
            "published_at",
        }
        self.assertEqual(
            set(document["jobs"]["notify-hub"]["steps"][-1]["env"]),
            expected_payload_fields,
        )


if __name__ == "__main__":
    unittest.main()
