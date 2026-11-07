import unittest

from minigit.graph import CommitGraph
from tests.helpers import make_commit, make_graph


class CommitGraphTest(unittest.TestCase):
    def test_finds_commit_by_hash(self):
        graph = make_graph([("a", [])])
        self.assertEqual(graph.get("a").hash, "a")
        self.assertIsNone(graph.get("missing"))
        self.assertIn("a", graph)
        self.assertNotIn("missing", graph)

    def test_tracks_edges_in_both_directions(self):
        graph = make_graph([("a", []), ("b", ["a"]), ("c", ["a"]), ("d", ["b", "c"])])
        self.assertEqual(graph.parents("d"), ("b", "c"))
        self.assertEqual(graph.children("a"), ["b", "c"])
        self.assertEqual(graph.neighbors("b"), ["a", "d"])

    def test_iterates_in_creation_order(self):
        graph = make_graph([("z", []), ("a", ["z"]), ("m", ["a"])])
        self.assertEqual(list(graph), ["z", "a", "m"])
        self.assertEqual(len(graph), 3)

    def test_rejects_duplicate_hash(self):
        graph = make_graph([("a", [])])
        with self.assertRaises(ValueError):
            graph.add(make_commit("a"))

    def test_rejects_unknown_parent_without_partial_update(self):
        graph = make_graph([("a", [])])
        with self.assertRaises(ValueError):
            graph.add(make_commit("b", ["a", "missing"]))
        self.assertNotIn("b", graph)
        self.assertEqual(graph.children("a"), [])

    def test_empty_graph(self):
        self.assertEqual(len(CommitGraph()), 0)


if __name__ == "__main__":
    unittest.main()
