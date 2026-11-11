"""브랜치, HEAD, 커밋 그래프, 색인을 묶어 관리하는 저장소."""

from collections.abc import Callable
from datetime import datetime

from minigit.graph import Commit, CommitGraph
from minigit.index import InvertedIndex, contains_phrase, tokenize
from minigit.sorting import merge_sort
from minigit.traversal import find_ancestors, shortest_path, topological_order

DEFAULT_BRANCH = "main"

SORT_KEYS: dict[str, Callable[[Commit], object]] = {
    "date": lambda commit: commit.timestamp,
    "author": lambda commit: commit.author.lower(),
}


class MiniGitError(Exception):
    """사용자에게 그대로 보여 줄 수 있는 오류."""


class HashGenerator:
    """세션 내에서 중복되지 않는 7자리 16진수 해시를 만든다.

    홀수를 곱하는 연산은 2^28로 나눈 나머지 위에서 일대일 대응이다. 따라서 서로 다른
    카운터 값은 항상 서로 다른 해시가 되어, 충돌 검사 없이도 유일성이 보장된다.
    """

    _BITS = 28
    _MULTIPLIER = 0x9E3779B1

    def __init__(self) -> None:
        self._counter = 0

    def next(self) -> str:
        """다음 해시를 돌려준다. 해시 공간을 모두 쓰면 오류를 던진다."""
        self._counter += 1
        if self._counter >= 1 << self._BITS:
            raise MiniGitError("Commit hash space exhausted")
        value = (self._counter * self._MULTIPLIER) & ((1 << self._BITS) - 1)
        return format(value, "07x")


class Repository:
    """메모리에서 동작하는 저장소. 브랜치는 최신 커밋 해시를 가리키는 이름표다."""

    def __init__(self, clock: Callable[[], datetime] = datetime.now) -> None:
        self._clock = clock
        self._hashes = HashGenerator()
        self._graph = CommitGraph()
        self._branches: dict[str, str | None] = {}
        self._keyword_index = InvertedIndex()
        self._author_index = InvertedIndex()
        self._current_branch: str | None = None
        self._user: str | None = None

    @property
    def current_branch(self) -> str | None:
        """HEAD가 가리키는 브랜치 이름."""
        return self._current_branch

    @property
    def current_user(self) -> str | None:
        """새 커밋의 작성자로 기록될 사용자."""
        return self._user

    def init(self, user: str) -> bool:
        """저장소를 초기화하고, 처음 초기화했으면 True를 돌려준다.

        이미 초기화된 저장소에서는 이력을 유지한 채 현재 사용자만 바꾼다.
        """
        self._user = user
        if self._current_branch is not None:
            return False
        self._branches[DEFAULT_BRANCH] = None
        self._current_branch = DEFAULT_BRANCH
        return True

    def create_branch(self, name: str) -> None:
        """HEAD와 같은 커밋을 가리키는 브랜치를 만든다.

        커밋이 없는 브랜치에서 만들면 새 브랜치도 비어 있고, 그 브랜치의 첫 커밋은
        부모가 없는 별도의 뿌리 커밋이 된다.
        """
        self._require_initialized()
        if name in self._branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self._branches[name] = self._branches[self._current_branch]

    def switch(self, name: str) -> None:
        """HEAD를 지정한 브랜치로 옮긴다."""
        self._require_initialized()
        if name not in self._branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self._current_branch = name

    def commit(self, message: str) -> Commit:
        """HEAD를 부모로 하는 커밋을 만들고 브랜치와 색인을 갱신한다."""
        self._require_initialized()
        head = self._branches[self._current_branch]
        commit = Commit(
            hash=self._hashes.next(),
            message=message,
            author=self._user,
            timestamp=self._clock(),
            parents=() if head is None else (head,),
            branch=self._current_branch,
        )
        self._graph.add(commit)
        self._branches[self._current_branch] = commit.hash
        self._author_index.add(commit.author, commit.hash)
        for token in tokenize(commit.message):
            self._keyword_index.add(token, commit.hash)
        return commit

    def log(self) -> list[Commit]:
        """모든 브랜치의 커밋을 부모가 먼저 오는 순서로 돌려준다."""
        self._require_initialized()
        return self._commits(topological_order(self._graph))

    def log_sorted_by(self, criterion: str) -> list[Commit]:
        """date 또는 author 오름차순으로 돌려준다. 같은 값은 생성 순서를 유지한다."""
        self._require_initialized()
        return merge_sort(self._commits(self._graph), key=SORT_KEYS[criterion])

    def path(self, start: str, goal: str) -> list[str] | None:
        """두 커밋 사이의 최단 경로를 돌려주고, 없으면 None을 돌려준다."""
        self._require_initialized()
        self._require_commit(start)
        self._require_commit(goal)
        return shortest_path(self._graph, start, goal)

    def ancestors(self, commit_hash: str) -> list[Commit]:
        """커밋에서 도달할 수 있는 모든 조상을 돌려준다."""
        self._require_initialized()
        self._require_commit(commit_hash)
        return self._commits(find_ancestors(self._graph, commit_hash))

    def search_keyword(self, keyword: str) -> list[Commit]:
        """키워드가 메시지에 들어 있는 커밋을 생성 순서대로 돌려준다.

        공백이 포함된 키워드는 토큰이 연속으로 나타나는 커밋만 찾는다. 후보는 색인에서
        얻으므로, 문구 확인도 전체 커밋이 아닌 후보에 대해서만 수행한다.
        """
        self._require_initialized()
        tokens = tokenize(keyword)
        matches = self._commits(self._keyword_index.lookup_all(tokens))
        return [commit for commit in matches if contains_phrase(commit.message, tokens)]

    def search_author(self, author: str) -> list[Commit]:
        """이름이 정확히 일치하는 작성자의 커밋을 생성 순서대로 돌려준다."""
        self._require_initialized()
        return self._commits(self._author_index.lookup(author))

    def _commits(self, hashes) -> list[Commit]:
        """해시 목록을 커밋 목록으로 바꾼다."""
        return [self._graph.get(commit_hash) for commit_hash in hashes]

    def _require_initialized(self) -> None:
        if self._current_branch is None:
            raise MiniGitError("Repository not initialized")

    def _require_commit(self, commit_hash: str) -> None:
        if commit_hash not in self._graph:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
