import unittest

from minigit.index import InvertedIndex, contains_phrase, tokenize


class TokenizeTest(unittest.TestCase):
    def test_splits_on_whitespace_and_lowercases(self):
        self.assertEqual(tokenize("  Add  LOGIN\tFeature "), ["add", "login", "feature"])

    def test_blank_text_has_no_tokens(self):
        self.assertEqual(tokenize("   "), [])


class ContainsPhraseTest(unittest.TestCase):
    def test_matches_consecutive_tokens_only(self):
        self.assertTrue(contains_phrase("Add  Login feature", ["add", "login"]))
        self.assertFalse(contains_phrase("login then add", ["add", "login"]))
        self.assertFalse(contains_phrase("add new login", ["add", "login"]))

    def test_does_not_match_part_of_token(self):
        self.assertFalse(contains_phrase("relogin now", ["login"]))


class InvertedIndexTest(unittest.TestCase):
    def setUp(self):
        self.index = InvertedIndex()
        self.index.add("login", "h1")
        self.index.add("login", "h2")
        self.index.add("add", "h2")
        self.index.add("add", "h3")

    def test_lookup_keeps_insertion_order(self):
        self.assertEqual(self.index.lookup("login"), ["h1", "h2"])

    def test_unknown_term_is_empty(self):
        self.assertEqual(self.index.lookup("missing"), [])
        self.assertEqual(self.index.lookup_all(["login", "missing"]), [])

    def test_repeated_term_in_same_commit_is_recorded_once(self):
        self.index.add("login", "h2")
        self.assertEqual(self.index.lookup("login"), ["h1", "h2"])

    def test_lookup_all_intersects_terms(self):
        self.assertEqual(self.index.lookup_all(["login", "add"]), ["h2"])

    def test_lookup_result_does_not_expose_internal_state(self):
        self.index.lookup("login").append("other")
        self.assertEqual(self.index.lookup("login"), ["h1", "h2"])


if __name__ == "__main__":
    unittest.main()
