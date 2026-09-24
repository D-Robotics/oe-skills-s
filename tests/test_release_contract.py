import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import yaml


ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROOT / "drobotics-s" / "skills"
CHECKOUT_ACTION = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"
CREATE_APP_TOKEN_ACTION = (
    "actions/create-github-app-token@"
    "fee1f7d63c2ff003460e3d139729b119787bc349"
)
MISSING = object()


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
    def test_release_api_validator_accepts_only_published_stable_release(self):
        validator = ROOT / "tools" / "validate_release.py"
        self.assertTrue(validator.is_file(), validator)

        canonical_payload = {
            "tag_name": "v1.0.0",
            "html_url": "https://github.com/D-Robotics/oe-skills-s/releases/tag/v1.0.0",
            "published_at": "2026-08-31T12:00:00Z",
            "draft": False,
            "prerelease": False,
        }
        invalid_mutations = (
            ("wrong tag_name: API v1.0.1 versus requested v1.0.0", "tag_name", "v1.0.1", "Release tag does not match the requested stable tag\n"),
            ("missing tag_name", "tag_name", MISSING, "Release tag_name must be a non-empty single-line string\n"),
            ("malformed tag_name", "tag_name", ["v1.0.0"], "Release tag_name must be a non-empty single-line string\n"),
            ("wrong html_url: noncanonical URL", "html_url", "https://example.test/releases/tag/v1.0.0", "Release URL is not canonical for the requested repository and tag\n"),
            ("missing html_url", "html_url", MISSING, "Release html_url must be a non-empty single-line string\n"),
            ("malformed html_url", "html_url", 1, "Release html_url must be a non-empty single-line string\n"),
            ("wrong published_at: empty time", "published_at", "", "Release published_at must be a non-empty single-line string\n"),
            ("missing published_at time", "published_at", MISSING, "Release published_at must be a non-empty single-line string\n"),
            ("malformed published_at", "published_at", {}, "Release published_at must be a non-empty single-line string\n"),
            ("wrong draft: true", "draft", True, "Release must be published, non-draft, and non-prerelease\n"),
            ("missing draft", "draft", MISSING, "Release must be published, non-draft, and non-prerelease\n"),
            ("malformed draft", "draft", "false", "Release must be published, non-draft, and non-prerelease\n"),
            ("wrong prerelease: true", "prerelease", True, "Release must be published, non-draft, and non-prerelease\n"),
            ("missing prerelease", "prerelease", MISSING, "Release must be published, non-draft, and non-prerelease\n"),
            ("malformed prerelease", "prerelease", 0, "Release must be published, non-draft, and non-prerelease\n"),
        )

        result = subprocess.run(
            [sys.executable, str(validator), "v1.0.0", "D-Robotics/oe-skills-s"],
            input=json.dumps(canonical_payload), text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "tag=v1.0.0\nrelease_url=https://github.com/D-Robotics/oe-skills-s/releases/tag/v1.0.0\npublished_at=2026-08-31T12:00:00Z\n",
        )

        for name, field, value, expected_error in invalid_mutations:
            with self.subTest(name=name):
                payload = canonical_payload.copy()
                if value is MISSING:
                    del payload[field]
                else:
                    payload[field] = value
                result = subprocess.run(
                    [sys.executable, str(validator), "v1.0.0", "D-Robotics/oe-skills-s"],
                    input=json.dumps(payload), text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 1, result)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, expected_error)

    def test_every_s_skill_has_v1_release_frontmatter(self):
        skill_paths = sorted(SKILLS_ROOT.rglob("SKILL.md"))
        self.assertTrue(skill_paths, "expected packaged S skills")

        for path in skill_paths:
            header = frontmatter(path.read_text(encoding="utf-8"), path)
            self.assertRegex(header, r"(?m)^name:\s*[^\s].*$", path)
            self.assertRegex(header, r"(?m)^description:\s*[^\s].*$", path)
            self.assertRegex(header, r"(?m)^version:\s*1\.1\.1\s*$", path)
            self.assertRegex(header, r"(?m)^license:\s*Apache-2\.0\s*$", path)

    def test_source_version_is_v1_release(self):
        self.assertEqual((ROOT / "drobotics-s" / "VERSION").read_text(encoding="utf-8").strip(), "1.1.1")

    def test_skill_index_versions_match_indexed_skill_frontmatter(self):
        index = json.loads((ROOT / "drobotics-s" / "skill-index.json").read_text(encoding="utf-8"))
        skill_paths = sorted(SKILLS_ROOT.rglob("SKILL.md"))

        for name, entry in index["paths"].items():
            skill_path = ROOT / "drobotics-s" / entry["skillFile"].removeprefix(".drobotics-s/")
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
            self.assertEqual(entry["version"], "1.1.1", name)

    def test_setup_records_the_requested_release_ref(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            (project / "AGENTS.md").write_text("# Project rules\n", encoding="utf-8")

            result = subprocess.run(
                ["bash", "setup.sh", "--ref", "v1.1.1", shell_path(project)],
                cwd=ROOT,
                check=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )

            self.assertEqual((project / ".drobotics-s" / "VERSION").read_text(encoding="utf-8").strip(), "1.1.1")
            self.assertEqual((project / ".drobotics-s" / "INSTALLED_REF").read_text(encoding="utf-8").strip(), "v1.1.1")
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
            destination = project / ".drobotics-s"
            (destination / "VERSION").write_bytes(b"1.1.1\r\n")
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

            self.assertIn("Already up to date (1.1.1)", result.stdout)
            self.assertTrue(retained.exists())

    def test_release_or_recovery_dispatch_notifies_hub_with_api_verified_payload(self):
        workflow_path = ROOT / ".github" / "workflows" / "notify-hub-release.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        document = yaml.load(workflow, Loader=yaml.BaseLoader)

        self.assertEqual(
            document["on"],
            {
                "release": {"types": ["published"]},
                "workflow_dispatch": {
                    "inputs": {
                        "tag": {
                            "description": "Stable Release tag to recover",
                            "required": "true",
                            "type": "string",
                        }
                    }
                },
            },
        )
        self.assertEqual(document["permissions"], {"contents": "read"})
        self.assertNotIn("if", document["jobs"]["notify-hub"])
        steps = document["jobs"]["notify-hub"]["steps"]
        self.assertEqual(
            [step["uses"] for step in steps if "uses" in step],
            [CHECKOUT_ACTION, CREATE_APP_TOKEN_ACTION],
        )
        checkout_step = steps[0]
        self.assertEqual(checkout_step["uses"], CHECKOUT_ACTION)
        self.assertEqual(
            checkout_step["with"],
            {
                "ref": "${{ github.event.repository.default_branch }}",
                "persist-credentials": "false",
            },
        )

        release_step = next(
            step
            for step in steps
            if step.get("id") == "release"
        )
        self.assertEqual(
            release_step["env"],
            {"tag": "${{ inputs.tag || github.event.release.tag_name }}"},
        )
        resolve_step = next(
            step
            for step in steps
            if step.get("name") == "Resolve the verified release tag to its commit SHA"
        )
        self.assertEqual(resolve_step.get("id"), "resolve")
        self.assertEqual(resolve_step["env"], {"tag": "${{ steps.release.outputs.tag }}"})
        self.assertIn("^[0-9a-fA-F]{40}$", resolve_step["run"])

        token_step = next(
            step
            for step in steps
            if step.get("uses") == CREATE_APP_TOKEN_ACTION
        )
        self.assertEqual(
            token_step["with"],
            {
                "app-id": "${{ vars.RDK_RELEASE_DISPATCHER_APP_ID }}",
                "private-key": "${{ secrets.RDK_RELEASE_DISPATCHER_PRIVATE_KEY }}",
                "owner": "D-Robotics",
                "repositories": "rdk-skills",
                "permission-actions": "write",
            },
        )

        dispatch_step = steps[-1]
        self.assertEqual(
            dispatch_step["env"],
            {
                "schema_version": "1",
                "source_repo": "${{ github.repository }}",
                "tag": "${{ steps.release.outputs.tag }}",
                "release_url": "${{ steps.release.outputs.release_url }}",
                "target_sha": "${{ steps.resolve.outputs.target_sha }}",
                "published_at": "${{ steps.release.outputs.published_at }}",
            },
        )

        release_url = "https://api.github.com/repos/${GITHUB_REPOSITORY}/releases/tags/$tag"
        commit_url = "https://api.github.com/repos/${GITHUB_REPOSITORY}/commits/$tag"
        hub_url = "https://api.github.com/repos/D-Robotics/rdk-skills/actions/workflows/component-upgrade.yml/dispatches"
        request_method = r"(?i)(?:--request(?:=|\s+)|-X\s*)([A-Z]+)\b"
        source_write_body = r"(?i)(?:^|\s)(?:-d|--data(?:-[a-z]+)?|--json|--form(?:-string)?|-F|--upload-file|-T)(?:=|\s)"
        for source_run, expected_url in (
            (release_step["run"], release_url),
            (resolve_step["run"], commit_url),
        ):
            with self.subTest(source_get=expected_url):
                self.assertEqual(len(re.findall(r"\bcurl\b", source_run)), 1)
                self.assertEqual(source_run.count("https://api.github.com/"), 1)
                self.assertEqual(
                    re.findall(r'"(https://api\.github\.com/repos/[^"]+)"', source_run),
                    [expected_url],
                )
                self.assertEqual(
                    source_run.count('Authorization: Bearer ${{ github.token }}'),
                    1,
                )
                self.assertEqual(re.findall(request_method, source_run), [])
                self.assertNotRegex(source_run, r"(?i)(?:^|\s)(?:--head|-I)(?:=|\s|$)")
                self.assertNotRegex(source_run, source_write_body)

        self.assertIn(
            'python3 tools/validate_release.py "$tag" "$GITHUB_REPOSITORY"',
            release_step["run"],
        )
        dispatch_run = dispatch_step["run"]
        self.assertEqual(dispatch_run.count("https://api.github.com/"), 1)
        self.assertEqual(
            re.findall(r'"(https://api\.github\.com/repos/[^"]+)"', dispatch_run),
            [hub_url],
        )
        self.assertEqual(
            re.findall(request_method, dispatch_run),
            ["POST"],
        )
        self.assertEqual(
            dispatch_run.count('Authorization: Bearer ${{ steps.app-token.outputs.token }}'),
            1,
        )
        self.assertIn('--data "$payload"', dispatch_run)

        normalized_dispatch = " ".join(dispatch_run.split())
        expected_payload_literal = (
            "'{ref: \"main\", inputs: { "
            "schema_version: ($schema_version | tostring), "
            "source_repo: $source_repo, tag: $tag, release_url: $release_url, "
            "target_sha: $target_sha, published_at: $published_at, dry_run: \"false\" }}'"
        )
        self.assertEqual(normalized_dispatch.count(expected_payload_literal), 1)
        self.assertIn('--argjson schema_version "$schema_version"', dispatch_run)

        all_runs = "\n".join(step.get("run", "") for step in steps)
        self.assertEqual(len(re.findall(r"\bcurl\b", all_runs)), 3)
        self.assertEqual(all_runs.count("https://api.github.com/"), 3)
        self.assertEqual(
            re.findall(r'"(https://api\.github\.com/repos/[^"]+)"', all_runs),
            [release_url, commit_url, hub_url],
        )
        self.assertEqual(
            re.findall(request_method, all_runs),
            ["POST"],
        )
        for forbidden in (
            r"(?i)\bgit\s+push\b",
            r"(?i)\bgit\s+tag\b",
            r"(?i)\bgh\s+release\s+(?:create|edit|delete)\b",
            r"(?i)\bgh\s+api\b",
            r"(?i)api\.github\.com/repos/[^\s\"']+/git/(?:refs|tags)(?:/|\b)",
        ):
            self.assertNotRegex(all_runs, forbidden)


if __name__ == "__main__":
    unittest.main()
