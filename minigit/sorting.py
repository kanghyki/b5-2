"""비교 기준을 바꿀 수 있는 정렬 알고리즘."""

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

T = TypeVar("T")


def merge_sort(items: Sequence[T], key: Callable[[T], Any] = lambda item: item) -> list[T]:
    """key 값 오름차순으로 정렬한 새 리스트를 돌려준다.

    평균과 최악 모두 시간 O(n log n), 추가 공간 O(n)이다. 입력 순서와 상관없이 항상
    절반씩 나눠 병합하므로 최악에도 느려지지 않는다. 또한 안정 정렬이어서 key가 같은
    원소는 입력 순서를 유지한다.
    """
    if len(items) <= 1:
        return list(items)
    middle = len(items) // 2
    return _merge(merge_sort(items[:middle], key), merge_sort(items[middle:], key), key)


def _merge(left: list[T], right: list[T], key: Callable[[T], Any]) -> list[T]:
    """정렬된 두 리스트를 병합한다. key가 같으면 left를 먼저 택해 안정성을 지킨다."""
    merged = []
    left_index = right_index = 0
    while left_index < len(left) and right_index < len(right):
        if key(right[right_index]) < key(left[left_index]):
            merged.append(right[right_index])
            right_index += 1
        else:
            merged.append(left[left_index])
            left_index += 1
    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged
