import random
import unittest

from minigit.graph import CommitGraph
from minigit.traversal import find_ancestors, shortest_path, topological_order
from tests.helpers import make_graph

DIAMOND = [("a", []), ("b", ["a"]), ("c", ["a"]), ("d", ["b", "c"])]


def all_shortest_paths(graph, start, goal):
    """검증용 완전 탐색: 단순 경로를 모두 나열해 가장 짧은 것들만 남긴다."""
    found = []

    def walk(path):
        if path[-1] == goal:
            found.append(path)
            return
        for neighbor in graph.neighbors(path[-1]):
            if neighbor not in path:
                walk(path + [neighbor])

    walk([start])
    if not found:
        return []
    length = min(len(path) for path in found)
    return [path for path in found if len(path) == length]


def random_graph(rng, size, names):
    """무작위 DAG를 만든다. 뿌리가 여러 개여서 끊어진 그래프도 나올 수 있다."""
    graph = CommitGraph()
    edges = []
    for index in range(size):
        count = rng.randint(0, min(index, 2))
        edges.append((names[index], rng.sample(names[:index], count)))
    return make_graph(edges) if edges else graph


class TopologicalOrderTest(unittest.TestCase):
    def assert_parents_first(self, graph, order):
        position = {commit: index for index, commit in enumerate(order)}
        self.assertEqual(len(position), len(graph))
        for commit in graph:
            for parent in graph.parents(commit):
                self.assertLess(position[parent], position[commit])

    def test_empty_graph(self):
        self.assertEqual(topological_order(CommitGraph()), [])

    def test_diamond(self):
        graph = make_graph(DIAMOND)
        self.assertEqual(topological_order(graph), ["a", "b", "c", "d"])

    def test_waits_for_every_parent_of_merge_commit(self):
        graph = make_graph([("a", []), ("b", ["a"]), ("c", []), ("d", ["b", "c"])])
        self.assert_parents_first(graph, topological_order(graph))

    def test_random_graphs(self):
        rng = random.Random(1)
        names = [f"{value:x}" for value in range(16, 46)]
        for _ in range(200):
            graph = random_graph(rng, rng.randint(1, 30), names)
            self.assert_parents_first(graph, topological_order(graph))


class FindAncestorsTest(unittest.TestCase):
    def test_root_has_no_ancestors(self):
        self.assertEqual(find_ancestors(make_graph(DIAMOND), "a"), [])

    def test_visits_shared_ancestor_once_and_excludes_self(self):
        self.assertEqual(find_ancestors(make_graph(DIAMOND), "d"), ["b", "c", "a"])

    def test_does_not_include_sibling_branch(self):
        self.assertEqual(find_ancestors(make_graph(DIAMOND), "b"), ["a"])

    def test_handles_long_chain_without_recursion_limit(self):
        size = 20000
        edges = [("0", [])] + [(str(i), [str(i - 1)]) for i in range(1, size)]
        self.assertEqual(len(find_ancestors(make_graph(edges), str(size - 1))), size - 1)


class ShortestPathTest(unittest.TestCase):
    def test_same_commit(self):
        self.assertEqual(shortest_path(make_graph(DIAMOND), "a", "a"), ["a"])

    def test_follows_edges_in_either_direction(self):
        graph = make_graph([("a", []), ("b", ["a"]), ("c", ["a"])])
        self.assertEqual(shortest_path(graph, "b", "c"), ["b", "a", "c"])
        self.assertEqual(shortest_path(graph, "c", "b"), ["c", "a", "b"])

    def test_picks_lexicographically_smallest_of_equal_paths(self):
        graph = make_graph(DIAMOND)
        self.assertEqual(shortest_path(graph, "a", "d"), ["a", "b", "d"])
        self.assertEqual(shortest_path(graph, "d", "a"), ["d", "b", "a"])

    def test_prefers_fewer_edges_over_smaller_hash(self):
        graph = make_graph([("z", []), ("a", ["z"]), ("b", ["a"]), ("y", ["z", "b"])])
        self.assertEqual(shortest_path(graph, "z", "y"), ["z", "y"])

    def test_returns_none_between_disconnected_commits(self):
        graph = make_graph([("a", []), ("b", [])])
        self.assertIsNone(shortest_path(graph, "a", "b"))

    def test_matches_exhaustive_search(self):
        rng = random.Random(2)
        name_sets = [
            [f"{value:02x}" for value in range(16, 26)],
            ["1", "10", "11", "2", "20", "a", "a1", "b", "b0", "c"],
        ]
        for _ in range(300):
            names = rng.sample(rng.choice(name_sets), 10)
            graph = random_graph(rng, rng.randint(1, 10), names)
            commits = list(graph)
            start, goal = rng.choice(commits), rng.choice(commits)
            candidates = all_shortest_paths(graph, start, goal)
            actual = shortest_path(graph, start, goal)
            if candidates:
                expected = min("->".join(path) for path in candidates)
                self.assertEqual("->".join(actual), expected)
            else:
                self.assertIsNone(actual)


if __name__ == "__main__":
    unittest.main()
