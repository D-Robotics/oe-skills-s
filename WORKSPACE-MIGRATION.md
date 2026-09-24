# Workspace migration

This release installs into `.drobotics-s/`. S and X5 use separate sibling directories `.drobotics-s/` and `.drobotics-x5/`.

Run `bash setup.sh --update <project-root>` from the new release. The installer refreshes its recognized routing blocks in existing AGENTS.md and CLAUDE.md. User rules are retained.

Legacy workspaces (`.horizon/` for S, `.drobotics/` for X5) remain untouched. Review and migrate board/environment configuration before running tasks; recreate virtual environments at the new path rather than moving them. Do not copy old Skill code over the new release.

As before, `--update --force` rebuilds only this pack's new workspace. Back up changes made inside that managed directory before forcing an update.

## Branding and SDK identifiers

Own resource root: `drobotics-s/`; workspace rules: `DROBOTICS-S.md`; CLI Skill: `s-tc-ui` under `skills/tc_ui/`. Public product names use the S series.

External SDK identifiers retain their actual names: `horizon_plugin_pytorch`, `horizon_tc_ui`, wheel/Docker names, `/opt/horizon/`, compiler march values, and existing service URLs. These are compatibility identifiers, not product branding. Original copyright notices remain attributed to their authors.

Official S-series reference checked: https://developer.d-robotics.cc/oe_s_doc/guide/plugin/plugin_api_reference/march (still declares `horizon_plugin_pytorch.march.March`). No alternative module name was verified.
