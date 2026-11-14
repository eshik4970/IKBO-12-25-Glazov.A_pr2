"""Visualize Cargo dependency graphs from a registry or JSON fixture."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from graph import build_graph, load_registry, load_test_repo, loading_order
from render import make_d2, make_svg, make_tree
from semver import parse_version


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
    if not args.package.strip() or not args.version.strip():
        parser.error('Package and version must not be empty')
    if not args.output.lower().endswith('.svg'):
        parser.error('Output filename must have .svg extension')
    if args.test:
        if not re.fullmatch(r'[A-Z]+', args.package):
            parser.error('Test package names must use uppercase Latin letters')
        if not Path(args.repository).is_file():
            parser.error('Test repository file does not exist')
    else:
        url = urlparse(args.repository)
        if url.scheme != 'https' or not url.netloc:
            parser.error('Repository must be an HTTPS URL')
        try:
            parse_version(args.version)
        except ValueError as error:
            parser.error(str(error))
    return args


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


def main(argv=None):
    """Execute one of the five required practical-work stages."""
    args = arguments(argv)
    if args.stage == 1:
        print_configuration(args)
        return
    try:
        resolver = (load_test_repo(args.repository) if args.test else
                    load_registry(args.repository))
        root = (args.package, args.version)
        if args.stage == 2:
            for name, version in resolver(root):
                print(f'{name} {version}')
            return
        graph = build_graph(root, resolver, args.filter)
        if args.stage == 3:
            print(json.dumps({f'{n}@{v}': [f'{a}@{b}' for a, b in children]
                              for (n, v), children in graph.items()}, indent=2))
            return
        if args.stage == 4:
            for name, version in loading_order(graph):
                print(f'{name}@{version}')
            return
        if args.ascii:
            print(make_tree(root, graph))
        save_diagrams(graph, args.output)
    except (ValueError, OSError, RecursionError) as error:
        raise SystemExit(f'Error: {error}') from error


if __name__ == '__main__':
    main()
