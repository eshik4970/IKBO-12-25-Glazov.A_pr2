"""Visualize Cargo dependency graphs from a registry or JSON fixture."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from graph import build_graph, load_registry, load_test_repo, loading_order
from render import make_d2, make_svg, make_tree
from semver import parse_version

STAGE_CONFIG = 1
STAGE_DIRECT = 2
STAGE_GRAPH = 3
STAGE_ORDER = 4
STAGE_RENDER = 5


def arguments(argv=None):
    """Parse CLI options and reject invalid parameter combinations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, help='Crate name')
    parser.add_argument(
        '--repository', required=True, help='HTTPS API or JSON'
    )
    parser.add_argument('--test', action='store_true', help='Read local JSON')
    parser.add_argument(
        '--version', required=True, help='Requested crate version'
    )
    parser.add_argument('--output', default='graph.svg', help='Output SVG path')
    parser.add_argument('--ascii', action='store_true', help='Show ASCII tree')
    parser.add_argument('--filter', default='', help='Excluded name substring')
    parser.add_argument('--stage', type=int, choices=range(1, 6), default=5)
    args = parser.parse_args(argv)
    validate_arguments(parser, args)
    return args


def validate_arguments(parser, args):
    """Validate common options and the selected repository mode."""
    if not args.package.strip() or not args.version.strip():
        parser.error('Package and version must not be empty')
    if not args.output.lower().endswith('.svg'):
        parser.error('Output filename must have .svg extension')
    if args.test:
        validate_test_options(parser, args)
    else:
        validate_registry_options(parser, args)


def validate_test_options(parser, args):
    """Check the local fixture options."""
    if not re.fullmatch(r'[A-Z]+', args.package):
        parser.error('Test package names must use uppercase Latin letters')
    if not Path(args.repository).is_file():
        parser.error('Test repository file does not exist')


def validate_registry_options(parser, args):
    """Check the HTTPS registry and requested Cargo version."""
    url = urlparse(args.repository)
    if url.scheme != 'https' or not url.netloc:
        parser.error('Repository must be an HTTPS URL')
    try:
        parse_version(args.version)
    except ValueError as error:
        parser.error(str(error))


def print_configuration(args):
    """Display all user options for the first stage."""
    for name, value in vars(args).items():
        print(f'{name}: {value}')


def save_diagrams(graph, output):
    """Write D2 and self-contained SVG files to the output directory."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    d2_path = path.with_suffix('.d2')
    d2_path.write_text(make_d2(graph), encoding='utf-8')
    path.write_text(make_svg(graph), encoding='utf-8')
    print(f'D2: {d2_path}\nSVG: {path}')


def run_stage(args, resolver):
    """Execute the selected stage with a configured dependency resolver."""
    root = (args.package, args.version)
    if args.stage == STAGE_DIRECT:
        for name, version in resolver(root):
            print(f'{name} {version}')
        return
    graph = build_graph(root, resolver, args.filter)
    show_graph(args, root, graph)


def show_graph(args, root, graph):
    """Print intermediate results or write final graph files."""
    if args.stage == STAGE_GRAPH:
        data = {f'{name}@{version}': [f'{a}@{b}' for a, b in children]
                for (name, version), children in graph.items()}
        print(json.dumps(data, indent=2))
    elif args.stage == STAGE_ORDER:
        for name, version in loading_order(graph):
            print(f'{name}@{version}')
    elif args.stage == STAGE_RENDER:
        if args.ascii:
            print(make_tree(root, graph))
        save_diagrams(graph, args.output)


def main(argv=None):
    """Execute one of the five required practical-work stages."""
    args = arguments(argv)
    if args.stage == STAGE_CONFIG:
        print_configuration(args)
        return
    try:
        resolver = (load_test_repo(args.repository) if args.test else
                    load_registry(args.repository))
        run_stage(args, resolver)
    except (ValueError, OSError, RecursionError) as error:
        raise SystemExit(f'Error: {error}') from error


if __name__ == '__main__':
    main()
