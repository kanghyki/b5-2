import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from minigit.cli import MiniGitCli

ROOT = Path(__file__).resolve().parent.parent


def committed_hash(output):
    """COMMIT 출력 "[브랜치 해시] 메시지"에서 해시를 꺼낸다."""
    return re.match(r"\[\S+ (\w+)\]", output).group(1)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.cli = MiniGitCli()
        self.cli.execute('init "Alice"')

    def commit(self, message):
        return committed_hash(self.cli.execute(f'commit "{message}"'))

    def test_command_names_ignore_case(self):
        cli = MiniGitCli()
        self.assertIn("Initialized repository.", cli.execute("INIT Alice"))
        self.assertIn("Created branch: dev", cli.execute("BrAnCh dev"))
        self.assertIn("Switched to branch: dev", cli.execute("SWITCH dev"))
        self.assertEqual(cli.execute("LOG"), "No commits")

    def test_branch_names_keep_case(self):
        self.cli.execute("branch Dev")
        self.assertEqual(self.cli.execute("switch dev"), "Unknown branch: dev")

    def test_init_output(self):
        self.assertEqual(
            MiniGitCli().execute('init "Alice Kim"'),
            "Initialized repository.\nCurrent branch: main\nCurrent user: Alice Kim",
        )

    def test_quoted_arguments_can_contain_spaces(self):
        output = self.cli.execute('commit "Add login feature"')
        self.assertRegex(output, r"^\[main \w{7}\] Add login feature$")

    def test_invalid_args(self):
        lines = [
            "init",
            'init ""',
            "init Alice Bob",
            "branch",
            "branch a b",
            'branch "a b"',
            "switch",
            "commit",
            'commit ""',
            'commit "   "',
            "commit Add login",
            'commit "unterminated',
            "log extra",
            "log --sort-by",
            "log --sort-by=size",
            "log --sort-by=date extra",
            "log --order=date",
            "path",
            "path onlyone",
            "path a b c",
            "ancestors",
            "ancestors a b",
            "search",
            'search "  "',
            "search a b",
            "search --author",
            "search --author=",
            "search --unknown=x",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(self.cli.execute(line), "Invalid args")

    def test_standard_errors(self):
        self.assertEqual(self.cli.execute("switch nope"), "Unknown branch: nope")
        self.assertEqual(self.cli.execute("path a b"), "Unknown commit: a")
        self.assertEqual(self.cli.execute("ancestors a"), "Unknown commit: a")
        self.assertEqual(self.cli.execute("branch main"), "Branch already exists: main")
        self.assertEqual(self.cli.execute("frobnicate"), "Unknown command: frobnicate")
        self.assertEqual(MiniGitCli().execute("log"), "Repository not initialized")

    def test_blank_line_produces_no_output(self):
        self.assertEqual(self.cli.execute("   "), "")

    def test_log_shows_required_fields(self):
        commit_hash = self.commit("First change")
        self.assertRegex(
            self.cli.execute("log"),
            rf"^commit {commit_hash} \(Alice, \d{{4}}-\d\d-\d\d \d\d:\d\d:\d\d\) \[main\]\n"
            r"    First change$",
        )

    def test_log_sort_options(self):
        first = self.commit("one")
        self.cli.execute("init Aaron")
        second = self.commit("two")
        by_author = self.cli.execute("LOG --SORT-BY=AUTHOR")
        self.assertLess(by_author.index(second), by_author.index(first))
        by_date = self.cli.execute("log --sort-by=date")
        self.assertLess(by_date.index(first), by_date.index(second))

    def test_path_outputs(self):
        root = self.commit("root")
        self.cli.execute("branch feature")
        left = self.commit("left")
        self.cli.execute("switch feature")
        right = self.commit("right")
        self.assertEqual(
            self.cli.execute(f"path {left} {right}"), f"Path: {left} -> {root} -> {right}"
        )
        self.assertEqual(self.cli.execute(f"path {root} {root}"), f"Path: {root}")

    def test_no_path_output(self):
        self.cli.execute("branch other")
        main_root = self.commit("main root")
        self.cli.execute("switch other")
        other_root = self.commit("other root")
        self.assertEqual(self.cli.execute(f"path {main_root} {other_root}"), "No path")

    def test_ancestors_output(self):
        root = self.commit("root")
        tip = self.commit("tip")
        self.assertEqual(
            self.cli.execute(f"ancestors {tip}"), f"Found 1 ancestor:\n- {root}: root"
        )
        self.assertEqual(self.cli.execute(f"ancestors {root}"), "No ancestors found")

    def test_search_outputs(self):
        login = self.commit("Add login feature")
        self.assertEqual(
            self.cli.execute('search "LOGIN"'), f"Found 1 commit:\n- {login}: Add login feature"
        )
        self.assertEqual(self.cli.execute("search payment"), "No commits found")
        self.cli.execute('init "Bob Lee"')
        second = self.commit("Fix login")
        self.assertEqual(
            self.cli.execute('search --author="Bob Lee"'), f"Found 1 commit:\n- {second}: Fix login"
        )
        self.assertEqual(
            self.cli.execute("search login"),
            f"Found 2 commits:\n- {login}: Add login feature\n- {second}: Fix login",
        )


class DiffCommandTest(unittest.TestCase):
    def setUp(self):
        self.cli = MiniGitCli()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_marks_added_deleted_and_common_lines_without_init(self):
        old = self.write("old.txt", "keep\nremove me\nend\n")
        new = self.write("new file.txt", "keep\nadd me\nend\n")
        self.assertEqual(
            self.cli.execute(f'DIFF {old} "{new}"'),
            f"--- {old}\n+++ {new}\n"
            "  keep\n- remove me\n+ add me\n  end\n"
            "1 added, 1 deleted, 2 common",
        )

    def test_invalid_args(self):
        old = self.write("old.txt", "a\n")
        for line in ["diff", f"diff {old}", f"diff {old} {old} {old}", f'diff {old} ""']:
            with self.subTest(line=line):
                self.assertEqual(self.cli.execute(line), "Invalid args")

    def test_unreadable_files(self):
        old = self.write("old.txt", "a\n")
        missing = str(self.dir / "missing.txt")
        binary = self.dir / "binary.bin"
        binary.write_bytes(b"\xff\xfe\x00")
        self.assertEqual(self.cli.execute(f"diff {old} {missing}"), f"Cannot read file: {missing}")
        self.assertEqual(self.cli.execute(f"diff {binary} {old}"), f"Cannot read file: {binary}")
        self.assertEqual(
            self.cli.execute(f"diff {self.dir} {old}"), f"Cannot read file: {self.dir}"
        )


class ReplTest(unittest.TestCase):
    def run_repl(self, stdin):
        return subprocess.run(
            [sys.executable, "main.py"],
            input=stdin,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout

    def test_repeats_until_exit_and_ignores_following_input(self):
        output = self.run_repl("init Alice\ncommit first\nEXIT\ncommit second\n")
        self.assertIn("Initialized repository.", output)
        self.assertIn("] first", output)
        self.assertNotIn("second", output)

    def test_quit_ends_session(self):
        self.assertEqual(self.run_repl("quit\n"), "mini-git> ")

    def test_end_of_input_ends_session(self):
        self.assertEqual(self.run_repl(""), "mini-git> \n")

    def test_error_does_not_end_session(self):
        output = self.run_repl("bad\nlog\nexit\n")
        self.assertIn("Unknown command: bad", output)
        self.assertIn("Repository not initialized", output)


if __name__ == "__main__":
    unittest.main()
