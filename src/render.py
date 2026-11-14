"""Generate D2 diagrams, readable SVG graphics, and ASCII dependency trees."""

from collections import deque
from html import escape

NODE_WIDTH = 225
NODE_HEIGHT = 34
ROW_GAP = 66
COL_GAP = 300
MARGIN = 40


def label(node):
    """Format a package and its chosen version."""
    return f'{node[0]}@{node[1]}'


def make_d2(graph):
    """Create a D2 specification with quoted unique identifiers."""
    lines = ['direction: right']
    for node, children in sorted(graph.items()):
        left = label(node).replace('\\', '\\\\').replace('"', '\\"')
        if not children:
            lines.append(f'"{left}"')
        for child in children:
            right = label(child).replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'"{left}" -> "{right}"')
    return '\n'.join(lines) + '\n'


def make_tree(root, graph):
    """Show recursive ASCII branches, indicating repeated packages."""
    lines = [label(root)]

    def walk(node, indent, seen):
        """Recursively expand the dependency branches."""
        for index, child in enumerate(graph.get(node, [])):
            final = index == len(graph[node]) - 1
            repeat = child in seen
            branch = '`-- ' if final else '|-- '
            suffix = ' [cycle/shared]' if repeat else ''
            lines.append(indent + branch + label(child) + suffix)
            if not repeat:
                continuation = '    ' if final else '|   '
                walk(child, indent + continuation, seen | {child})

    walk(root, '', {root})
    return '\n'.join(lines)


def layout(graph):
    """Place graph nodes by BFS depth, giving each depth its own column."""
    nodes = sorted(set(graph) | {child for kids in graph.values()
                                 for child in kids})
    incoming = {child for children in graph.values() for child in children}
    roots = [node for node in nodes if node not in incoming]
    if not roots and nodes:
        roots = [nodes[0]]
    depth = {}
    queue = deque((node, 0) for node in roots)
    while queue:
        node, level = queue.popleft()
        if node in depth:
            continue
        depth[node] = level
        queue.extend((child, level + 1) for child in graph.get(node, []))
    for node in nodes:
        depth.setdefault(node, 0)
    grouped = {}
    for node in nodes:
        grouped.setdefault(depth[node], []).append(node)
    position = {}
    for level, members in grouped.items():
        for index, node in enumerate(members):
            position[node] = (MARGIN + COL_GAP * level,
                              MARGIN + ROW_GAP * index)
    width = MARGIN * 2 + COL_GAP * max(depth.values(), default=0)
    height = MARGIN * 2 + ROW_GAP * (
        max((len(members) for members in grouped.values()), default=1) - 1
    )
    return position, width + NODE_WIDTH, height + NODE_HEIGHT


def make_svg(graph):
    """Draw valid SVG with all arrows touching their actual nodes."""
    positions, width, height = layout(graph)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
        'refX="7" refY="3" orient="auto" markerUnits="strokeWidth">'
        '<path d="M0,0 L0,6 L7,3 z" fill="#475569"/>'
        '</marker></defs>',
    ]
    for node, children in graph.items():
        x, y = positions[node]
        for child in children:
            tx, ty = positions[child]
            start_x = x + NODE_WIDTH if tx > x else x + NODE_WIDTH // 2
            end_x = tx if tx > x else tx + NODE_WIDTH // 2
            start_y, end_y = y + NODE_HEIGHT // 2, ty + NODE_HEIGHT // 2
            lines.append(f'<path d="M{start_x} {start_y} L{end_x} '
                         f'{end_y}" stroke="#475569" fill="none" '
                         'marker-end="url(#arrow)"/>')
    for node, (x, y) in positions.items():
        lines.append(f'<rect x="{x}" y="{y}" width="{NODE_WIDTH}" '
                     f'height="{NODE_HEIGHT}" rx="5" fill="#dbeafe" '
                     'stroke="#2563eb"/>')
        lines.append(f'<text x="{x + 9}" y="{y + 22}" '
                     'font-size="13" font-family="sans-serif">'
                     f'{escape(label(node))}</text>')
    return '\n'.join(lines + ['</svg>'])
