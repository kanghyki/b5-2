import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from minigit.cli import run_cli
from minigit.storage import REPOSITORY_DIR, state_path

MAIN = Path(__file__).resolve().parent.parent / "main.py"


class CliTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def run_cli(self, *argv, cwd=None):
        """명령 하나를 실행해 (종료 코드, stdout, stderr)를 돌려준다."""
        stdout, stderr = io.StringIO(), io.StringIO()
        code = run_cli(list(argv), cwd or self.root, stdout, stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def commit(self, message, cwd=None):
        code, out, _ = self.run_cli("commit", message, cwd=cwd)
        self.assertEqual(code, 0)
        return re.match(r"\[\S+ (\w+)\]", out).group(1)

    def test_init_creates_repository_in_current_directory(self):
        self.assertEqual(
            self.run_cli("init", "Alice Kim"),
            (0, "Initialized repository.\nCurrent branch: main\nCurrent user: Alice Kim\n", ""),
        )
        self.assertTrue(state_path(self.root).is_file())

    def test_history_persists_across_invocations(self):
        self.run_cli("init", "Alice")
        root = self.commit("Initial commit")
        self.run_cli("branch", "feature")
        self.run_cli("SWITCH", "feature")
        login = self.commit("Add login feature")
        self.run_cli("switch", "main")
        payment = self.commit("Add payment feature")

        code, out, _ = self.run_cli("log")
        self.assertEqual(code, 0)
        self.assertEqual(re.findall(r"^commit (\w+)", out, re.M), [root, login, payment])
        self.assertEqual(
            self.run_cli("path", login, payment)[1], f"Path: {login} -> {root} -> {payment}\n"
        )
        self.assertEqual(
            self.run_cli("search", "login")[1], f"Found 1 commit:\n- {login}: Add login feature\n"
        )

    def test_reinit_keeps_history_and_changes_user(self):
        self.run_cli("init", "Alice")
        first = self.commit("one")
        code, out, _ = self.run_cli("init", "Bob")
        self.assertEqual((code, out.splitlines()[0]), (0, "Reinitialized repository."))
        second = self.commit("two")
        self.assertEqual(
            self.run_cli("search", "--author=Bob")[1], f"Found 1 commit:\n- {second}: two\n"
        )
        self.assertEqual(
            self.run_cli("ancestors", second)[1], f"Found 1 ancestor:\n- {first}: one\n"
        )

    def test_finds_repository_from_subdirectory(self):
        self.run_cli("init", "Alice")
        nested = self.root / "src" / "pkg"
        nested.mkdir(parents=True)
        commit_hash = self.commit("from nested", cwd=nested)
        self.assertIn(commit_hash, self.run_cli("log")[1])
        self.assertFalse((nested / REPOSITORY_DIR).exists())

    def test_arguments_are_not_split_again(self):
        self.run_cli("init", "Alice")
        message = 'Say "hi" to it\'s owner'
        commit_hash = self.commit(message)
        self.assertEqual(
            self.run_cli("search", "owner")[1], f"Found 1 commit:\n- {commit_hash}: {message}\n"
        )

    def test_errors_go_to_stderr_with_failure_code(self):
        self.assertEqual(self.run_cli("log"), (1, "", "Repository not initialized\n"))
        self.assertEqual(self.run_cli("commit", "x"), (1, "", "Repository not initialized\n"))
        self.assertFalse((self.root / REPOSITORY_DIR).exists())
        self.run_cli("init", "Alice")
        self.assertEqual(self.run_cli("switch", "nope"), (1, "", "Unknown branch: nope\n"))
        self.assertEqual(self.run_cli("commit", "a", "b"), (1, "", "Invalid args\n"))
        self.assertEqual(self.run_cli("exit"), (1, "", "Unknown command: exit\n"))

    def test_failed_and_read_only_commands_do_not_rewrite_state(self):
        self.run_cli("init", "Alice")
        self.commit("one")
        before = state_path(self.root).read_bytes()
        for argv in [("log",), ("search", "one"), ("branch", "main"), ("switch", "nope")]:
            with self.subTest(argv=argv):
                self.run_cli(*argv)
                self.assertEqual(state_path(self.root).read_bytes(), before)

    def test_corrupted_repository_is_reported(self):
        self.run_cli("init", "Alice")
        state_path(self.root).write_text("{", encoding="utf-8")
        code, out, err = self.run_cli("log")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("Corrupted repository: "))

    def test_diff_works_without_repository(self):
        (self.root / "a.txt").write_text("same\nold\n", encoding="utf-8")
        (self.root / "b.txt").write_text("same\nnew\n", encoding="utf-8")
        code, out, _ = self.run_cli("diff", str(self.root / "a.txt"), str(self.root / "b.txt"))
        self.assertEqual(code, 0)
        self.assertIn("  same\n- old\n+ new\n", out)
        self.assertFalse((self.root / REPOSITORY_DIR).exists())


class MainTest(unittest.TestCase):
    """main.py가 인자에 따라 CLI와 REPL로 나뉘는지 실제 프로세스로 확인한다."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def main(self, *args, stdin=""):
        return subprocess.run(
            [sys.executable, str(MAIN), *args],
            input=stdin,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_arguments_run_one_command_and_persist(self):
        self.assertEqual(self.main("init", "Alice").returncode, 0)
        self.assertEqual(self.main("commit", "First change").returncode, 0)
        result = self.main("log")
        self.assertEqual(result.returncode, 0)
        self.assertIn("    First change", result.stdout)

    def test_failure_exit_code(self):
        result = self.main("log")
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertEqual(result.stderr, "Repository not initialized\n")

    def test_no_arguments_start_in_memory_repl(self):
        result = self.main(stdin="init Alice\ncommit first\nexit\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("mini-git> ", result.stdout)
        self.assertFalse((self.root / REPOSITORY_DIR).exists())


if __name__ == "__main__":
    unittest.main()
