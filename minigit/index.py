"""커밋 검색에 쓰는 역색인."""


def tokenize(text: str) -> list[str]:
    """공백으로 나누고 소문자로 정규화한 토큰 목록을 돌려준다."""
    return text.lower().split()


def contains_phrase(text: str, tokens: list[str]) -> bool:
    """text의 토큰 중에 tokens가 연속해서 나타나는지 확인한다."""
    wrapped_text = f" {' '.join(tokenize(text))} "
    return f" {' '.join(tokens)} " in wrapped_text


class InvertedIndex:
    """검색어에서 커밋 해시 목록으로 바로 이어지는 색인.

    전체 커밋을 순회하는 검색은 커밋 수 N에 비례해 O(N)이지만, 역색인은 해시맵 조회
    O(1)로 후보를 얻고 결과 수 K만큼만 복사하므로 O(K)이다.
    """

    def __init__(self) -> None:
        self._postings: dict[str, list[str]] = {}

    def add(self, term: str, commit_hash: str) -> None:
        """term에 해시를 추가한다. 같은 커밋이 연달아 들어오면 한 번만 기록한다."""
        postings = self._postings.setdefault(term, [])
        if not postings or postings[-1] != commit_hash:
            postings.append(commit_hash)

    def lookup(self, term: str) -> list[str]:
        """term이 가리키는 해시 목록을 추가된 순서대로 돌려준다."""
        return list(self._postings.get(term, []))

    def lookup_all(self, terms: list[str]) -> list[str]:
        """모든 term을 포함하는 해시만 첫 term의 순서대로 돌려준다."""
        matches = self.lookup(terms[0])
        for term in terms[1:]:
            allowed = set(self._postings.get(term, []))
            matches = [commit_hash for commit_hash in matches if commit_hash in allowed]
        return matches
