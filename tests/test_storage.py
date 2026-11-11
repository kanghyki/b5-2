import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from minigit.repository import MiniGitError, Repository
from minigit.storage import REPOSITORY_DIR, find_root, load, save, state_path


def ticking_clock():
    """호출할 때마다 1분씩 늘어난 시각을 돌려준다."""
    minutes = iter(range(1000))
    return lambda: datetime(2024, 1, 1, 9) + timedelta(minutes=next(minutes))


def hashes(commits):
    return [commit.hash for commit in commits]


def build_repository():
    """두 브랜치와 두 작성자가 있는 저장소를 만든다."""
    repo = Repository(ticking_clock())
    repo.init("Alice")
    repo.commit("Initial commit")
    repo.create_branch("feature")
    repo.switch("feature")
    repo.commit("Add login feature")
    repo.init("Bob Lee")
    repo.commit("Fix login 한글")
    repo.switch("main")
    repo.commit("Add payment feature")
    return repo


class StorageTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_round_trip_keeps_history_and_queries(self):
        original = build_repository()
        save(original, self.root)
        restored = load(self.root)
        self.assertEqual(restored.state(), original.state())
        self.assertEqual(restored.current_branch, "main")
        self.assertEqual(restored.current_user, "Bob Lee")
        self.assertEqual(restored.log(), original.log())
        self.assertEqual(restored.log_sorted_by("author"), original.log_sorted_by("author"))
        for search, term in [("search_keyword", "login"), ("search_author", "Bob Lee")]:
            self.assertEqual(
                hashes(getattr(restored, search)(term)), hashes(getattr(original, search)(term))
            )
        tip = original.log()[-1].hash
        self.assertEqual(hashes(restored.ancestors(tip)), hashes(original.ancestors(tip)))

    def test_restored_repository_continues_hash_sequence(self):
        original = build_repository()
        save(original, self.root)
        restored = load(self.root)
        self.assertEqual(restored.commit("next").hash, original.commit("next").hash)
        self.assertEqual(len(set(hashes(restored.log()))), 5)

    def test_round_trip_of_initialized_empty_repository(self):
        repo = Repository()
        repo.init("Alice")
        repo.create_branch("empty")
        save(repo, self.root)
        restored = load(self.root)
        self.assertEqual(restored.state(), repo.state())
        self.assertEqual(restored.log(), [])

    def test_save_replaces_file_without_leftovers(self):
        repo = build_repository()
        save(repo, self.root)
        repo.commit("more")
        save(repo, self.root)
        self.assertEqual(len(load(self.root).log()), 5)
        files = [path.name for path in (self.root / REPOSITORY_DIR).iterdir()]
        self.assertEqual(files, ["state.json"])

    def test_unwritable_location_is_reported(self):
        (self.root / REPOSITORY_DIR).write_text("not a directory", encoding="utf-8")
        with self.assertRaisesRegex(MiniGitError, "^Cannot write repository: "):
            save(build_repository(), self.root)

    def test_find_root_walks_up_to_repository(self):
        nested = self.root / "a" / "b"
        nested.mkdir(parents=True)
        self.assertIsNone(find_root(nested))
        (self.root / REPOSITORY_DIR).mkdir()
        self.assertEqual(find_root(nested), self.root)
        self.assertEqual(find_root(self.root), self.root)

    def test_corrupted_state_is_reported(self):
        save(build_repository(), self.root)
        valid = json.loads(state_path(self.root).read_text(encoding="utf-8"))

        def broken(**changes):
            return json.dumps({**valid, **changes})

        cases = {
            "not json": "{",
            "wrong shape": "[]",
            "unknown version": broken(version=99),
            "missing field": json.dumps({k: v for k, v in valid.items() if k != "commits"}),
            "unknown parent": broken(commits=[{**valid["commits"][1]}]),
            "duplicate commit": broken(commits=valid["commits"] + valid["commits"][:1]),
            "bad timestamp": broken(commits=[{**valid["commits"][0], "timestamp": "yesterday"}]),
            "branch to unknown commit": broken(branches={"main": "fffffff"}),
            "unknown current branch": broken(current_branch="nope"),
            "counter behind": broken(hash_counter=1),
            "counter not integer": broken(hash_counter="4"),
            "message not string": broken(commits=[{**valid["commits"][0], "message": 1}]),
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                state_path(self.root).write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(MiniGitError, "^Corrupted repository: "):
                    load(self.root)

    def test_missing_state_file_is_reported(self):
        (self.root / REPOSITORY_DIR).mkdir()
        with self.assertRaisesRegex(MiniGitError, "^Corrupted repository: "):
            load(self.root)


if __name__ == "__main__":
    unittest.main()
