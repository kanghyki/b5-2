import unittest
from datetime import datetime, timedelta

from minigit.repository import HashGenerator, MiniGitError, Repository


def fixed_clock(*minutes):
    """지정한 분(minute) 값을 차례로 돌려주는 시계를 만든다."""
    values = iter(minutes)
    return lambda: datetime(2024, 1, 1) + timedelta(minutes=next(values))


def hashes(commits):
    return [commit.hash for commit in commits]


class HashGeneratorTest(unittest.TestCase):
    def test_generates_unique_fixed_width_hashes(self):
        generator = HashGenerator()
        values = [generator.next() for _ in range(100000)]
        self.assertEqual(len(set(values)), len(values))
        for value in values[:100]:
            self.assertEqual(len(value), 7)


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.repo.init("Alice")

    def test_init_creates_main_and_sets_user(self):
        self.assertEqual(self.repo.current_branch, "main")
        self.assertEqual(self.repo.current_user, "Alice")

    def test_commands_require_init(self):
        repo = Repository()
        calls = [
            lambda: repo.commit("x"),
            lambda: repo.create_branch("x"),
            lambda: repo.switch("main"),
            repo.log,
            lambda: repo.log_sorted_by("date"),
            lambda: repo.path("a", "b"),
            lambda: repo.ancestors("a"),
            lambda: repo.search_keyword("x"),
            lambda: repo.search_author("x"),
        ]
        for call in calls:
            with self.assertRaisesRegex(MiniGitError, "Repository not initialized"):
                call()

    def test_reinit_keeps_history_and_changes_author(self):
        first = self.repo.commit("one")
        self.repo.create_branch("feature")
        self.repo.switch("feature")
        self.assertFalse(self.repo.init("Bob"))
        second = self.repo.commit("two")
        self.assertEqual(self.repo.current_branch, "feature")
        self.assertEqual(second.author, "Bob")
        self.assertEqual(second.parents, (first.hash,))

    def test_commit_links_to_head_of_current_branch(self):
        root = self.repo.commit("root")
        child = self.repo.commit("child")
        self.assertEqual(root.parents, ())
        self.assertEqual(child.parents, (root.hash,))
        self.assertEqual(child.branch, "main")

    def test_branch_starts_from_head_and_diverges(self):
        root = self.repo.commit("root")
        self.repo.create_branch("feature")
        self.repo.switch("feature")
        feature = self.repo.commit("feature work")
        self.repo.switch("main")
        main = self.repo.commit("main work")
        self.assertEqual(feature.parents, (root.hash,))
        self.assertEqual(main.parents, (root.hash,))

    def test_rejects_duplicate_and_unknown_branch(self):
        with self.assertRaisesRegex(MiniGitError, "Branch already exists: main"):
            self.repo.create_branch("main")
        with self.assertRaisesRegex(MiniGitError, "Unknown branch: nope"):
            self.repo.switch("nope")

    def test_branches_from_empty_head_make_disconnected_roots(self):
        self.repo.create_branch("other")
        first = self.repo.commit("main root")
        self.repo.switch("other")
        second = self.repo.commit("other root")
        self.assertEqual(second.parents, ())
        self.assertIsNone(self.repo.path(first.hash, second.hash))

    def test_log_includes_all_branches_with_parents_first(self):
        root = self.repo.commit("root")
        self.repo.create_branch("feature")
        self.repo.switch("feature")
        feature = self.repo.commit("feature")
        self.repo.switch("main")
        main = self.repo.commit("main")
        self.assertEqual(hashes(self.repo.log()), [root.hash, feature.hash, main.hash])

    def test_log_sorted_by_date_uses_timestamp(self):
        repo = Repository(clock=fixed_clock(30, 10, 20))
        repo.init("Alice")
        late, early, middle = repo.commit("a"), repo.commit("b"), repo.commit("c")
        self.assertEqual(
            hashes(repo.log_sorted_by("date")), [early.hash, middle.hash, late.hash]
        )

    def test_log_sorted_by_author_keeps_creation_order_on_ties(self):
        self.repo.init("Carol")
        first = self.repo.commit("a")
        self.repo.init("Alice")
        second = self.repo.commit("b")
        self.repo.init("bob")
        third = self.repo.commit("c")
        self.repo.init("Alice")
        fourth = self.repo.commit("d")
        self.assertEqual(
            hashes(self.repo.log_sorted_by("author")),
            [second.hash, fourth.hash, third.hash, first.hash],
        )

    def test_path_and_ancestors_reject_unknown_commit(self):
        known = self.repo.commit("root")
        with self.assertRaisesRegex(MiniGitError, "Unknown commit: nope"):
            self.repo.path(known.hash, "nope")
        with self.assertRaisesRegex(MiniGitError, "Unknown commit: nope"):
            self.repo.path("nope", known.hash)
        with self.assertRaisesRegex(MiniGitError, "Unknown commit: nope"):
            self.repo.ancestors("nope")

    def test_ancestors_follow_only_parents(self):
        root = self.repo.commit("root")
        self.repo.create_branch("feature")
        middle = self.repo.commit("middle")
        tip = self.repo.commit("tip")
        self.repo.switch("feature")
        self.repo.commit("other")
        self.assertEqual(hashes(self.repo.ancestors(tip.hash)), [middle.hash, root.hash])

    def test_search_keyword_is_case_insensitive_and_token_based(self):
        login = self.repo.commit("Add LOGIN feature")
        self.repo.commit("relogin later")
        self.assertEqual(hashes(self.repo.search_keyword("login")), [login.hash])
        self.assertEqual(self.repo.search_keyword("missing"), [])

    def test_search_keyword_with_spaces_requires_consecutive_tokens(self):
        match = self.repo.commit("Add login feature")
        self.repo.commit("login then add")
        self.assertEqual(hashes(self.repo.search_keyword("ADD login")), [match.hash])

    def test_search_returns_commit_once_when_token_repeats(self):
        commit = self.repo.commit("fix bug fix")
        self.assertEqual(hashes(self.repo.search_keyword("fix")), [commit.hash])

    def test_search_author_matches_exact_name(self):
        alice = self.repo.commit("a")
        self.repo.init("Bob Lee")
        bob = self.repo.commit("b")
        self.assertEqual(hashes(self.repo.search_author("Alice")), [alice.hash])
        self.assertEqual(hashes(self.repo.search_author("Bob Lee")), [bob.hash])
        self.assertEqual(self.repo.search_author("Bob"), [])


if __name__ == "__main__":
    unittest.main()
