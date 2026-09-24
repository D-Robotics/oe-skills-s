# Changelog

## [1.1.2] - 2026-09-24

- Make the package-detection trigger consistent with the default cached-Docker PTQ workflow.
- Clarify that package-internal assets do not imply host-local tool execution.
- Remove bundled OE code snapshots that could be mistaken for current or official documentation.
- Align release metadata and the TC UI display module key with D Robotics naming while preserving external package identifiers.

## [1.1.1] - 2026-09-24

- Retrieve current S OpenExplorer facts through the official RDK documentation MCP; local notes remain workflow aids.
- Probe locally cached Docker images before PTQ or QAT without requiring an extracted OE package.
- Keep OE package assets separate from explicit host execution and clarify CPU/GPU QAT environment checks.

## [1.1.0] - 2026-09-24

- Route ordinary floating-point deployment through PTQ first, including PyTorch-to-ONNX evaluation.
- Align OE environment guidance with the current S-series package and version-matched Docker images.
- Clarify D-Robotics S-series product naming while retaining external toolchain identifiers.

## [1.0.0] - 2026-08-31

- Establish the unified OE S skills release baseline.
- Normalize packaged Skill release metadata and setup version anchoring.
