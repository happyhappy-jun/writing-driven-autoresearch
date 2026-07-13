#!/usr/bin/env python3
"""Record one official VESSL autoresearch Job as local, offline evidence.

The benchmark stays unchanged in VESSL. This local post-processor parses a
downloaded Job log, validates the VESSL/Git/cache evidence, appends one locked
JSONL record, and creates a W&B run in offline mode. Upload is always a later,
explicitly approved action.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping, Sequence


COOKBOOK_SHA = "97a0af14b0acae042162b1f70f17fbe2d570afa2"
COOKBOOK_SOURCE = "vessl-ai/vessl-cloud-cookbook/autoresearch"
SANITIZED_WANDB_HOST = "ralphthon-offline"
ALLOWED_STATUSES = frozenset({"keep", "discard", "crash", "confirmation"})
TERMINAL_JOB_STATES = frozenset({"succeeded", "failed", "terminated", "cancelled"})
FAILED_JOB_STATES = TERMINAL_JOB_STATES - {"succeeded"}
RUN_TAG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BRANCH_PATTERN = re.compile(r"^autoresearch/[a-z0-9]+(?:-[a-z0-9]+)*$")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
VESSL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
GPU_IDENTITY_PATTERN = re.compile(
    r"^(?:NVIDIA[ -])?A100"
    r"(?:[- ](?:SXM4?|PCI[Ee]))?"
    r"(?:[- ](?:40|80) ?GB)?$",
    re.IGNORECASE,
)
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TRIAL_STATUSES = {
    "baseline": frozenset({"keep", "crash"}),
    "candidate-1": frozenset({"keep", "discard", "crash"}),
    "candidate-2": frozenset({"keep", "discard", "crash"}),
    "candidate-3": frozenset({"keep", "discard", "crash"}),
    "winner-confirmation": frozenset({"confirmation", "crash"}),
}
CANDIDATE_TRIALS = ("candidate-1", "candidate-2", "candidate-3")
SUMMARY_FIELDS = {
    "val_bpb": float,
    "training_seconds": float,
    "total_seconds": float,
    "peak_vram_mb": float,
    "mfu_percent": float,
    "total_tokens_M": float,
    "num_steps": int,
    "num_params_M": float,
    "parameters": int,
    "depth": int,
}
BASE_RECORD_FIELDS = (
    "run_tag",
    "trial",
    "git_sha",
    "remote_commit",
    "hypothesis",
    "change",
    "val_bpb",
    "peak_vram_mb",
    "num_params_M",
    "elapsed_seconds",
    "status",
    "failure",
    "next_hint",
    "wandb_run",
)
CORRELATION_FIELDS = (
    "cookbook_sha",
    "vessl_job_slug",
    "vessl_job_name",
    "vessl_job_state",
    "approved_resource_spec",
    "job_resource_spec",
    "gpu_identity",
    "gpu_count",
    "branch",
    "cache_fingerprint",
    "evaluation_fingerprint",
    "train_py_sha256",
    "log_sha256",
    "job_json_sha256",
)
CAMPAIGN_INVARIANTS = (
    "cookbook_sha",
    "approved_resource_spec",
    "job_resource_spec",
    "gpu_identity",
    "gpu_count",
    "cache_fingerprint",
    "evaluation_fingerprint",
)
RECORD_FIELDS = BASE_RECORD_FIELDS + CORRELATION_FIELDS


def parse_training_summary(text: str) -> dict[str, int | float]:
    """Parse known final-summary scalars from a downloaded VESSL Job log."""

    summary: dict[str, int | float] = {}
    known_keys = "|".join(re.escape(key) for key in SUMMARY_FIELDS)
    line_pattern = re.compile(
        rf"(?:^|\s)(?P<key>{known_keys})\s*:\s*(?P<value>\S+)\s*$"
    )
    for raw_line in text.splitlines():
        line = ANSI_ESCAPE_PATTERN.sub("", raw_line)
        match = line_pattern.search(line)
        if match is None:
            continue
        key = match.group("key")
        raw_value = match.group("value")
        converter = SUMMARY_FIELDS[key]
        try:
            value = converter(raw_value)
        except ValueError as error:
            raise ValueError(f"invalid {key} value: {raw_value!r}") from error
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"invalid {key} value: {raw_value!r}")
        summary[key] = value
    return summary


def sha256_file(path: Path) -> str:
    """Return a canonical SHA-256 marker for one local evidence file."""

    if not path.is_file():
        raise ValueError(f"evidence file does not exist: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError(f"cannot hash evidence file {path}: {error}") from error
    return f"sha256:{digest.hexdigest()}"


def _resource_spec_values(value: Any, *, in_resource_spec: bool = False) -> set[str]:
    values: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = re.sub(r"[^a-z]", "", str(key).lower())
            child_context = in_resource_spec or (
                "resource" in normalized_key and "spec" in normalized_key
            )
            values.update(
                _resource_spec_values(child, in_resource_spec=child_context)
            )
    elif isinstance(value, list):
        for child in value:
            values.update(
                _resource_spec_values(child, in_resource_spec=in_resource_spec)
            )
    elif in_resource_spec and isinstance(value, str):
        values.add(value)
    return values


def validate_job_json(
    path: Path,
    *,
    expected_slug: str,
    expected_name: str,
    expected_state: str,
    expected_resource_spec: str,
) -> None:
    """Bind supplied Job fields to the saved `vesslctl job show -o json`."""

    if not path.is_file():
        raise ValueError(f"Job JSON does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid VESSL Job JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError("VESSL Job JSON must contain one object")

    actual_slug = value.get("slug")
    actual_name = value.get("name")
    actual_state = value.get("workloadState")
    if actual_slug != expected_slug:
        raise ValueError("saved Job JSON slug does not match --vessl-job-slug")
    if actual_name != expected_name:
        raise ValueError("saved Job JSON name does not match --vessl-job-name")
    if not isinstance(actual_state, str) or actual_state.lower() != expected_state.lower():
        raise ValueError("saved Job JSON state does not match --vessl-job-state")

    resource_specs = _resource_spec_values(value)
    if expected_resource_spec not in resource_specs:
        raise ValueError(
            "saved Job JSON does not contain the supplied --job-resource-spec"
        )


def _require_text(field: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be empty")
    return value.strip()


def _require_single_line(field: str, value: Any) -> str:
    normalized = _require_text(field, value)
    if "\n" in normalized or "\r" in normalized:
        raise ValueError(f"{field} must be a single line")
    return normalized


def _require_full_sha(field: str, value: Any) -> str:
    normalized = _require_single_line(field, value)
    if FULL_SHA_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field} must be a full lowercase 40-hex Git SHA")
    return normalized


def _require_sha256(field: str, value: Any) -> str:
    normalized = _require_single_line(field, value)
    if SHA256_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field} must use sha256:<64 lowercase hex>")
    return normalized


def _finite_number(field: str, value: Any, *, positive: bool = False) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be a finite number")
    if positive and float(value) <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return value


def validate_run_tag(run_tag: Any) -> str:
    """Return a normalized campaign tag only when it is shell/name safe."""

    value = _require_single_line("run_tag", run_tag)
    if RUN_TAG_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "run_tag must use lowercase letters and digits separated by single hyphens"
        )
    return value


def validate_trial_status(trial: Any, status: Any) -> tuple[str, str]:
    """Bind each bounded campaign trial to its allowed outcome statuses."""

    trial_value = _require_single_line("trial", trial)
    if not isinstance(status, str) or status not in ALLOWED_STATUSES:
        raise ValueError("record contains an invalid status")
    allowed = TRIAL_STATUSES.get(trial_value)
    if allowed is None:
        raise ValueError(f"invalid trial: {trial_value}")
    if status not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{trial_value} status must be one of: {choices}")
    return trial_value, status


def _validate_job_state_for_status(state: str, status: str) -> None:
    if status == "crash":
        if state not in FAILED_JOB_STATES:
            raise ValueError("crash requires failed, terminated, or cancelled Job state")
    elif state != "succeeded":
        raise ValueError(f"{status} requires succeeded Job state")


def validate_correlation(
    *,
    cookbook_sha: Any,
    vessl_job_slug: Any,
    vessl_job_name: Any,
    vessl_job_state: Any,
    approved_resource_spec: Any,
    job_resource_spec: Any,
    gpu_identity: Any,
    gpu_count: Any,
    branch: Any,
    cache_fingerprint: Any,
    evaluation_fingerprint: Any,
    train_py_sha256: Any,
    log_sha256: Any,
    job_json_sha256: Any,
) -> dict[str, Any]:
    """Validate join keys between the approved resource, VESSL, Git, and W&B."""

    cookbook = _require_full_sha("cookbook_sha", cookbook_sha)
    if cookbook != COOKBOOK_SHA:
        raise ValueError(
            f"cookbook_sha must equal the reviewed execution SOT pin {COOKBOOK_SHA}"
        )

    job_slug = _require_single_line("vessl_job_slug", vessl_job_slug)
    job_name = _require_single_line("vessl_job_name", vessl_job_name)
    for field, value in (("vessl_job_slug", job_slug), ("vessl_job_name", job_name)):
        if VESSL_NAME_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{field} must be a lowercase VESSL name or slug")
    if not job_name.startswith("autoresearch-"):
        raise ValueError("vessl_job_name must use the official autoresearch prefix")

    job_state = _require_single_line("vessl_job_state", vessl_job_state).lower()
    if job_state not in TERMINAL_JOB_STATES:
        choices = ", ".join(sorted(TERMINAL_JOB_STATES))
        raise ValueError(f"vessl_job_state must be terminal: {choices}")

    approved_spec = _require_single_line(
        "approved_resource_spec", approved_resource_spec
    )
    actual_spec = _require_single_line("job_resource_spec", job_resource_spec)
    if approved_spec != actual_spec:
        raise ValueError("job_resource_spec must equal approved_resource_spec")
    if "H100" in approved_spec.upper():
        raise ValueError("A100 campaign resource spec must not identify H100")

    gpu_model = _require_single_line("gpu_identity", gpu_identity)
    if GPU_IDENTITY_PATTERN.fullmatch(gpu_model) is None:
        raise ValueError("gpu_identity must be a normalized NVIDIA A100 model")
    if type(gpu_count) is not int or gpu_count != 1:
        raise ValueError("gpu_count must equal exactly 1")

    branch_value = _require_single_line("branch", branch)
    if BRANCH_PATTERN.fullmatch(branch_value) is None:
        raise ValueError("branch must match autoresearch/<lowercase-tag>")

    return {
        "cookbook_sha": cookbook,
        "vessl_job_slug": job_slug,
        "vessl_job_name": job_name,
        "vessl_job_state": job_state,
        "approved_resource_spec": approved_spec,
        "job_resource_spec": actual_spec,
        "gpu_identity": gpu_model,
        "gpu_count": gpu_count,
        "branch": branch_value,
        "cache_fingerprint": _require_sha256(
            "cache_fingerprint", cache_fingerprint
        ),
        "evaluation_fingerprint": _require_sha256(
            "evaluation_fingerprint", evaluation_fingerprint
        ),
        "train_py_sha256": _require_sha256("train_py_sha256", train_py_sha256),
        "log_sha256": _require_sha256("log_sha256", log_sha256),
        "job_json_sha256": _require_sha256(
            "job_json_sha256", job_json_sha256
        ),
    }


def validate_record(record: Mapping[str, Any]) -> None:
    """Reject evidence records that do not implement the approved contract."""

    if set(record) != set(RECORD_FIELDS):
        raise ValueError(f"record fields must be exactly: {', '.join(RECORD_FIELDS)}")
    validate_run_tag(record["run_tag"])
    trial, status = validate_trial_status(record["trial"], record["status"])
    git_sha = _require_full_sha("git_sha", record["git_sha"])
    remote_commit = _require_full_sha("remote_commit", record["remote_commit"])
    if remote_commit != git_sha:
        raise ValueError("remote_commit must equal the local full git_sha")
    for field in ("hypothesis", "change", "wandb_run"):
        _require_text(field, record[field])

    correlation = validate_correlation(
        **{field: record[field] for field in CORRELATION_FIELDS}
    )
    _validate_job_state_for_status(correlation["vessl_job_state"], status)
    expected_branch = f"autoresearch/{record['run_tag']}"
    if trial == "winner-confirmation":
        expected_branch += "-confirm"
    if correlation["branch"] != expected_branch:
        raise ValueError(f"{trial} branch must equal {expected_branch}")
    if record["next_hint"] is not None:
        _require_text("next_hint", record["next_hint"])

    if status == "crash":
        _require_text("failure", record["failure"])
        for field in ("val_bpb", "peak_vram_mb", "num_params_M", "elapsed_seconds"):
            if record[field] is not None:
                _finite_number(field, record[field], positive=True)
    else:
        if record["failure"] not in (None, ""):
            raise ValueError(f"{status} must not contain a failure message")
        for field in ("val_bpb", "peak_vram_mb", "num_params_M", "elapsed_seconds"):
            _finite_number(field, record[field], positive=True)


def build_record(
    *,
    run_tag: str,
    trial: str,
    git_sha: str,
    remote_commit: str,
    hypothesis: str,
    change: str,
    status: str,
    failure: str | None,
    next_hint: str | None,
    summary: Mapping[str, int | float],
    wandb_run: str,
    cookbook_sha: str,
    vessl_job_slug: str,
    vessl_job_name: str,
    vessl_job_state: str,
    approved_resource_spec: str,
    job_resource_spec: str,
    gpu_identity: str,
    gpu_count: int,
    branch: str,
    cache_fingerprint: str,
    evaluation_fingerprint: str,
    train_py_sha256: str,
    log_sha256: str,
    job_json_sha256: str,
) -> dict[str, Any]:
    """Build one append-only record correlated to its exact remote Job."""

    normalized_run_tag = validate_run_tag(run_tag)
    normalized_trial, normalized_status = validate_trial_status(trial, status)
    local_sha = _require_full_sha("git_sha", git_sha)
    remote_sha = _require_full_sha("remote_commit", remote_commit)
    correlation = validate_correlation(
        cookbook_sha=cookbook_sha,
        vessl_job_slug=vessl_job_slug,
        vessl_job_name=vessl_job_name,
        vessl_job_state=vessl_job_state,
        approved_resource_spec=approved_resource_spec,
        job_resource_spec=job_resource_spec,
        gpu_identity=gpu_identity,
        gpu_count=gpu_count,
        branch=branch,
        cache_fingerprint=cache_fingerprint,
        evaluation_fingerprint=evaluation_fingerprint,
        train_py_sha256=train_py_sha256,
        log_sha256=log_sha256,
        job_json_sha256=job_json_sha256,
    )

    val_bpb = summary.get("val_bpb")
    peak_vram_mb = summary.get("peak_vram_mb")
    num_params_m = summary.get("num_params_M")
    elapsed_seconds = summary.get("total_seconds", summary.get("training_seconds"))
    if normalized_status != "crash":
        for field, value in (
            ("val_bpb", val_bpb),
            ("peak_vram_mb", peak_vram_mb),
            ("num_params_M", num_params_m),
            ("elapsed_seconds", elapsed_seconds),
        ):
            _finite_number(field, value, positive=True)
        training_seconds = summary.get("training_seconds")
        total_seconds = summary.get("total_seconds")
        if training_seconds is not None:
            _finite_number("training_seconds", training_seconds, positive=True)
        if total_seconds is not None:
            _finite_number("total_seconds", total_seconds, positive=True)
        if training_seconds is not None and total_seconds is not None:
            if float(total_seconds) < float(training_seconds):
                raise ValueError(
                    "total_seconds must be greater than or equal to training_seconds"
                )

    record: dict[str, Any] = {
        "run_tag": normalized_run_tag,
        "trial": normalized_trial,
        "git_sha": local_sha,
        "remote_commit": remote_sha,
        "hypothesis": _require_text("hypothesis", hypothesis),
        "change": _require_text("change", change),
        "val_bpb": val_bpb,
        "peak_vram_mb": peak_vram_mb,
        "num_params_M": num_params_m,
        "elapsed_seconds": elapsed_seconds,
        "status": normalized_status,
        "failure": failure,
        "next_hint": next_hint,
        "wandb_run": _require_text("wandb_run", wandb_run),
        **correlation,
    }
    validate_record(record)
    return record


def _read_locked_ledger(ledger: BinaryIO) -> list[dict[str, Any]]:
    ledger.seek(0)
    raw = ledger.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("ledger must be UTF-8 JSONL") from error
    if text and not text.endswith("\n"):
        raise ValueError("ledger ends with a partial JSON line")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"empty ledger line {line_number}")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid ledger JSON on line {line_number}") from error
        if not isinstance(record, dict):
            raise ValueError(f"ledger line {line_number} must be a JSON object")
        validate_record(record)
        records.append(record)
    return records


def _validate_campaign(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        return

    baseline = records[0]
    if baseline["trial"] != "baseline":
        raise ValueError("baseline must be the first ledger trial")
    run_tag = validate_run_tag(baseline["run_tag"])
    base_branch = f"autoresearch/{run_tag}"
    if baseline["branch"] != base_branch:
        raise ValueError(f"baseline branch must equal {base_branch}")

    seen_trials: set[str] = set()
    seen_job_slugs: set[str] = set()
    seen_job_names: set[str] = set()
    seen_log_hashes: set[str] = set()
    seen_job_json_hashes: set[str] = set()
    candidate_count = 0
    confirmation_seen = False
    best_candidate: Mapping[str, Any] | None = None
    baseline_value = baseline["val_bpb"]
    best_value = baseline_value

    for index, record in enumerate(records):
        validate_record(record)
        if record["run_tag"] != run_tag:
            raise ValueError(f"ledger run_tag mismatch at record {index + 1}")
        for field in CAMPAIGN_INVARIANTS:
            if record[field] != baseline[field]:
                raise ValueError(f"campaign invariant changed: {field}")
        for field, seen in (
            ("trial", seen_trials),
            ("vessl_job_slug", seen_job_slugs),
            ("vessl_job_name", seen_job_names),
            ("log_sha256", seen_log_hashes),
            ("job_json_sha256", seen_job_json_hashes),
        ):
            value = str(record[field])
            if value in seen:
                raise ValueError(f"duplicate {field} in ledger: {value}")
            seen.add(value)

        trial = str(record["trial"])
        if index == 0:
            if record["status"] == "crash" and len(records) > 1:
                raise ValueError("baseline crashed; no later trial is allowed")
            continue

        if trial in CANDIDATE_TRIALS:
            if confirmation_seen:
                raise ValueError("candidate cannot follow winner-confirmation")
            expected = CANDIDATE_TRIALS[candidate_count]
            if trial != expected:
                raise ValueError(f"expected {expected} before {trial}")
            candidate_count += 1
            if record["branch"] != base_branch:
                raise ValueError("candidate branch must equal the baseline branch")
            if record["status"] == "keep":
                if best_value is None or float(record["val_bpb"]) >= float(best_value):
                    raise ValueError("kept candidate val_bpb must be strictly lower")
                best_value = record["val_bpb"]
                best_candidate = record
            continue

        if trial == "winner-confirmation":
            if confirmation_seen or index != len(records) - 1:
                raise ValueError("winner-confirmation must be the final unique trial")
            confirmation_seen = True
            if best_candidate is None:
                raise ValueError("winner-confirmation requires a kept candidate")
            if record["branch"] != f"{base_branch}-confirm":
                raise ValueError("winner-confirmation requires the unique -confirm branch")
            for field in ("git_sha", "remote_commit", "train_py_sha256", "hypothesis", "change"):
                if record[field] != best_candidate[field]:
                    raise ValueError(
                        f"winner-confirmation must match best kept candidate: {field}"
                    )
            if record["status"] == "confirmation":
                if baseline_value is None or float(record["val_bpb"]) >= float(
                    baseline_value
                ):
                    raise ValueError(
                        "winner-confirmation must improve val_bpb below baseline"
                    )
            continue

        raise ValueError(f"invalid existing trial: {trial}")


@contextmanager
def locked_ledger(path: Path) -> Iterator[BinaryIO]:
    """Hold an exclusive advisory lock for validation and append."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_file():
        raise ValueError(f"ledger is not a regular file: {path}")
    try:
        ledger = path.open("a+b", buffering=0)
    except OSError as error:
        raise ValueError(f"ledger is not writable: {path}: {error}") from error
    with ledger:
        try:
            fcntl.flock(ledger.fileno(), fcntl.LOCK_EX)
        except OSError as error:
            raise ValueError(f"ledger cannot be locked: {path}: {error}") from error
        try:
            yield ledger
        finally:
            fcntl.flock(ledger.fileno(), fcntl.LOCK_UN)


def _validate_candidate_locked(ledger: BinaryIO, record: Mapping[str, Any]) -> None:
    validate_record(record)
    records = _read_locked_ledger(ledger)
    _validate_campaign([*records, record])


def _append_record_locked(ledger: BinaryIO, record: Mapping[str, Any]) -> None:
    """Append one line, fsync it, and roll back a failed partial write."""

    validate_record(record)
    payload = (
        json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    ledger.seek(0, os.SEEK_END)
    start = ledger.tell()
    try:
        written = ledger.write(payload)
        if written != len(payload):
            raise OSError(f"short ledger write: {written} of {len(payload)} bytes")
        os.fsync(ledger.fileno())
    except Exception:
        ledger.seek(start)
        ledger.truncate()
        os.fsync(ledger.fileno())
        raise


def append_record(path: Path, record: Mapping[str, Any]) -> None:
    """Validate and append one record under an exclusive ledger lock."""

    with locked_ledger(path) as ledger:
        _validate_candidate_locked(ledger, record)
        _append_record_locked(ledger, record)


def validate_ledger_writable(path: Path) -> None:
    """Prove that the ledger can be locked for append."""

    with locked_ledger(path):
        pass


def validate_ledger_sequence(path: Path, *, record: Mapping[str, Any]) -> None:
    """Validate a prospective record against the locked campaign ledger."""

    with locked_ledger(path) as ledger:
        _validate_candidate_locked(ledger, record)


def remove_new_offline_run(run_directory: str, wandb_directory: Path) -> None:
    """Remove one known W&B offline run without touching sibling runs."""

    base = wandb_directory.resolve()
    run = Path(run_directory).resolve()
    if base not in run.parents or not run.name.startswith("offline-run-"):
        raise RuntimeError(f"refusing unsafe offline run cleanup: {run}")
    invocation_root = next(
        (
            parent
            for parent in run.parents
            if parent.parent == base and parent.name.startswith(".recorder-")
        ),
        None,
    )
    target = invocation_root or run
    if target.exists():
        shutil.rmtree(target)


def record_offline_run(
    *,
    wandb_directory: Path,
    entity: str,
    project: str,
    run_tag: str,
    trial: str,
    git_sha: str,
    remote_commit: str,
    status: str,
    summary: Mapping[str, int | float],
    cookbook_sha: str,
    vessl_job_slug: str,
    vessl_job_name: str,
    vessl_job_state: str,
    approved_resource_spec: str,
    job_resource_spec: str,
    gpu_identity: str,
    gpu_count: int,
    branch: str,
    cache_fingerprint: str,
    evaluation_fingerprint: str,
    train_py_sha256: str,
    log_sha256: str,
    job_json_sha256: str,
) -> tuple[str, str]:
    """Create one allowlisted W&B run locally, never an online run."""

    entity = _require_single_line("entity", entity)
    project = _require_single_line("project", project)
    normalized_run_tag = validate_run_tag(run_tag)
    normalized_trial, normalized_status = validate_trial_status(trial, status)
    local_sha = _require_full_sha("git_sha", git_sha)
    remote_sha = _require_full_sha("remote_commit", remote_commit)
    if local_sha != remote_sha:
        raise ValueError("remote_commit must equal the local full git_sha")
    correlation = validate_correlation(
        cookbook_sha=cookbook_sha,
        vessl_job_slug=vessl_job_slug,
        vessl_job_name=vessl_job_name,
        vessl_job_state=vessl_job_state,
        approved_resource_spec=approved_resource_spec,
        job_resource_spec=job_resource_spec,
        gpu_identity=gpu_identity,
        gpu_count=gpu_count,
        branch=branch,
        cache_fingerprint=cache_fingerprint,
        evaluation_fingerprint=evaluation_fingerprint,
        train_py_sha256=train_py_sha256,
        log_sha256=log_sha256,
        job_json_sha256=job_json_sha256,
    )
    _validate_job_state_for_status(correlation["vessl_job_state"], normalized_status)

    try:
        import wandb
    except ImportError as error:
        raise RuntimeError(
            "The W&B SDK is needed only for local post-processing; install it "
            "in the recorder environment."
        ) from error

    config: dict[str, int | float | str] = {
        "run_tag": normalized_run_tag,
        "trial": normalized_trial,
        "git_sha": local_sha,
        "remote_commit": remote_sha,
        "execution_source": COOKBOOK_SOURCE,
        "status": normalized_status,
        **correlation,
    }
    num_params_m = summary.get("num_params_M")
    if num_params_m is not None:
        config["num_params_M"] = _finite_number(
            "num_params_M", num_params_m, positive=True
        )
    metrics = {
        key: value
        for key, value in {
            "val_bpb": summary.get("val_bpb"),
            "peak_vram_mb": summary.get("peak_vram_mb"),
            "elapsed_seconds": summary.get(
                "total_seconds", summary.get("training_seconds")
            ),
        }.items()
        if value is not None
    }
    for field, value in metrics.items():
        _finite_number(field, value, positive=True)

    wandb_directory.mkdir(parents=True, exist_ok=True)
    invocation_directory = Path(
        tempfile.mkdtemp(
            prefix=f".recorder-{normalized_run_tag}-{normalized_trial}-",
            dir=wandb_directory,
        )
    ).resolve()
    run = None
    run_directory: str | None = None
    try:
        settings = wandb.Settings(
            console="off",
            disable_code=True,
            disable_git=True,
            disable_job_creation=True,
            host=SANITIZED_WANDB_HOST,
            x_disable_machine_info=True,
            x_disable_meta=True,
            x_disable_stats=True,
            x_save_requirements=False,
            save_code=False,
        )
        run = wandb.init(
            mode="offline",
            dir=str(invocation_directory),
            entity=entity,
            project=project,
            name=f"{normalized_run_tag}-{normalized_trial}",
            group=normalized_run_tag,
            job_type="autoresearch-trial",
            config=config,
            save_code=False,
            settings=settings,
        )
        if run is None:
            raise RuntimeError("wandb.init did not return an offline run")

        files_directory = Path(run.dir)
        run_directory = str(
            files_directory.parent
            if files_directory.name == "files"
            else files_directory
        )
        run.define_metric("val_bpb", summary="min")
        if metrics:
            run.log(metrics)
        run_id = _require_single_line("wandb run id", str(run.id))
        run.finish(exit_code=1 if normalized_status == "crash" else 0)
        return run_id, run_directory
    except Exception as error:
        if run is not None:
            try:
                run.finish(exit_code=1)
            except Exception:
                pass
        try:
            if invocation_directory.exists():
                shutil.rmtree(invocation_directory)
        except Exception as cleanup_error:
            raise RuntimeError(
                f"W&B offline run failed ({error}); cleanup failed: {cleanup_error}"
            ) from error
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Append an official VESSL autoresearch result and create a local "
            "W&B offline run."
        )
    )
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--job-json", type=Path, required=True)
    parser.add_argument("--train-py", type=Path, required=True)
    parser.add_argument("--evaluation-file", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, default=Path("experiments.jsonl"))
    parser.add_argument("--wandb-dir", type=Path, default=Path(".wandb-offline"))
    parser.add_argument("--entity", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--trial", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--remote-commit", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--status", choices=sorted(ALLOWED_STATUSES), required=True)
    parser.add_argument("--failure")
    parser.add_argument("--next-hint")
    parser.add_argument("--cookbook-sha", required=True)
    parser.add_argument("--vessl-job-slug", required=True)
    parser.add_argument("--vessl-job-name", required=True)
    parser.add_argument("--vessl-job-state", required=True)
    parser.add_argument("--approved-resource-spec", required=True)
    parser.add_argument("--job-resource-spec", required=True)
    parser.add_argument("--gpu-identity", required=True)
    parser.add_argument("--gpu-count", type=int, required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--cache-fingerprint", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = parse_training_summary(args.summary.read_text(encoding="utf-8"))
    validate_job_json(
        args.job_json,
        expected_slug=args.vessl_job_slug,
        expected_name=args.vessl_job_name,
        expected_state=args.vessl_job_state,
        expected_resource_spec=args.job_resource_spec,
    )
    correlation = {
        "cookbook_sha": args.cookbook_sha,
        "vessl_job_slug": args.vessl_job_slug,
        "vessl_job_name": args.vessl_job_name,
        "vessl_job_state": args.vessl_job_state,
        "approved_resource_spec": args.approved_resource_spec,
        "job_resource_spec": args.job_resource_spec,
        "gpu_identity": args.gpu_identity,
        "gpu_count": args.gpu_count,
        "branch": args.branch,
        "cache_fingerprint": args.cache_fingerprint,
        "evaluation_fingerprint": sha256_file(args.evaluation_file),
        "train_py_sha256": sha256_file(args.train_py),
        "log_sha256": sha256_file(args.summary),
        "job_json_sha256": sha256_file(args.job_json),
    }
    record_inputs = {
        "run_tag": args.run_tag,
        "trial": args.trial,
        "git_sha": args.git_sha,
        "remote_commit": args.remote_commit,
        "hypothesis": args.hypothesis,
        "change": args.change,
        "status": args.status,
        "failure": args.failure,
        "next_hint": args.next_hint,
        "summary": summary,
        **correlation,
    }
    pending = build_record(
        **record_inputs,
        wandb_run="pending-offline-run",
    )
    _require_single_line("entity", args.entity)
    _require_single_line("project", args.project)

    run_id: str
    run_directory: str
    with locked_ledger(args.ledger) as ledger:
        _validate_candidate_locked(ledger, pending)
        run_id, run_directory = record_offline_run(
            wandb_directory=args.wandb_dir,
            entity=args.entity,
            project=args.project,
            run_tag=args.run_tag,
            trial=args.trial,
            git_sha=args.git_sha,
            remote_commit=args.remote_commit,
            status=args.status,
            summary=summary,
            **correlation,
        )
        try:
            record = build_record(**record_inputs, wandb_run=run_id)
            _validate_candidate_locked(ledger, record)
            _append_record_locked(ledger, record)
        except Exception as error:
            try:
                remove_new_offline_run(run_directory, args.wandb_dir)
            except Exception as cleanup_error:
                raise RuntimeError(
                    f"ledger append failed ({error}); offline run cleanup also "
                    f"failed: {cleanup_error}"
                ) from error
            raise RuntimeError(
                f"ledger append failed ({error}); removed new offline run: "
                f"{run_directory}"
            ) from error

    print(
        json.dumps(
            {
                "ledger": str(args.ledger),
                "vessl_job_slug": args.vessl_job_slug,
                "wandb_run_id": run_id,
                "wandb_run_directory": run_directory,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
