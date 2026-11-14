"""Executable regression tests for all five practical-work stages."""

import sys
import tempfile
import unittest
from xml.etree import ElementTree
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from graph import build_graph, load_registry, load_test_repo, loading_order
from graph import select_version
from main import arguments, main
from render import layout, make_d2, make_svg, make_tree
from semver import matches


class DependencyTests(unittest.TestCase):
    """Validate algorithms and user-facing stages."""

    def create_fixture(self):
        """Supply a graph featuring a shared transitive dependency."""
        self.data = {'A': ['B', 'C'], 'B': ['D'],
                     'C': ['D'], 'D': []}

    def resolve(self, node):
        """Resolve a test fixture without network requests."""
        return [(name, 'test') for name in self.data[node[0]]]

    def test_bfs(self):
        """All reachable vertices are visited once."""
        self.create_fixture()
        graph = build_graph(('A', 'test'), self.resolve)
        self.assertEqual(len(graph), 4)
        self.assertEqual(len(graph[('A', 'test')]), 2)

    def test_filter(self):
        """Substring filtering omits matching nodes."""
        self.create_fixture()
        graph = build_graph(('A', 'test'), self.resolve, 'B')
        self.assertNotIn(('B', 'test'), graph)

    def test_cycle(self):
        """Cycle traversal terminates, topological order rejects cycles."""
        self.create_fixture()
        self.data['D'] = ['A']
        graph = build_graph(('A', 'test'), self.resolve)
        self.assertEqual(len(graph), 4)
        with self.assertRaisesRegex(ValueError, 'Cycle'):
            loading_order(graph)

    def test_order(self):
        """Children occur before their dependent parents."""
        self.create_fixture()
        graph = build_graph(('A', 'test'), self.resolve)
        order = loading_order(graph)
        self.assertEqual(order[-1], ('A', 'test'))
        for parent, children in graph.items():
            for child in children:
                self.assertLess(order.index(child), order.index(parent))

    def test_render(self):
        """Produce D2, valid SVG XML and an ASCII tree."""
        self.create_fixture()
        graph = build_graph(('A', 'test'), self.resolve)
        self.assertIn('->', make_d2(graph))
        self.assertIn('|--', make_tree(('A', 'test'), graph))
        root = ElementTree.fromstring(make_svg(graph))
        self.assertTrue(root.tag.endswith('svg'))
        positions, _, _ = layout(graph)
        self.assertEqual(len(positions), 4)

    def test_semver_caret(self):
        """Caret allows compatible minor versions, not breaking majors."""
        self.assertTrue(matches('1.9.0', '^1.2'))
        self.assertFalse(matches('2.0.0', '^1.2'))
        self.assertTrue(matches('0.2.9', '^0.2.1'))
        self.assertFalse(matches('0.3.0', '^0.2.1'))

    def test_semver_ranges(self):
        """Combine multiple comparators and exclude prereleases."""
        self.assertTrue(matches('1.6.0', '>=1.2, <2.0'))
        self.assertFalse(matches('2.1.0', '>=1.2, <2.0'))
        self.assertFalse(matches('1.7.0-beta.1', '^1.2'))
        self.assertTrue(matches('1.7.0-beta.2', '^1.7.0-beta.1'))

    def test_pick_version(self):
        """Select the highest compatible non-yanked release."""
        versions = [{'num': '1.2.0'}, {'num': '1.9.0'},
                    {'num': '2.0.0'}, {'num': '1.9.1', 'yanked': True}]
        self.assertEqual(select_version(versions, '^1.2'), '1.9.0')

    def test_invalid_test_graph(self):
        """Reject Cyrillic, missing nodes and malformed JSON."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'
            for bad in ['{"А": []}', '{"A": ["Z"]}', '{broken']:
                path.write_text(bad, encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_test_repo(path)

    def test_cli_validation(self):
        """Disallow bad options before executing network requests."""
        with self.assertRaises(SystemExit):
            arguments(['--package', 'A', '--repository', 'http://unsafe',
                       '--version', '1.0.0'])
        with self.assertRaises(SystemExit):
            arguments(['--package', 'A', '--repository', 'https://crates.io',
                       '--version', '1.0.0', '--output', 'wrong.png'])

    def test_all_stages_local(self):
        """Execute every CLI stage using an actual test JSON file."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'repo.json'
            path.write_text('{"A": ["B"], "B": []}', encoding='utf-8')
            for stage in range(1, 6):
                result = str(Path(directory) / 'result.svg')
                main(['--test', '--package', 'A', '--version', 'test',
                      '--repository', str(path), '--stage', str(stage),
                      '--output', result])
            self.assertTrue(Path(result).is_file())
            self.assertTrue(Path(result).with_suffix('.d2').is_file())


if __name__ == '__main__':
    unittest.main()
