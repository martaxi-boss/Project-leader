"""Single-revision runtime bootstrap contract for Project Leader.

The ChatGPT Skill still performs connector reads itself. This module defines the
executable invariants used by tests and by any host adapter: resolve canonical
main exactly once, pin the resulting commit SHA, and read every runtime contract
file from that same immutable revision.
"""

import re

RUNTIME_CONTRACT_VERSION = 1
MIN_LOADER_VERSION = 1
PINNED_RUNTIME_STATE = "RUNTIME_CANONICAL_PINNED"

DEFAULT_RUNTIME_PATHS = (
    "plugins/project-leader/plugin.json",
    "plugins/project-leader/skills/project-leader/SKILL.md",
    "PROJECT_LEADER.md",
    "RUNBOOK.md",
    "RECOVERY_PROTOCOL.md",
    "roles/SUPERVISOR.md",
    "roles/BUILDER.md",
    "roles/RECOVERY_GUARDIAN.md",
    "projects/standing-authority.json",
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_loader_version(loader_version):
    if not isinstance(loader_version, int) or isinstance(loader_version, bool):
        raise ValueError("loader_version must be an integer")
    if loader_version < MIN_LOADER_VERSION:
        raise ValueError(
            f"loader version {loader_version} is incompatible; "
            f"minimum is {MIN_LOADER_VERSION}"
        )
    return True


def pin_runtime_bundle(resolve_main_sha, read_at_revision, *, loader_version=1, paths=None):
    """Resolve main once and fetch a coherent runtime bundle at that SHA."""
    validate_loader_version(loader_version)
    revision = resolve_main_sha()
    if not isinstance(revision, str) or _SHA_RE.fullmatch(revision) is None:
        raise ValueError("canonical main resolver must return an exact 40-hex commit SHA")

    selected_paths = tuple(paths or DEFAULT_RUNTIME_PATHS)
    if not selected_paths:
        raise ValueError("runtime bundle requires at least one contract path")
    if len(selected_paths) != len(set(selected_paths)):
        raise ValueError("runtime bundle paths must be unique")

    files = {}
    for path in selected_paths:
        if not isinstance(path, str) or not path or path.startswith("/"):
            raise ValueError(f"invalid runtime contract path: {path!r}")
        files[path] = read_at_revision(path, revision)

    return {
        "state": PINNED_RUNTIME_STATE,
        "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
        "loader_version": loader_version,
        "revision": revision,
        "files": files,
    }
