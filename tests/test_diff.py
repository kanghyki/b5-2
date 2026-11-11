import unittest

from minigit.diff import ADDED, COMMON, DELETED, diff_lines


def lcs_length(entries):
    return sum(1 for mark, _ in entries if mark == COMMON)


def side(entries, keep):
    """diff 결과에서 한쪽 파일을 다시 만든다."""
    return [line for mark, line in entries if mark in keep]


class DiffLinesTest(unittest.TestCase):
    def assertReconstructs(self, old, new, entries):
        self.assertEqual(side(entries, (COMMON, DELETED)), old)
        self.assertEqual(side(entries, (COMMON, ADDED)), new)

    def test_identical_files_are_all_common(self):
        lines = ["a", "b", "c"]
        self.assertEqual(diff_lines(lines, lines), [(COMMON, "a"), (COMMON, "b"), (COMMON, "c")])

    def test_empty_inputs(self):
        self.assertEqual(diff_lines([], []), [])
        self.assertEqual(diff_lines([], ["a"]), [(ADDED, "a")])
        self.assertEqual(diff_lines(["a"], []), [(DELETED, "a")])

    def test_changed_line_puts_deletion_before_addition(self):
        self.assertEqual(
            diff_lines(["a", "b", "c"], ["a", "x", "c"]),
            [(COMMON, "a"), (DELETED, "b"), (ADDED, "x"), (COMMON, "c")],
        )

    def test_insertion_and_deletion_in_middle(self):
        self.assertEqual(
            diff_lines(["a", "b", "c", "d"], ["a", "c", "e", "d"]),
            [(COMMON, "a"), (DELETED, "b"), (COMMON, "c"), (ADDED, "e"), (COMMON, "d")],
        )

    def test_keeps_longest_common_subsequence(self):
        old = ["a", "b", "c", "a", "b", "b", "a"]
        new = ["c", "b", "a", "b", "a", "c"]
        entries = diff_lines(old, new)
        self.assertReconstructs(old, new, entries)
        self.assertEqual(lcs_length(entries), 4)

    def test_duplicate_lines_reconstruct_both_sides(self):
        cases = [
            (["x", "x", "x"], ["x", "x"]),
            (["a", "a", "b"], ["b", "a", "a"]),
            (["", "a", ""], ["a", "", ""]),
        ]
        for old, new in cases:
            with self.subTest(old=old, new=new):
                self.assertReconstructs(old, new, diff_lines(old, new))


if __name__ == "__main__":
    unittest.main()
