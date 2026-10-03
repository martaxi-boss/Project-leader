from fnmatch import fnmatchcase

_GLOB_MAGIC = "*?["


def _normalize_scope_pattern(pattern):
    normalized = pattern.replace("\\", "/").strip()
    if not normalized or normalized.startswith("/"):
        raise ValueError(f"invalid mutation_scope pattern: {pattern!r}")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"invalid mutation_scope pattern: {pattern!r}")
    return normalized


def _has_glob(pattern):
    return any(char in pattern for char in _GLOB_MAGIC)


def _literal_prefix(pattern):
    positions = [pattern.find(char) for char in _GLOB_MAGIC if char in pattern]
    return pattern[: min(positions)] if positions else pattern


def scope_pattern_is_within(requested_pattern, allowed_pattern):
    requested = _normalize_scope_pattern(requested_pattern)
    allowed = _normalize_scope_pattern(allowed_pattern)

    if allowed == "**":
        return True

    if requested == allowed:
        return True

    if not _has_glob(requested):
        return fnmatchcase(requested, allowed)

    if not _has_glob(allowed):
        return False

    requested_prefix = _literal_prefix(requested)
    if allowed.endswith("/**") and not _has_glob(allowed[:-3]):
        return requested_prefix.startswith(allowed[:-2])
    if allowed.endswith("*") and not _has_glob(allowed[:-1]):
        return requested_prefix.startswith(allowed[:-1])
    return False
