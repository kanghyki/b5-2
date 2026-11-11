"""두 텍스트를 줄 단위로 비교하는 LCS 기반 diff 알고리즘."""

from collections.abc import Sequence

COMMON = " "
DELETED = "-"
ADDED = "+"


def diff_lines(old: Sequence[str], new: Sequence[str]) -> list[tuple[str, str]]:
    """old를 new로 바꾸는 줄 목록을 (표시, 줄) 쌍으로 돌려준다.

    표시는 공통 줄이면 COMMON, old에만 있으면 DELETED, new에만 있으면 ADDED다. 공통 줄은
    최장 공통 부분 수열(LCS)로 정하므로 바뀐 줄 수가 가장 적은 결과가 된다. 같은 위치에서
    삭제와 추가가 모두 가능하면 삭제를 먼저 둔다.

    앞뒤로 같은 줄은 표를 만들기 전에 떼어 낸다. 남은 줄 수를 n, m이라 하면 시간과 추가
    공간은 O(n × m)이다.
    """
    prefix = 0
    while prefix < len(old) and prefix < len(new) and old[prefix] == new[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(old) - prefix
        and suffix < len(new) - prefix
        and old[len(old) - 1 - suffix] == new[len(new) - 1 - suffix]
    ):
        suffix += 1

    head = [(COMMON, line) for line in old[:prefix]]
    tail = [(COMMON, line) for line in old[len(old) - suffix :]]
    middle = _diff_by_lcs(old[prefix : len(old) - suffix], new[prefix : len(new) - suffix])
    return head + middle + tail


def _diff_by_lcs(old: Sequence[str], new: Sequence[str]) -> list[tuple[str, str]]:
    """LCS 길이 표를 채운 뒤 앞에서부터 따라가며 diff를 만든다.

    lcs[i][j]는 old[i:]와 new[j:]의 LCS 길이다. 뒤에서부터 채우면 앞에서부터 따라갈 때
    매 단계에서 남은 구간의 최적값을 바로 비교할 수 있다.
    """
    rows, cols = len(old), len(new)
    lcs = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows - 1, -1, -1):
        for j in range(cols - 1, -1, -1):
            if old[i] == new[j]:
                lcs[i][j] = lcs[i + 1][j + 1] + 1
            else:
                lcs[i][j] = max(lcs[i + 1][j], lcs[i][j + 1])

    result = []
    i = j = 0
    while i < rows and j < cols:
        if old[i] == new[j]:
            result.append((COMMON, old[i]))
            i += 1
            j += 1
        elif lcs[i + 1][j] >= lcs[i][j + 1]:
            result.append((DELETED, old[i]))
            i += 1
        else:
            result.append((ADDED, new[j]))
            j += 1
    result.extend((DELETED, line) for line in old[i:])
    result.extend((ADDED, line) for line in new[j:])
    return result
