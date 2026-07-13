from __future__ import annotations

import importlib.util
import inspect
import json
import shutil
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from typing import Mapping
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
# The five core event skills share one execution contract.
EXPECTED_SKILLS = {
    "hello-ralphthon-icml",
    "auto-research",
    "wandb-onboarding",
    "vessl-cloud-onboarding",
    "world-model-ideation",
}
# The three W&B companion skills use the W&B product-workflow contract.  Codex
# reached them through .agents/ symlinks; Claude Code requires them to sit
# directly under skills/.
EXPECTED_WANDB_SKILLS = {
    "wandb-track-experiment",
    "weave-add-tracing",
    "wandb-project-analyst",
}
ALL_EXPECTED_SKILLS = EXPECTED_SKILLS | EXPECTED_WANDB_SKILLS
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"
MARKETPLACE_MANIFEST = Path(".claude-plugin") / "marketplace.json"
PLUGIN_VERSION = "1.0.0"
VESSL_AUTORESEARCH_URL = (
    "https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/autoresearch"
)
VESSL_COOKBOOK_SHA = "97a0af14b0acae042162b1f70f17fbe2d570afa2"
KARPATHY_SHA = "228791fb499afffb54b46200aca536f79142f117"
GIT_SHA = "1" * 40
SECOND_GIT_SHA = "2" * 40


def sha256_marker(character: str) -> str:
    return "sha256:" + character * 64


def load_validator():
    path = ROOT / "scripts" / "validate_plugin.py"
    spec = importlib.util.spec_from_file_location("validate_plugin", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_recorder():
    path = ROOT / "skills" / "auto-research" / "scripts" / "record_experiment.py"
    spec = importlib.util.spec_from_file_location("record_experiment", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cookbook_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "val_bpb": 1.2345,
        "peak_vram_mb": 26_432.0,
        "training_seconds": 300.1,
        "total_seconds": 330.2,
        "num_params_M": 50.3,
    }
    summary.update(overrides)
    return summary


def recorder_correlation(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "cookbook_sha": VESSL_COOKBOOK_SHA,
        "vessl_job_slug": "autoresearch-baseline-abc123",
        "vessl_job_name": "autoresearch-campaign-42-1111111",
        "vessl_job_state": "succeeded",
        "approved_resource_spec": "resourcespec-live-a100-1",
        "job_resource_spec": "resourcespec-live-a100-1",
        "gpu_identity": "NVIDIA A100-SXM4-80GB",
        "gpu_count": 1,
        "branch": "autoresearch/campaign-42",
        "cache_fingerprint": sha256_marker("a"),
        "evaluation_fingerprint": sha256_marker("b"),
        "train_py_sha256": sha256_marker("c"),
        "log_sha256": sha256_marker("d"),
        "job_json_sha256": sha256_marker("e"),
    }
    values.update(overrides)
    return values


def recorder_record_inputs(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "run_tag": "campaign-42",
        "trial": "baseline",
        "git_sha": GIT_SHA,
        "remote_commit": GIT_SHA,
        "hypothesis": "frozen official baseline",
        "change": "none",
        "status": "keep",
        "failure": None,
        "next_hint": "try one candidate",
        "summary": cookbook_summary(),
        "wandb_run": "offline-run-id",
        **recorder_correlation(),
    }
    values.update(overrides)
    return values


class RepositoryContractTest(unittest.TestCase):
    def test_expected_skill_catalog_exists_without_commands(self) -> None:
        skills = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}

        self.assertEqual(skills, ALL_EXPECTED_SKILLS)
        self.assertFalse((ROOT / "commands").exists())
        self.assertFalse((ROOT / "docs" / "superpowers").exists())

    def test_every_skill_is_discoverable_by_claude_code(self) -> None:
        """Claude Code discovers plugin skills at skills/<name>/SKILL.md.

        A SKILL.md nested deeper is not discovered as a top-level skill, so the
        W&B skills must not regress to the old skills/wandb/<name>/ layout.
        """
        skills_root = ROOT / "skills"
        found = sorted(skills_root.rglob("SKILL.md"))

        self.assertEqual(
            {path.parent.name for path in found}, ALL_EXPECTED_SKILLS
        )
        for path in found:
            with self.subTest(skill=path.parent.name):
                self.assertEqual(
                    path.parent.parent,
                    skills_root,
                    f"{path} must be exactly one level under skills/",
                )

    def test_codex_artifacts_are_gone(self) -> None:
        for relative in (".codex-plugin", ".agents", "commands"):
            with self.subTest(path=relative):
                self.assertFalse((ROOT / relative).exists())
        self.assertEqual(list((ROOT / "skills").rglob("openai.yaml")), [])
        self.assertEqual(list((ROOT / "skills").rglob("agents")), [])

    def test_plugin_manifest_matches_claude_code_schema(self) -> None:
        manifest = json.loads((ROOT / PLUGIN_MANIFEST).read_text())

        self.assertEqual(manifest["name"], "ralphthon-icml")
        self.assertEqual(manifest["version"], PLUGIN_VERSION)
        for field in (
            "description",
            "author",
            "homepage",
            "repository",
            "license",
            "keywords",
        ):
            with self.subTest(field=field):
                self.assertTrue(manifest.get(field))
        # Codex-only fields that Claude Code silently ignores.
        for field in ("interface", "commands", "skills"):
            with self.subTest(unsupported=field):
                self.assertNotIn(field, manifest)

    def test_marketplace_manifest_can_install_the_plugin(self) -> None:
        marketplace = json.loads((ROOT / MARKETPLACE_MANIFEST).read_text())

        self.assertEqual(marketplace["name"], "ralphthon-icml")
        self.assertTrue(marketplace["owner"]["name"])
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn("ralphthon-icml", entries)
        source = entries["ralphthon-icml"]["source"]
        self.assertTrue((ROOT / source).exists(), f"source must resolve: {source}")

    def test_validator_accepts_the_migrated_repository(self) -> None:
        validator = load_validator()

        self.assertEqual(validator.validate_repository(ROOT), [])

    def mutated_repository(self, directory: str) -> Path:
        root = Path(directory) / "plugin"
        shutil.copytree(
            ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__")
        )
        return root

    def validator_messages(self, root: Path) -> list[str]:
        validator = load_validator()
        return [error.message for error in validator.validate_repository(root)]

    def test_validator_rejects_skill_name_directory_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            skill = root / "skills" / "hello-ralphthon-icml" / "SKILL.md"
            skill.write_text(
                skill.read_text().replace(
                    "name: hello-ralphthon-icml",
                    "name: wrong-skill-name",
                    1,
                )
            )

            messages = self.validator_messages(root)

        self.assertTrue(any("directory name" in message for message in messages))

    def test_validator_rejects_codex_era_artifacts(self) -> None:
        """The runtime ignores these silently, so the validator must not."""
        cases = {
            "codex-manifest": Path(".codex-plugin") / "plugin.json",
            "agents-symlink-dir": Path(".agents") / "skills" / "auto-research",
            "legacy-commands": Path("commands") / "legacy.md",
            "openai-metadata": Path("skills")
            / "auto-research"
            / "agents"
            / "openai.yaml",
        }

        for case_name, relative in cases.items():
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as directory:
                root = self.mutated_repository(directory)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("legacy\n")

                messages = self.validator_messages(root)

                self.assertTrue(
                    any("remove it" in message for message in messages),
                    f"validator accepted a Codex-era artifact: {relative}",
                )

    def test_validator_rejects_a_skill_nested_below_skills(self) -> None:
        """The pre-migration W&B layout must not silently come back."""
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            nested = root / "skills" / "wandb" / "weave-add-tracing"
            nested.mkdir(parents=True)
            (nested / "SKILL.md").write_text(
                "---\nname: weave-add-tracing\ndescription: Nested too deep.\n---\n"
            )

            messages = self.validator_messages(root)

        self.assertTrue(
            any("one level under skills/" in message for message in messages)
        )

    def test_validator_rejects_unsupported_manifest_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            path = root / PLUGIN_MANIFEST
            manifest = json.loads(path.read_text())
            manifest["interface"] = {"displayName": "Ralphthon @ICML"}
            path.write_text(json.dumps(manifest))

            messages = self.validator_messages(root)

        self.assertTrue(any("interface" in message for message in messages))

    def test_validator_rejects_a_missing_or_broken_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            (root / MARKETPLACE_MANIFEST).unlink()

            messages = self.validator_messages(root)

        self.assertTrue(
            any("/plugin marketplace add" in message for message in messages)
        )

        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            path = root / MARKETPLACE_MANIFEST
            marketplace = json.loads(path.read_text())
            marketplace["plugins"][0]["source"] = "./does-not-exist"
            path.write_text(json.dumps(marketplace))

            messages = self.validator_messages(root)

        self.assertTrue(
            any("source does not resolve" in message for message in messages)
        )

    def test_validator_rejects_broken_and_escaping_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            (
                root
                / "skills"
                / "auto-research"
                / "assets"
                / "track-1-submission-template.md"
            ).unlink()

            messages = self.validator_messages(root)

        self.assertTrue(any("local Markdown link" in message for message in messages))

        # A link outside the skill directory resolves in the repository but
        # breaks once the plugin is installed.
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            skill = root / "skills" / "weave-add-tracing" / "SKILL.md"
            skill.write_text(
                skill.read_text()
                + "\nSee [the other skill](../auto-research/SKILL.md).\n"
            )

            messages = self.validator_messages(root)

        self.assertTrue(
            any("escapes the skill directory" in message for message in messages)
        )

    def test_validator_rejects_an_overlong_description(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.mutated_repository(directory)
            skill = root / "skills" / "hello-ralphthon-icml" / "SKILL.md"
            skill.write_text(
                skill.read_text().replace(
                    "description: Welcome",
                    "description: " + "x" * 1100 + " Welcome",
                    1,
                )
            )

            messages = self.validator_messages(root)

        self.assertTrue(any("truncated" in message for message in messages))

    def test_manifest_advertises_full_workflow(self) -> None:
        manifest = json.loads((ROOT / PLUGIN_MANIFEST).read_text())
        marketplace = json.loads((ROOT / MARKETPLACE_MANIFEST).read_text())
        entry = next(
            plugin
            for plugin in marketplace["plugins"]
            if plugin["name"] == "ralphthon-icml"
        )
        searchable = " ".join(
            manifest["keywords"]
            + [manifest["description"], manifest["displayName"], entry["description"]]
        ).lower()

        for phrase in ("auto-research", "wandb", "vessl", "world-model"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, searchable)

    def test_readme_documents_full_catalog_and_privacy_boundary(self) -> None:
        text = (ROOT / "README.md").read_text()

        for phrase in (
            *ALL_EXPECTED_SKILLS,
            "16:30",
            "W&B",
            "VESSL Cloud",
            "private participant",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("slash commands", text)
        hello_skill = (ROOT / "skills/hello-ralphthon-icml/SKILL.md").read_text()
        self.assertNotIn("world-model sponsor narrative", hello_skill)

    def test_readme_documents_claude_code_installation(self) -> None:
        text = (ROOT / "README.md").read_text()

        for phrase in (
            "/plugin marketplace add team-attention/ralphthon-icml",
            "/plugin install ralphthon-icml@ralphthon-icml",
            ".claude-plugin/plugin.json",
            "claude plugin validate",
            "skills (8)",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        # Codex install and invocation instructions must not survive.
        for stale in (
            ".codex-plugin",
            ".agents/skills",
            "agents/openai.yaml",
            "~/.codex/skills",
            "$wandb-track-experiment",
            "$auto-research",
            "skills/wandb/",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, text)

    def test_official_cookbook_integration_docs_and_metadata(self) -> None:
        manifest = json.loads((ROOT / PLUGIN_MANIFEST).read_text())
        self.assertEqual(manifest["version"], PLUGIN_VERSION)
        manifest_text = json.dumps(manifest, ensure_ascii=False)
        for phrase in ("VESSL Cloud Cookbook", "A100", "W&B", "autoresearch"):
            with self.subTest(manifest_phrase=phrase):
                self.assertIn(phrase, manifest_text)

        readme = (ROOT / "README.md").read_text()
        for phrase in (
            VESSL_AUTORESEARCH_URL,
            VESSL_COOKBOOK_SHA,
            "single A100",
            "W&B offline",
            "participant-owned fork",
            "unchanged benchmark",
        ):
            with self.subTest(readme_phrase=phrase):
                self.assertIn(phrase, readme)

        marketplace_text = (ROOT / MARKETPLACE_MANIFEST).read_text()
        for phrase in ("VESSL", "A100", "W&B"):
            with self.subTest(marketplace_phrase=phrase):
                self.assertIn(phrase, marketplace_text)

        public_bundle = "\n".join((manifest_text, readme, marketplace_text))
        for stale in ("A100-micro-v1", "786,468", "TIME_BUDGET=120"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, public_bundle)

    def test_each_skill_contains_integrated_execution_contract(self) -> None:
        for skill_name in EXPECTED_SKILLS:
            text = (ROOT / "skills" / skill_name / "SKILL.md").read_text()
            for heading in ("Preflight", "Workflow", "Verification", "Output", "Next Steps"):
                with self.subTest(skill=skill_name, heading=heading):
                    self.assertIn(f"## {heading}", text)

    def test_each_wandb_skill_contains_product_workflow_contract(self) -> None:
        for skill_name in EXPECTED_WANDB_SKILLS:
            text = (ROOT / "skills" / skill_name / "SKILL.md").read_text()
            for heading in ("Operating Rules", "Workflow", "Response Shape"):
                with self.subTest(skill=skill_name, heading=heading):
                    self.assertIn(f"## {heading}", text)

    def test_hands_on_notebooks_ship_inside_their_skill(self) -> None:
        """An installed plugin cannot resolve a path outside the skill directory."""
        for skill_name, notebook in (
            ("wandb-track-experiment", "handson_models.ipynb"),
            ("weave-add-tracing", "handson_weave.ipynb"),
        ):
            with self.subTest(skill=skill_name):
                skill_dir = ROOT / "skills" / skill_name
                self.assertTrue((skill_dir / "assets" / notebook).is_file())
                text = (skill_dir / "SKILL.md").read_text()
                self.assertIn(f"assets/{notebook}", text)
                self.assertNotIn("skills/wandb/hands-on", text)

    def test_skill_references_resolve(self) -> None:
        for skill_name in ALL_EXPECTED_SKILLS:
            skill_path = ROOT / "skills" / skill_name / "SKILL.md"
            with self.subTest(skill=skill_name):
                self.assertTrue(skill_path.is_file())
                if not skill_path.is_file():
                    continue
                text = skill_path.read_text()
                for relative in self._reference_links(text):
                    self.assertTrue(
                        (skill_path.parent / relative).is_file(),
                        f"missing reference from {skill_name}: {relative}",
                    )

    @staticmethod
    def _reference_links(text: str) -> list[str]:
        links: list[str] = []
        marker = "](references/"
        for line in text.splitlines():
            offset = 0
            while (start := line.find(marker, offset)) >= 0:
                path_start = start + 2
                path_end = line.find(")", path_start)
                if path_end < 0:
                    break
                links.append(line[path_start:path_end])
                offset = path_end + 1
        return links


class SkillBehaviorContractTest(unittest.TestCase):
    def read_skill(self, name: str) -> str:
        path = ROOT / "skills" / name / "SKILL.md"
        self.assertTrue(path.is_file(), f"missing skill: {name}")
        return path.read_text() if path.is_file() else ""

    def read_auto_research_bundle(self) -> str:
        root = ROOT / "skills" / "auto-research"
        return "\n".join(
            path.read_text()
            for path in sorted(root.rglob("*.md"))
            if path.is_file()
        )

    def test_auto_research_encodes_both_tracks_and_hard_cut(self) -> None:
        text = self.read_skill("auto-research")

        for phrase in (
            "Track 1",
            "2-4 page",
            "Track 2",
            "ICML-style review",
            "16:30",
            "Ralph Loop",
            "self-review",
            "research spec",
            "falsifiable hypothesis",
            "baseline",
            "evaluation metric",
            "evidence",
            "failure modes",
            "Do not fabricate",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        for relative in (
            "assets/track-1-submission-template.md",
            "assets/track-2-agent-template.md",
            "assets/track-2-review-template.md",
        ):
            with self.subTest(asset=relative):
                self.assertTrue((ROOT / "skills" / "auto-research" / relative).is_file())

        readme = (ROOT / "README.md").read_text()
        for name, document in (("skill", text), ("readme", readme)):
            with self.subTest(general_track_1=name):
                self.assertIn("General Track 1 path", document)
                self.assertIn("does not automatically require W&B, VESSL, or A100", document)

    def test_official_vessl_cookbook_is_the_execution_sot(self) -> None:
        text = self.read_auto_research_bundle()

        for phrase in (
            VESSL_AUTORESEARCH_URL,
            VESSL_COOKBOOK_SHA,
            KARPATHY_SHA,
            "execution SOT",
            "batch-job/prep.sh",
            "batch-job/submit.sh",
            "batch-job/submit-async.sh",
            "batch-job/wait-jobs.sh",
            "AUTORESEARCH_CACHE_VOLUME",
            "AUTORESEARCH_RESOURCE_SPEC",
            "AUTORESEARCH_IMAGE",
            "AUTORESEARCH_REPO_URL",
            "AUTORESEARCH_TIMEOUT_S",
            "vesslctl job create",
            "vesslctl job show",
            "vesslctl job logs",
            "object volume",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        for stale in (
            "A100-micro-v1",
            "DEPTH=2",
            "TIME_BUDGET=120",
            "786,468",
            "prepare.py --num-shards 1",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, text)

    def test_official_benchmark_is_not_reimplemented_or_changed(self) -> None:
        text = self.read_auto_research_bundle()

        for phrase in (
            "unchanged benchmark",
            "byte-for-byte",
            "prepare.py",
            "pyproject.toml",
            "uv.lock",
            "evaluation",
            "benchmark defaults",
            "only `train.py`",
            "one hypothesis",
            "one change",
            "A100 results",
            "H100 results",
            "not directly comparable",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        safety_sentence = (
            "**DO NOT USE** `git reset --hard`, `git add -A`, "
            "`LOOP FOREVER`, or `NEVER STOP`"
        )
        skill = self.read_skill("auto-research")
        runbook = (
            ROOT
            / "skills"
            / "auto-research"
            / "references"
            / "vessl-autoresearch-runbook.md"
        ).read_text()
        self.assertIn(safety_sentence, skill)
        self.assertIn(safety_sentence, runbook)

        # This plugin supplies orchestration and evidence templates, not a forked
        # benchmark.  The executable benchmark remains in the pinned cookbook.
        skill_root = ROOT / "skills" / "auto-research"
        for benchmark_file in (
            "prepare.py",
            "train.py",
            "pyproject.toml",
            "uv.lock",
            "benchmarks.md",
            "results.example.tsv",
            "analysis.ipynb",
        ):
            with self.subTest(not_vendored=benchmark_file):
                self.assertFalse(any(skill_root.rglob(benchmark_file)))

    def test_a100_gate_cost_fork_and_bounded_loop_fail_closed(self) -> None:
        text = self.read_auto_research_bundle()

        for phrase in (
            "resource-spec list --usable-only -o json",
            "single A100",
            "exact live resource spec",
            "Do not fall back",
            "hourly price",
            "credit",
            "storage",
            "estimated cost",
            "explicit confirmation",
            "participant-owned fork",
            "writable",
            "git remote get-url origin",
            "git ls-remote",
            "cloud-clonable",
            "Push that unchanged pinned branch",
            "full remote SHA",
            "baseline",
            "at most three candidate",
            "winner confirmation",
            "sequential",
            "APPROVED_A100_RESOURCE_SPEC",
            "prep.sh` has no `AUTORESEARCH_TIMEOUT_S",
            "read-only CPU verification Job",
            "autoresearch/<run-tag>-confirm",
            "Require a new Job name and slug",
            "local polling timeout",
            "does not terminate",
            "vesslctl job terminate",
            "confirmed terminal state",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("fall back to H100", text)
        self.assertNotIn("parallel fanout", text)

    def test_auto_research_binds_secret_and_wandb_postprocessing_gates(self) -> None:
        text = self.read_auto_research_bundle()

        for phrase in (
            "wandb-onboarding",
            "vessl-cloud-onboarding",
            "WANDB_MODE=offline",
            "vesslctl job logs",
            "local post-processing",
            "entity",
            "project",
            "visibility",
            "upload allowlist",
            "explicit confirmation",
            "wandb sync --entity",
            "experiments.jsonl",
            "val_bpb",
            "W&B Launch",
            "W&B Sweeps",
            "sanitized host",
            "SDK telemetry records",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        for forbidden in (
            "wandb login $WANDB_API_KEY",
            "WANDB_API_KEY=",
            "put the W&B API key in VESSL",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_auto_research_recorder_correlates_vessl_and_wandb_evidence(self) -> None:
        path = ROOT / "skills" / "auto-research" / "scripts" / "record_experiment.py"
        self.assertTrue(path.is_file())
        if not path.is_file():
            return

        module = load_recorder()
        summary = module.parse_training_summary(
            "\n".join(
                (
                    "val_bpb:          1.234500",
                    "training_seconds: 300.1",
                    "total_seconds:    330.2",
                    "peak_vram_mb:     26432.0",
                    "num_params_M:     50.3",
                )
            )
        )
        self.assertEqual(summary["val_bpb"], 1.2345)
        self.assertEqual(summary["num_params_M"], 50.3)

        correlation = recorder_correlation()
        required_parameters = set(correlation)
        actual_parameters = set(inspect.signature(module.build_record).parameters)
        self.assertTrue(
            required_parameters <= actual_parameters,
            f"build_record missing correlation parameters: "
            f"{sorted(required_parameters - actual_parameters)}",
        )
        if not required_parameters <= actual_parameters:
            return
        record = module.build_record(
            **recorder_record_inputs(summary=summary, **correlation)
        )
        for field, expected in correlation.items():
            with self.subTest(field=field):
                self.assertEqual(record[field], expected)
        self.assertEqual(record["val_bpb"], 1.2345)

        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "experiments.jsonl"
            module.append_record(ledger, record)
            self.assertEqual(json.loads(ledger.read_text()), record)

        actions = {
            option
            for action in module.build_parser()._actions
            for option in action.option_strings
        }
        for flag in (
            "--cookbook-sha",
            "--vessl-job-slug",
            "--vessl-job-name",
            "--vessl-job-state",
            "--approved-resource-spec",
            "--job-resource-spec",
            "--gpu-identity",
            "--gpu-count",
            "--branch",
            "--cache-fingerprint",
            "--evaluation-file",
            "--train-py",
            "--job-json",
            "--git-sha",
            "--remote-commit",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, actions)

    def test_auto_research_recorder_rejects_untrusted_or_unbounded_evidence(self) -> None:
        module = load_recorder()
        base = recorder_record_inputs()

        with self.assertRaisesRegex(ValueError, "execution SOT pin"):
            module.build_record(**{**base, "cookbook_sha": "0" * 40})
        with self.assertRaisesRegex(ValueError, "normalized NVIDIA A100"):
            module.build_record(**{**base, "gpu_identity": "NVIDIA H100 80GB"})
        for invalid_gpu in (
            "8x NVIDIA A100",
            "NVIDIA A100 H100",
            "A100 not an A100",
            "A100 x8",
        ):
            with self.subTest(invalid_gpu=invalid_gpu):
                with self.assertRaisesRegex(ValueError, "normalized NVIDIA A100"):
                    module.build_record(**{**base, "gpu_identity": invalid_gpu})
        with self.assertRaisesRegex(ValueError, "exactly 1"):
            module.build_record(**{**base, "gpu_count": 8})
        with self.assertRaisesRegex(ValueError, "must be terminal"):
            module.build_record(**{**base, "vessl_job_state": "running"})
        with self.assertRaisesRegex(ValueError, "must equal approved"):
            module.build_record(
                **{**base, "job_resource_spec": "resourcespec-other-a100"}
            )
        with self.assertRaisesRegex(ValueError, "must not identify H100"):
            module.build_record(
                **{
                    **base,
                    "approved_resource_spec": "resourcespec-h100-1",
                    "job_resource_spec": "resourcespec-h100-1",
                }
            )
        with self.assertRaisesRegex(ValueError, "full lowercase 40-hex"):
            module.build_record(**{**base, "remote_commit": "abc1234"})
        with self.assertRaisesRegex(ValueError, "sha256:<64 lowercase hex>"):
            module.build_record(**{**base, "cache_fingerprint": "placeholder"})
        with self.assertRaisesRegex(ValueError, "finite number"):
            module.build_record(
                **{**base, "summary": cookbook_summary(val_bpb=float("nan"))}
            )
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            module.build_record(**{**base, "summary": cookbook_summary(val_bpb=-1.0)})
        with self.assertRaisesRegex(ValueError, "lowercase"):
            module.build_record(**{**base, "run_tag": "Campaign-42"})

        baseline = module.build_record(**base)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "experiments.jsonl"
            module.append_record(ledger, baseline)
            before = ledger.read_bytes()
            skipped = module.build_record(
                **recorder_record_inputs(
                    trial="candidate-2",
                    git_sha=SECOND_GIT_SHA,
                    remote_commit=SECOND_GIT_SHA,
                    hypothesis="candidate two too early",
                    change="one train.py change",
                    status="discard",
                    vessl_job_slug="autoresearch-candidate-2-abc123",
                    vessl_job_name="autoresearch-campaign-42-2222222",
                    train_py_sha256=sha256_marker("f"),
                    log_sha256=sha256_marker("1"),
                    job_json_sha256=sha256_marker("2"),
                )
            )
            with self.assertRaisesRegex(ValueError, "expected candidate-1"):
                module.validate_ledger_sequence(ledger, record=skipped)
            self.assertEqual(ledger.read_bytes(), before)

    def test_auto_research_recorder_enforces_lower_winner_and_invariants(self) -> None:
        module = load_recorder()
        baseline = module.build_record(**recorder_record_inputs())
        candidate_inputs = recorder_record_inputs(
            trial="candidate-1",
            git_sha=SECOND_GIT_SHA,
            remote_commit=SECOND_GIT_SHA,
            hypothesis="one mechanism predicts lower BPB",
            change="one train.py change",
            status="keep",
            next_hint="confirm if it remains best",
            summary=cookbook_summary(val_bpb=1.1),
            vessl_job_slug="autoresearch-candidate-1-abc123",
            vessl_job_name="autoresearch-campaign-42-2222222",
            train_py_sha256=sha256_marker("f"),
            log_sha256=sha256_marker("1"),
            job_json_sha256=sha256_marker("2"),
        )

        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "experiments.jsonl"
            module.append_record(ledger, baseline)

            worse = module.build_record(
                **{**candidate_inputs, "summary": cookbook_summary(val_bpb=2.0)}
            )
            with self.assertRaisesRegex(ValueError, "strictly lower"):
                module.validate_ledger_sequence(ledger, record=worse)

            changed_environment = module.build_record(
                **{
                    **candidate_inputs,
                    "approved_resource_spec": "resourcespec-other-a100",
                    "job_resource_spec": "resourcespec-other-a100",
                }
            )
            with self.assertRaisesRegex(ValueError, "campaign invariant changed"):
                module.validate_ledger_sequence(ledger, record=changed_environment)

            duplicate_job = module.build_record(
                **{
                    **candidate_inputs,
                    "vessl_job_slug": baseline["vessl_job_slug"],
                }
            )
            with self.assertRaisesRegex(ValueError, "duplicate vessl_job_slug"):
                module.validate_ledger_sequence(ledger, record=duplicate_job)

            candidate = module.build_record(**candidate_inputs)
            module.append_record(ledger, candidate)

            confirmation_inputs = recorder_record_inputs(
                trial="winner-confirmation",
                git_sha=SECOND_GIT_SHA,
                remote_commit=SECOND_GIT_SHA,
                hypothesis=candidate["hypothesis"],
                change=candidate["change"],
                status="confirmation",
                next_hint="freeze the evidence",
                summary=cookbook_summary(val_bpb=1.15),
                vessl_job_slug="autoresearch-confirmation-abc123",
                vessl_job_name="autoresearch-campaign-42-confirm-2222222",
                branch="autoresearch/campaign-42-confirm",
                train_py_sha256=candidate["train_py_sha256"],
                log_sha256=sha256_marker("3"),
                job_json_sha256=sha256_marker("4"),
            )
            opposite_direction = module.build_record(
                **{**confirmation_inputs, "summary": cookbook_summary(val_bpb=1.3)}
            )
            with self.assertRaisesRegex(ValueError, "below baseline"):
                module.validate_ledger_sequence(ledger, record=opposite_direction)

            changed_code = module.build_record(
                **{**confirmation_inputs, "train_py_sha256": sha256_marker("9")}
            )
            with self.assertRaisesRegex(ValueError, "train_py_sha256"):
                module.validate_ledger_sequence(ledger, record=changed_code)

            confirmation = module.build_record(**confirmation_inputs)
            module.append_record(ledger, confirmation)
            self.assertEqual(len(ledger.read_text().splitlines()), 3)

    def test_auto_research_recorder_serializes_concurrent_candidates(self) -> None:
        module = load_recorder()
        baseline = module.build_record(**recorder_record_inputs())

        def candidate_record(marker: str, value: float) -> dict[str, object]:
            git_sha = marker * 40
            return module.build_record(
                **recorder_record_inputs(
                    trial="candidate-1",
                    git_sha=git_sha,
                    remote_commit=git_sha,
                    hypothesis=f"candidate {marker}",
                    change="one train.py change",
                    status="keep",
                    summary=cookbook_summary(val_bpb=value),
                    vessl_job_slug=f"autoresearch-candidate-{marker}",
                    vessl_job_name=f"autoresearch-campaign-42-{marker * 7}",
                    train_py_sha256=sha256_marker(marker),
                    log_sha256=sha256_marker(marker.upper()),
                    job_json_sha256=sha256_marker(str(int(marker) + 4)),
                )
            )

        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "experiments.jsonl"
            module.append_record(ledger, baseline)
            barrier = threading.Barrier(2)
            results: list[str] = []

            def append_candidate(record: Mapping[str, object]) -> None:
                barrier.wait()
                try:
                    module.append_record(ledger, record)
                except ValueError:
                    results.append("rejected")
                else:
                    results.append("appended")

            threads = [
                threading.Thread(
                    target=append_candidate,
                    args=(candidate_record("2", 1.1),),
                ),
                threading.Thread(
                    target=append_candidate,
                    args=(candidate_record("3", 1.05),),
                ),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

            self.assertEqual(sorted(results), ["appended", "rejected"])
            self.assertEqual(len(ledger.read_text().splitlines()), 2)

    def test_auto_research_recorder_is_private_offline_and_wandb_native(self) -> None:
        module = load_recorder()
        calls: dict[str, object] = {"defined_metrics": []}

        class FakeSettings:
            def __init__(self, **kwargs):
                calls["settings"] = kwargs

        class FakeRun:
            id = "offline-123"

            def __init__(self, directory: Path):
                self.dir = str(directory / "offline-run-123" / "files")
                Path(self.dir).mkdir(parents=True)

            def define_metric(self, name, **kwargs):
                calls["defined_metrics"].append((name, kwargs))

            def log(self, metrics):
                calls["metrics"] = metrics

            def finish(self, exit_code=0):
                calls["exit_code"] = exit_code

        def fake_init(**kwargs):
            calls["init"] = kwargs
            return FakeRun(Path(kwargs["dir"]))

        fake_wandb = types.SimpleNamespace(Settings=FakeSettings, init=fake_init)
        correlation = recorder_correlation()
        required_parameters = set(correlation)
        actual_parameters = set(inspect.signature(module.record_offline_run).parameters)
        self.assertTrue(
            required_parameters <= actual_parameters,
            f"record_offline_run missing correlation parameters: "
            f"{sorted(required_parameters - actual_parameters)}",
        )
        if not required_parameters <= actual_parameters:
            return
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                run_id, run_directory = module.record_offline_run(
                    wandb_directory=root / "wandb",
                    entity="approved-entity",
                    project="approved-project",
                    run_tag="campaign-42",
                    trial="candidate-1",
                    git_sha=GIT_SHA,
                    remote_commit=GIT_SHA,
                    status="keep",
                    summary=cookbook_summary(),
                    **correlation,
                )

        self.assertEqual(run_id, "offline-123")
        self.assertEqual(Path(run_directory).name, "offline-run-123")
        settings = calls["settings"]
        for field, expected in (
            ("console", "off"),
            ("disable_git", True),
            ("disable_code", True),
            ("disable_job_creation", True),
            ("x_disable_meta", True),
            ("x_disable_stats", True),
            ("x_disable_machine_info", True),
            ("x_save_requirements", False),
            ("save_code", False),
            ("host", "ralphthon-offline"),
        ):
            with self.subTest(setting=field):
                self.assertEqual(settings[field], expected)

        init = calls["init"]
        self.assertEqual(init["mode"], "offline")
        self.assertEqual(init["group"], "campaign-42")
        self.assertEqual(init["job_type"], "autoresearch-trial")
        self.assertFalse(init["save_code"])
        self.assertEqual(calls["defined_metrics"], [("val_bpb", {"summary": "min"})])
        self.assertEqual(calls["exit_code"], 0)
        self.assertEqual(calls["metrics"]["val_bpb"], 1.2345)
        for field, expected in correlation.items():
            with self.subTest(config_field=field):
                self.assertEqual(init["config"][field], expected)

        source = (
            ROOT / "skills/auto-research/scripts/record_experiment.py"
        ).read_text()
        self.assertNotIn("--api-key", source)
        self.assertNotIn('mode="online"', source)
        for forbidden in ("dataset", "checkpoint", "artifact"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, init["config"])

    def test_auto_research_recorder_marks_crashes_with_nonzero_exit(self) -> None:
        module = load_recorder()
        exit_codes: list[int] = []

        class FakeSettings:
            def __init__(self, **_kwargs):
                pass

        class FakeRun:
            id = "offline-crash"

            def __init__(self, directory: Path):
                self.dir = str(directory / "offline-run-crash" / "files")
                Path(self.dir).mkdir(parents=True)

            def define_metric(self, _name, **_kwargs):
                pass

            def log(self, _metrics):
                pass

            def finish(self, exit_code=0):
                exit_codes.append(exit_code)

        def fake_init(**kwargs):
            return FakeRun(Path(kwargs["dir"]))

        fake_wandb = types.SimpleNamespace(Settings=FakeSettings, init=fake_init)
        correlation = recorder_correlation(
            vessl_job_state="failed",
            vessl_job_slug="autoresearch-crash-abc123",
            vessl_job_name="autoresearch-campaign-42-crash",
            log_sha256=sha256_marker("1"),
            job_json_sha256=sha256_marker("2"),
        )
        required_parameters = set(correlation)
        actual_parameters = set(inspect.signature(module.record_offline_run).parameters)
        self.assertTrue(
            required_parameters <= actual_parameters,
            f"record_offline_run missing correlation parameters: "
            f"{sorted(required_parameters - actual_parameters)}",
        )
        if not required_parameters <= actual_parameters:
            return
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                module.record_offline_run(
                    wandb_directory=Path(directory),
                    entity="approved-entity",
                    project="approved-project",
                    run_tag="campaign-42",
                    trial="candidate-1",
                    git_sha=GIT_SHA,
                    remote_commit=GIT_SHA,
                    status="crash",
                    summary={},
                    **correlation,
                )

        self.assertEqual(exit_codes, [1])

    def test_auto_research_recorder_removes_failed_offline_run(self) -> None:
        module = load_recorder()

        class FakeSettings:
            def __init__(self, **_kwargs):
                pass

        class FailingRun:
            id = "offline-failed"

            def __init__(self, directory: Path):
                (directory.parent / "offline-run-sibling").mkdir(parents=True)
                self.dir = str(directory / "offline-run-failed" / "files")
                Path(self.dir).mkdir(parents=True)

            def define_metric(self, _name, **_kwargs):
                pass

            def log(self, _metrics):
                raise RuntimeError("synthetic W&B log failure")

            def finish(self, exit_code=0):
                pass

        def fake_init(**kwargs):
            return FailingRun(Path(kwargs["dir"]))

        fake_wandb = types.SimpleNamespace(Settings=FakeSettings, init=fake_init)
        correlation = recorder_correlation(
            vessl_job_slug="autoresearch-failed-abc123",
            vessl_job_name="autoresearch-campaign-42-failed",
            log_sha256=sha256_marker("1"),
            job_json_sha256=sha256_marker("2"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                with self.assertRaisesRegex(RuntimeError, "synthetic W&B log failure"):
                    module.record_offline_run(
                        wandb_directory=root,
                        entity="approved-entity",
                        project="approved-project",
                        run_tag="campaign-42",
                        trial="candidate-1",
                        git_sha=GIT_SHA,
                        remote_commit=GIT_SHA,
                        status="keep",
                        summary=cookbook_summary(),
                        **correlation,
                    )
            remaining = [path.name for path in root.rglob("offline-run-*")]
            self.assertEqual(remaining, ["offline-run-sibling"])

    def test_auto_research_recorder_main_prevalidates_and_cleans_append_failure(
        self,
    ) -> None:
        module = load_recorder()
        init_calls: list[dict[str, object]] = []

        class FakeSettings:
            def __init__(self, **_kwargs):
                pass

        class FakeRun:
            id = "offline-main"

            def __init__(self, directory: Path):
                self.dir = str(directory / "offline-run-main" / "files")
                Path(self.dir).mkdir(parents=True)

            def define_metric(self, _name, **_kwargs):
                pass

            def log(self, _metrics):
                pass

            def finish(self, exit_code=0):
                pass

        def fake_init(**kwargs):
            init_calls.append(kwargs)
            return FakeRun(Path(kwargs["dir"]))

        fake_wandb = types.SimpleNamespace(Settings=FakeSettings, init=fake_init)

        def cli_args(
            inputs: Mapping[str, object],
            summary: Path,
            train_py: Path,
            evaluation_file: Path,
            ledger: Path,
            wandb_dir: Path,
        ) -> list[str]:
            job_json = ledger.parent / f"{inputs['vessl_job_slug']}.json"
            job_json.write_text(
                json.dumps(
                    {
                        "slug": inputs["vessl_job_slug"],
                        "name": inputs["vessl_job_name"],
                        "workloadState": inputs["vessl_job_state"],
                        "resourceSpec": {"slug": inputs["job_resource_spec"]},
                    }
                )
            )
            flags = {
                "--summary": summary,
                "--job-json": job_json,
                "--train-py": train_py,
                "--evaluation-file": evaluation_file,
                "--ledger": ledger,
                "--wandb-dir": wandb_dir,
                "--entity": "approved-entity",
                "--project": "approved-project",
                "--run-tag": inputs["run_tag"],
                "--trial": inputs["trial"],
                "--git-sha": inputs["git_sha"],
                "--remote-commit": inputs["remote_commit"],
                "--hypothesis": inputs["hypothesis"],
                "--change": inputs["change"],
                "--status": inputs["status"],
                "--cookbook-sha": inputs["cookbook_sha"],
                "--vessl-job-slug": inputs["vessl_job_slug"],
                "--vessl-job-name": inputs["vessl_job_name"],
                "--vessl-job-state": inputs["vessl_job_state"],
                "--approved-resource-spec": inputs["approved_resource_spec"],
                "--job-resource-spec": inputs["job_resource_spec"],
                "--gpu-identity": inputs["gpu_identity"],
                "--gpu-count": inputs["gpu_count"],
                "--branch": inputs["branch"],
                "--cache-fingerprint": inputs["cache_fingerprint"],
            }
            return [str(item) for pair in flags.items() for item in pair]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root / "run.log"
            summary.write_text(
                "\n".join(
                    (
                        "val_bpb: 1.2",
                        "training_seconds: 300",
                        "total_seconds: 320",
                        "peak_vram_mb: 20000",
                        "num_params_M: 50.3",
                    )
                )
            )
            train_py = root / "train.py"
            train_py.write_text("# frozen candidate train.py\n")
            evaluation_file = root / "prepare.py"
            evaluation_file.write_text("# frozen evaluation harness\n")

            existing_ledger = root / "existing.jsonl"
            baseline_inputs = recorder_record_inputs(
                train_py_sha256=module.sha256_file(train_py),
                evaluation_fingerprint=module.sha256_file(evaluation_file),
            )
            module.append_record(
                existing_ledger,
                module.build_record(**baseline_inputs),
            )
            skipped = recorder_record_inputs(
                trial="candidate-2",
                git_sha=SECOND_GIT_SHA,
                remote_commit=SECOND_GIT_SHA,
                hypothesis="skipped candidate",
                change="one train.py change",
                status="discard",
                vessl_job_slug="autoresearch-candidate-2-main",
                vessl_job_name="autoresearch-campaign-42-2222222",
                train_py_sha256=sha256_marker("f"),
                log_sha256=sha256_marker("1"),
                job_json_sha256=sha256_marker("2"),
            )
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                with self.assertRaisesRegex(ValueError, "expected candidate-1"):
                    module.main(
                        cli_args(
                            skipped,
                            summary,
                            train_py,
                            evaluation_file,
                            existing_ledger,
                            root / "prevalidation-wandb",
                        )
                    )
            self.assertEqual(init_calls, [])

            new_ledger = root / "new.jsonl"
            new_wandb = root / "append-failure-wandb"
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                with mock.patch.object(
                    module,
                    "_append_record_locked",
                    side_effect=OSError("synthetic append failure"),
                ):
                    with self.assertRaisesRegex(RuntimeError, "ledger append failed"):
                        module.main(
                            cli_args(
                            recorder_record_inputs(),
                            summary,
                            train_py,
                            evaluation_file,
                            new_ledger,
                                new_wandb,
                            )
                        )
            self.assertEqual(len(init_calls), 1)
            self.assertEqual(list(new_wandb.rglob("offline-run-*")), [])

            mismatch_ledger = root / "mismatch.jsonl"
            mismatch_args = cli_args(
                recorder_record_inputs(),
                summary,
                train_py,
                evaluation_file,
                mismatch_ledger,
                root / "mismatch-wandb",
            )
            job_json_index = mismatch_args.index("--job-json") + 1
            Path(mismatch_args[job_json_index]).write_text(
                json.dumps(
                    {
                        "slug": "autoresearch-baseline-abc123",
                        "name": "autoresearch-campaign-42-1111111",
                        "workloadState": "succeeded",
                        "resourceSpec": {"slug": "resourcespec-wrong-a100"},
                    }
                )
            )
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                with self.assertRaisesRegex(ValueError, "does not contain"):
                    module.main(mismatch_args)
            self.assertEqual(len(init_calls), 1)

            success_ledger = root / "success.jsonl"
            success_args = cli_args(
                recorder_record_inputs(),
                summary,
                train_py,
                evaluation_file,
                success_ledger,
                root / "success-wandb",
            )
            success_job_json = Path(
                success_args[success_args.index("--job-json") + 1]
            )
            with mock.patch.dict(sys.modules, {"wandb": fake_wandb}):
                with mock.patch("builtins.print"):
                    self.assertEqual(module.main(success_args), 0)
            saved = json.loads(success_ledger.read_text())
            self.assertEqual(saved["log_sha256"], module.sha256_file(summary))
            self.assertEqual(saved["train_py_sha256"], module.sha256_file(train_py))
            self.assertEqual(
                saved["evaluation_fingerprint"], module.sha256_file(evaluation_file)
            )
            self.assertEqual(
                saved["job_json_sha256"], module.sha256_file(success_job_json)
            )

    def test_official_vessl_resource_catalog_is_surfaced(self) -> None:
        path = (
            ROOT
            / "skills"
            / "vessl-cloud-onboarding"
            / "references"
            / "official-repositories.md"
        )
        self.assertTrue(path.is_file())
        text = path.read_text() if path.is_file() else ""
        for url in (
            "https://github.com/vessl-ai/vessl-cloud-cookbook",
            VESSL_AUTORESEARCH_URL,
            "https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/gemma4-finetuning",
            "https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/gpu-cost-benchmark",
            "https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/aqr-finance",
            "https://github.com/vessl-ai/vessl-cloud-cookbook/tree/main/_template",
            "https://github.com/vessl-ai",
            "https://github.com/vessl-ai/physical-ai-hackathon-demo",
            "https://github.com/vessl-ai/nccl-multinode-example",
            "https://github.com/vessl-ai/vessl-cloud-integration",
            "https://github.com/vessl-ai/mcpctl",
            "https://docs.cloud.vessl.ai/mcp",
            "https://docs.cloud.vessl.ai/cli/ai-tools",
        ):
            with self.subTest(url=url):
                self.assertIn(url, text)
        for phrase in (
            "vesslctl skill show --output json",
            "vesslctl skill install --target cross-client",
            "legacy",
            "not an execution SOT",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_official_wandb_resource_catalog_is_surfaced(self) -> None:
        path = (
            ROOT
            / "skills"
            / "wandb-onboarding"
            / "references"
            / "official-ecosystem.md"
        )
        self.assertTrue(path.is_file())
        text = path.read_text() if path.is_file() else ""
        for url in (
            "https://github.com/wandb/docs",
            "https://github.com/wandb/skills",
            "https://github.com/wandb/examples",
            "https://github.com/wandb/edu",
            "https://github.com/wandb/artifacts-examples",
            "https://github.com/wandb/launch-jobs",
            "https://github.com/wandb/sweeps",
            "https://github.com/wandb/wandb",
            "https://docs.wandb.ai/aria/autoresearch",
            "https://docs.wandb.ai/platform/mcp-server",
            "https://github.com/wandb/wandb-mcp-server",
        ):
            with self.subTest(url=url):
                self.assertIn(url, text)
        for phrase in (
            "primary SOT",
            "experimental",
            "reference only",
            "one falsifiable",
            "single-variable probe",
            "W&B Launch",
            "VESSL",
            "Preview",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_wandb_onboarding_keeps_secrets_interactive_and_runs_offline_first(self) -> None:
        text = self.read_skill("wandb-onboarding")

        for phrase in (
            "wandb login --verify",
            "WANDB_MODE=offline",
            "interactive prompt",
            "Never ask",
            "explicit confirmation",
            "entity",
            "project",
            "visibility",
            "upload allowlist",
            "wandb sync --entity",
            "local post-processing",
            "vesslctl job logs",
            "group",
            "job_type",
            "val_bpb",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("wandb login $WANDB_API_KEY", text)
        self.assertNotIn("WANDB_API_KEY=", text)
        asset = ROOT / "skills/wandb-onboarding/assets/wandb-quickstart.py"
        self.assertTrue(asset.is_file())
        asset_text = asset.read_text() if asset.is_file() else ""
        self.assertIn("WANDB_ENTITY", asset_text)
        self.assertIn("WANDB_PROJECT", asset_text)
        self.assertIn("--relogin --cloud --verify", text)

    def test_vessl_cloud_onboarding_covers_cookbook_job_lifecycle_and_cost(self) -> None:
        text = self.read_skill("vessl-cloud-onboarding")

        for phrase in (
            "https://cloud.vessl.ai",
            "vesslctl auth status",
            "vesslctl config show",
            "vesslctl billing show",
            "vesslctl org list",
            "vesslctl team list",
            "vesslctl cluster list",
            "resource-spec list --usable-only",
            "hourly price",
            "credit",
            "image",
            "duration",
            "cleanup",
            "explicit confirmation",
            "Pause",
            "Terminate",
            "legacy",
            "vesslctl auth login --web",
            VESSL_AUTORESEARCH_URL,
            "object volume",
            "vesslctl job create",
            "vesslctl job show",
            "vesslctl job logs",
            "vesslctl job terminate",
            "polling timeout",
            "keeps running",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertNotIn("app.vessl.ai/login", text)
        cost_card = ROOT / "skills/vessl-cloud-onboarding/assets/workspace-cost-card.md"
        self.assertTrue(cost_card.is_file())
        cost_text = cost_card.read_text() if cost_card.is_file() else ""
        for phrase in ("Storage capacity", "Storage hourly price", "Estimated storage cost"):
            with self.subTest(cost_phrase=phrase):
                self.assertIn(phrase, cost_text)

    def test_world_model_ideation_produces_testable_research_not_only_brand_copy(self) -> None:
        text = self.read_skill("world-model-ideation")

        for phrase in (
            "falsifiable hypothesis",
            "baseline",
            "evaluation metric",
            "failure mode",
            "minimum experiment",
            "Track 1",
            "Track 2",
            "Do not claim",
            "Dalpha",
            "unconfirmed",
            "0–2 for",
            "Action alignment",
            "General Track 1",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        self.assertTrue(
            (ROOT / "skills/world-model-ideation/assets/research-spec-template.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
