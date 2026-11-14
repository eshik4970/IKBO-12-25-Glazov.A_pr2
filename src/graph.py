"""Read Cargo registry metadata and recursively traverse dependency graphs."""

import json
import re
from collections import deque
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from semver import compare, matches

LATIN_NAME = re.compile(r'[A-Z]+\Z')
VISITING = 1
VISITED = 2


def load_test_repo(filename):
    """Validate a local test graph using uppercase Latin crate labels."""
    try:
        data = json.loads(Path(filename).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f'Cannot read test repository: {error}') from error
    if not isinstance(data, dict):
        raise ValueError('Test repository must contain a JSON object')
    validate_test_data(data)


    def dependencies(node):
        """Resolve edges from a test node."""
        name, _ = node
        if name not in data:
            raise ValueError(f'Unknown package: {name}')
        return [(dependency, 'test') for dependency in data[name]]

    return dependencies


def validate_test_data(data):
    """Check names, adjacency lists and references in a test graph."""
    for name, dependencies in data.items():
        if not isinstance(name, str) or not LATIN_NAME.fullmatch(name):
            raise ValueError(f'Invalid package name: {name}')
        validate_test_dependencies(name, dependencies)
    missing = set().union(*(set(deps) for deps in data.values())) - data.keys()
    if missing:
        raise ValueError(f'Unknown dependencies: {", ".join(sorted(missing))}')


def validate_test_dependencies(name, dependencies):
    """Require every dependency to use uppercase Latin letters."""
    if not isinstance(dependencies, list):
        raise ValueError(f'Dependencies of {name} must be a list')
    if any(not isinstance(dep, str) or
           not LATIN_NAME.fullmatch(dep) for dep in dependencies):
        raise ValueError(f'Invalid dependency in {name}')


def fetch_json(url):
    """Download metadata directly via HTTP, without invoking Cargo."""
    request = Request(url, headers={'User-Agent': 'cargo-graph-study/2.0'})
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, OSError, ValueError) as error:
        raise ValueError(f'Cannot fetch {url}: {error}') from error


def select_version(versions, requirement):
    """Select highest compatible non-yanked SemVer version."""
    candidates = [item['num'] for item in versions
                  if not item.get('yanked') and 'num' in item]
    compatible = [value for value in candidates if matches(value, requirement)]
    from functools import cmp_to_key
    return max(compatible, key=cmp_to_key(compare)) if compatible else None


def load_registry(base_url):
    """Resolve direct normal/build dependencies through crates.io API."""
    versions_cache = {}
    dependencies_cache = {}
    root = base_url.rstrip('/')
    def versions_for(name):
        """Cache the registry version listing for each crate."""
        if name not in versions_cache:
            path = quote(name, safe='')
            url = f'{root}/api/v1/crates/{path}/versions'
            versions_cache[name] = fetch_json(url).get('versions', [])
        return versions_cache[name]
    def dependencies(node):
        """Fetch dependencies for one exact version of a crate."""
        if node in dependencies_cache:
            return dependencies_cache[node]
        name, version = node
        crate = quote(name, safe='')
        release = quote(version, safe='')
        url = f'{root}/api/v1/crates/{crate}/{release}/dependencies'
        metadata = fetch_json(url)
        result = []
        for item in metadata.get('dependencies', []):
            if item.get('optional') or item.get('kind') == 'dev':
                continue
            dependency = item.get('crate_id') or item.get('name')
            if not dependency:
                raise ValueError(f'Invalid dependency in {name}@{version}')
            requirement = item.get('req', '*')
            chosen = select_version(versions_for(dependency), requirement)
            if chosen is None:
                raise ValueError(
                    f'No compatible release: {dependency} {requirement}'
                )
            result.append((dependency, chosen))
        dependencies_cache[node] = sorted(set(result))
        return dependencies_cache[node]

    return dependencies


def build_graph(root, dependencies, excluded=''):
    """Use recursive breadth-first traversal with a shared visited set."""
    graph = {}
    visited = set()
    queue = deque([root])

    def next_level():
        """Process one BFS layer, then recursively process the next."""
        if not queue:
            return
        level_count = len(queue)
        for _ in range(level_count):
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            children = [child for child in dependencies(node)
                        if not excluded or excluded not in child[0]]
            graph[node] = sorted(set(children))
            queue.extend(child for child in children if child not in visited)
        next_level()

    next_level()
    return graph


def loading_order(graph):
    """Return dependency-first topological order or reject a cycle."""
    result = []
    state = {}

    def visit(node):
        """Visit dependents after their dependencies."""
        if state.get(node) == VISITING:
            raise ValueError('Cycle prevents dependency loading order')
        if state.get(node) == VISITED:
            return
        state[node] = VISITING
        for child in graph.get(node, []):
            visit(child)
        state[node] = VISITED
        result.append(node)

    for node in graph:
        visit(node)
    return result
