import random
import unittest

from minigit.sorting import merge_sort


class MergeSortTest(unittest.TestCase):
    def assert_ascending(self, values):
        for previous, current in zip(values, values[1:]):
            self.assertLessEqual(previous, current)

    def test_small_inputs(self):
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(merge_sort([1]), [1])
        self.assertEqual(merge_sort([2, 1]), [1, 2])

    def test_random_inputs_keep_every_element(self):
        rng = random.Random(3)
        for _ in range(200):
            values = [rng.randint(-20, 20) for _ in range(rng.randint(0, 60))]
            result = merge_sort(values)
            self.assert_ascending(result)
            self.assertEqual(len(result), len(values))
            for value in values:
                self.assertEqual(result.count(value), values.count(value))

    def test_does_not_modify_input(self):
        values = [3, 1, 2]
        merge_sort(values)
        self.assertEqual(values, [3, 1, 2])

    def test_key_changes_sort_criteria(self):
        words = ["ccc", "a", "bb"]
        self.assertEqual(merge_sort(words, key=len), ["a", "bb", "ccc"])
        self.assertEqual(merge_sort(words, key=lambda word: -len(word)), ["ccc", "bb", "a"])

    def test_is_stable(self):
        rows = [(rank, order) for order, rank in enumerate([2, 1, 2, 1, 3, 1, 2])]
        result = merge_sort(rows, key=lambda row: row[0])
        for previous, current in zip(result, result[1:]):
            if previous[0] == current[0]:
                self.assertLess(previous[1], current[1])


if __name__ == "__main__":
    unittest.main()
