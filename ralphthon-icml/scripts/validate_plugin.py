#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Validate this repository against the Claude Code plugin contract.

Claude Code discovers plugin skills at `skills/<name>/SKILL.md` and reads the
plugin manifest from `.claude-plugin/plugin.json`.  Distribution through
`/plugin marketplace add` additionally requires `.claude-plugin/marketplace.json`.

The runtime silently ignores unrecognized manifest and frontmatter fields, so a
Codex-era leftover would never raise an error at load time -- it would just stop
working.  This validator fails closed on those instead.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Final, NamedTuple


ROOT: Final = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST: Final = Path(".claude-plugin") / "plugin.json"
MARKETPLACE_MANIFEST: Final = Path(".claude-plugin") / "marketplace.json"
PLUGIN_NAME: Final = "ralphthon-icml"

# Required in this repository.  `name` is the only field Claude Code itself
# requires, but a distributed plugin without the rest is a bad citizen.
PLUGIN_FIELDS: Final = (
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
)
# Fields Claude Code does not understand.  Present only in the Codex manifest.
PLUGIN_FORBIDDEN_FIELDS: Final = ("interface", "commands")
MARKETPLACE_FIELDS: Final = ("name", "owner", "plugins")

KEBAB_CASE: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK: Final = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# `description` (combined with `when_to_use`) is truncated by the runtime at
# 1536 characters.  Stay clearly inside it so nothing is silently cut.
DESCRIPTION_LIMIT: Final = 1024

# Codex-era paths.  Their continued presence means the migration regressed.
LEGACY_PATHS: Final = (
    Path(".codex-plugin"),
    Path(".agents"),
    Path("commands"),
)


class ValidationError(NamedTuple):
    path: Path
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> list[str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return []
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:index]
    return []


def top_level_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def discover_skill_paths(root: Path) -> list[Path]:
    return sorted((root / "skills").glob("*/SKILL.md"))


def add_error(
    errors: list[ValidationError], root: Path, path: Path, message: str
) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    errors.append(ValidationError(relative, message))


def validate_plugin_manifest(root: Path, errors: list[ValidationError]) -> None:
    path = root / PLUGIN_MANIFEST
    if not path.is_file():
        add_error(errors, root, path, "required file is missing")
        return
    try:
        manifest = json.loads(read_text(path))
    except json.JSONDecodeError as error:
        add_error(errors, root, path, f"invalid JSON: {error}")
        return

    for field in PLUGIN_FIELDS:
        if not manifest.get(field):
            add_error(errors, root, path, f"missing field: {field}")
    for field in PLUGIN_FORBIDDEN_FIELDS:
        if field in manifest:
            add_error(
                errors,
                root,
                path,
                f"Claude Code does not support the {field!r} field; "
                "it is silently ignored",
            )
    name = manifest.get("name")
    if name != PLUGIN_NAME:
        add_error(errors, root, path, f"name must be {PLUGIN_NAME}")
    if isinstance(name, str) and not KEBAB_CASE.fullmatch(name):
        add_error(errors, root, path, f"name must be kebab-case: {name}")


def validate_marketplace_manifest(root: Path, errors: list[ValidationError]) -> None:
    path = root / MARKETPLACE_MANIFEST
    if not path.is_file():
        add_error(
            errors,
            root,
            path,
            "required file is missing; /plugin marketplace add cannot install "
            "this repository without it",
        )
        return
    try:
        manifest = json.loads(read_text(path))
    except json.JSONDecodeError as error:
        add_error(errors, root, path, f"invalid JSON: {error}")
        return

    for field in MARKETPLACE_FIELDS:
        if not manifest.get(field):
            add_error(errors, root, path, f"missing field: {field}")

    owner = manifest.get("owner")
    if isinstance(owner, dict) and not owner.get("name"):
        add_error(errors, root, path, "owner requires a name")

    plugins = manifest.get("plugins")
    if not isinstance(plugins, list):
        return
    names = [entry.get("name") for entry in plugins if isinstance(entry, dict)]
    if PLUGIN_NAME not in names:
        add_error(errors, root, path, f"plugins must advertise {PLUGIN_NAME}")
    for entry in plugins:
        if not isinstance(entry, dict):
            add_error(errors, root, path, "each plugin entry must be an object")
            continue
        if not entry.get("source"):
            add_error(
                errors,
                root,
                path,
                f"plugin entry {entry.get('name')!r} requires a source",
            )
            continue
        source = entry["source"]
        # A local source must resolve, or the install produces an empty plugin.
        if isinstance(source, str) and not (root / source).exists():
            add_error(
                errors,
                root,
                path,
                f"plugin source does not resolve: {source}",
            )


def validate_skill_files(
    root: Path, paths: list[Path], errors: list[ValidationError]
) -> set[str]:
    names: set[str] = set()
    for path in paths:
        lines = frontmatter(read_text(path))
        if not lines:
            add_error(errors, root, path, "frontmatter is missing")
            continue
        values = top_level_values(lines)
        name = values.get("name", "")
        description = values.get("description", "")
        if not name:
            add_error(errors, root, path, "missing frontmatter field: name")
        if not description:
            add_error(errors, root, path, "missing frontmatter field: description")
        if name and name != path.parent.name:
            add_error(
                errors,
                root,
                path,
                f"frontmatter name must match directory name: {path.parent.name}",
            )
        if name and not KEBAB_CASE.fullmatch(name):
            add_error(errors, root, path, f"skill name must be kebab-case: {name}")
        if len(description) > DESCRIPTION_LIMIT:
            add_error(
                errors,
                root,
                path,
                f"description is {len(description)} characters; "
                f"keep it under {DESCRIPTION_LIMIT} so it is not truncated",
            )
        if name in names:
            add_error(errors, root, path, f"duplicate skill name: {name}")
        if name:
            names.add(name)
    return names


def validate_skill_layout(root: Path, errors: list[ValidationError]) -> None:
    """Every SKILL.md must sit exactly one level under skills/.

    A skill nested deeper (the Codex layout, which relied on .agents/ symlinks)
    is not reliably discovered as a top-level Claude Code skill.
    """
    skills = root / "skills"
    if not skills.is_dir():
        add_error(errors, root, skills, "skills/ directory is missing")
        return
    for path in sorted(skills.rglob("SKILL.md")):
        if path.parent.parent != skills:
            add_error(
                errors,
                root,
                path,
                "SKILL.md must be exactly one level under skills/ "
                "(skills/<name>/SKILL.md)",
            )


def validate_no_legacy_artifacts(root: Path, errors: list[ValidationError]) -> None:
    for relative in LEGACY_PATHS:
        path = root / relative
        if path.exists():
            add_error(
                errors,
                root,
                path,
                "Codex-era path is not used by Claude Code; remove it",
            )
    for path in sorted((root / "skills").rglob("openai.yaml")):
        add_error(
            errors,
            root,
            path,
            "Codex UI metadata is ignored by Claude Code; remove it",
        )


def validate_local_markdown_links(root: Path, errors: list[ValidationError]) -> None:
    paths = [root / "README.md", *sorted((root / "skills").rglob("*.md"))]
    for path in paths:
        if not path.is_file():
            continue
        for match in MARKDOWN_LINK.finditer(read_text(path)):
            raw_target = match.group(1).strip().strip("<>")
            if (
                not raw_target
                or raw_target.startswith("#")
                or raw_target.startswith(("https://", "http://", "mailto:"))
            ):
                continue
            target = raw_target.split("#", maxsplit=1)[0]
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                add_error(
                    errors,
                    root,
                    path,
                    f"local Markdown link does not resolve: {raw_target}",
                )


def validate_skill_asset_locality(root: Path, errors: list[ValidationError]) -> None:
    """A skill may only link to files inside its own skill directory.

    An installed plugin cannot resolve paths that escape the skill directory,
    so an out-of-tree link works in the repository and breaks once installed.
    """
    for skill_md in discover_skill_paths(root):
        skill_dir = skill_md.parent
        for path in sorted(skill_dir.rglob("*.md")):
            for match in MARKDOWN_LINK.finditer(read_text(path)):
                raw_target = match.group(1).strip().strip("<>")
                if (
                    not raw_target
                    or raw_target.startswith("#")
                    or raw_target.startswith(("https://", "http://", "mailto:"))
                ):
                    continue
                target = raw_target.split("#", maxsplit=1)[0]
                resolved = (path.parent / target).resolve()
                try:
                    resolved.relative_to(skill_dir.resolve())
                except ValueError:
                    add_error(
                        errors,
                        root,
                        path,
                        f"link escapes the skill directory and will not resolve "
                        f"once installed: {raw_target}",
                    )


def validate_repository(root: Path = ROOT) -> list[ValidationError]:
    root = root.resolve()
    errors: list[ValidationError] = []
    readme = root / "README.md"
    if not readme.is_file():
        add_error(errors, root, readme, "required file is missing")

    validate_plugin_manifest(root, errors)
    validate_marketplace_manifest(root, errors)
    skill_paths = discover_skill_paths(root)
    if not skill_paths:
        add_error(errors, root, root / "skills", "no skills discovered")
    validate_skill_files(root, skill_paths, errors)
    validate_skill_layout(root, errors)
    validate_no_legacy_artifacts(root, errors)
    validate_local_markdown_links(root, errors)
    validate_skill_asset_locality(root, errors)
    return errors


def validate(root: Path = ROOT) -> list[ValidationError]:
    return validate_repository(root)


def main() -> int:
    errors = validate_repository(ROOT)
    if errors:
        print("Validation failed")
        for error in errors:
            print(f"- {error.path}: {error.message}")
        return 1

    skill_names = [path.parent.name for path in discover_skill_paths(ROOT)]
    print("Validation passed")
    print(f"- plugin: {PLUGIN_NAME}")
    print(f"- skills ({len(skill_names)}): {', '.join(skill_names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
