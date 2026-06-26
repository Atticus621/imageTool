"""Topological sort for node graph — pure Python, no Qt dependency."""

from __future__ import annotations

from collections import defaultdict, deque

from core.logger import logger


def topological_sort(nodes: list) -> list:
    """Sort graph nodes topologically using Kahn's algorithm.

    Falls back to partial ordering if a cycle is detected.

    Args:
        nodes: List of graph node objects with input_ports()/output_ports() methods.

    Returns:
        Sorted list of graph nodes.
    """
    in_degree: dict[int, int] = defaultdict(int)
    adjacency: dict[int, list[int]] = defaultdict(list)
    node_set = set(id(n) for n in nodes)

    for node in nodes:
        if id(node) not in in_degree:
            in_degree[id(node)] = 0

        for port in node.input_ports():
            for connected_port in port.connected_ports():
                src = connected_port.node()
                if id(src) in node_set:
                    adjacency[id(src)].append(id(node))
                    in_degree[id(node)] += 1

    queue = deque()
    for node in nodes:
        if in_degree[id(node)] == 0:
            queue.append(node)

    sorted_nodes = []
    while queue:
        node = queue.popleft()
        sorted_nodes.append(node)
        for neighbor_id in adjacency[id(node)]:
            in_degree[neighbor_id] -= 1
            if in_degree[neighbor_id] == 0:
                for n in nodes:
                    if id(n) == neighbor_id:
                        queue.append(n)
                        break

    if len(sorted_nodes) != len(nodes):
        logger.warning("Cycle detected in node graph, falling back to partial sort")

    return sorted_nodes
