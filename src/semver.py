"""Small Cargo-style SemVer requirement matcher (no third-party packages)."""

import re

VERSION = re.compile(
    r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
    r'(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$'
)
PARTIAL = re.compile(
    r'^(\d+)(?:\.(\d+|\*))?(?:\.(\d+|\*))?'
    r'(?:-([0-9A-Za-z.-]+))?$'
)


MAJOR_ONLY = 1
MAJOR_MINOR = 2


def parse_version(value):
    """Return the numeric triple and pre-release tuple."""
    match = VERSION.fullmatch(value)
    if not match:
        raise ValueError(f'Invalid semantic version: {value}')
    return tuple(map(int, match.group(1, 2, 3))), (
        tuple(match.group(4).split('.')) if match.group(4) else ()
    )


def compare_pre(left, right):
    """Compare SemVer pre-release identifiers, with release greatest."""
    if not left or not right:
        return (not left) - (not right)
    for a, b in zip(left, right):
        a_num, b_num = a.isdigit(), b.isdigit()
        if a_num != b_num:
            return -1 if a_num else 1
        x, y = (int(a), int(b)) if a_num else (a, b)
        if x != y:
            return (x > y) - (x < y)
    return (len(left) > len(right)) - (len(left) < len(right))


def compare(left, right):
    """Compare versions without using lexical string sorting."""
    a, a_pre = parse_version(left)
    b, b_pre = parse_version(right)
    return ((a > b) - (a < b)) or compare_pre(a_pre, b_pre)


def partial(value):
    """Parse a comparator with missing or wildcard components."""
    match = PARTIAL.fullmatch(value)
    if not match:
        raise ValueError(f'Unsupported Cargo version requirement: {value}')
    values = match.group(1, 2, 3)
    size = sum(item is not None and item != '*' for item in values)
    numbers = tuple(int(item) if item and item != '*' else 0
                    for item in values)
    return numbers, size, match.group(4)


def upper_bound(nums, size, mode):
    """Compute an exclusive upper limit for caret, tilde or wildcard."""
    major, minor, patch = nums
    if mode == '~':
        if size == MAJOR_ONLY:
            return major + 1, 0, 0
        return major, minor + 1, 0
    if mode == '*':
        return ((major + 1, 0, 0) if size == MAJOR_ONLY else
                (major, minor + 1, 0))
    if major:
        return major + 1, 0, 0
    if size == MAJOR_ONLY:
        return 1, 0, 0
    if minor:
        return 0, minor + 1, 0
    if size == MAJOR_MINOR:
        return 0, 1, 0
    return 0, 0, patch + 1


def matches_comparator(version, expression):
    """Evaluate one comma-separated Cargo comparator."""
    match = re.fullmatch(r'(>=|<=|>|<|=|\^|~)?\s*(.+)', expression)
    if not match:
        raise ValueError(f'Invalid requirement: {expression}')
    op, value = match.group(1) or '^', match.group(2)
    if value in ('*', 'x', 'X'):
        return True
    nums, size, pre = partial(value)
    actual, actual_pre = parse_version(version)
    lower = '.'.join(map(str, nums)) + (f'-{pre}' if pre else '')
    relation = compare(version, lower)
    if op in ('>', '>=', '<', '<=', '='):
        return {'>': relation > 0, '>=': relation >= 0,
                '<': relation < 0, '<=': relation <= 0,
                '=': actual[:size] == nums[:size]}[op]
    if op == '^' and size == 0:
        return True
    limit = upper_bound(nums, size, op)
    return relation >= 0 and actual < limit


def matches(version, requirement):
    """Check Cargo AND constraints, with explicit prerelease opt-in."""
    try:
        _, prerelease = parse_version(version)
        tokens = [token.strip() for token in requirement.split(',')]
        if not tokens or not all(tokens):
            return False
        if prerelease and not prerelease_allowed(version, tokens):
            return False
        return all(matches_comparator(version, token) for token in tokens)
    except ValueError:
        return False


def prerelease_allowed(version, tokens):
    """Require an explicit prerelease comparator for the same triple."""
    numbers, _ = parse_version(version)
    for token in tokens:
        value = re.sub(r'^(>=|<=|>|<|=|\^|~)\s*', '', token)
        try:
            target, _, pre = partial(value)
        except ValueError:
            continue
        if pre and target == numbers:
            return True
    return False
