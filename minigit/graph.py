"""커밋 노드와 커밋 그래프(DAG) 자료구조."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Commit:
    """변경 불가능한 커밋 노드. branch는 커밋이 생성된 브랜치로, 표시에만 쓴다."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple[str, ...] = ()
    branch: str = ""


class CommitGraph:
    """해시로 커밋을 O(1)에 찾고, 부모/자식 간선을 함께 관리하는 그래프.

    새 커밋은 이미 존재하는 커밋만 부모로 삼을 수 있다. 간선이 항상 나중 노드에서
    먼저 추가된 노드로만 향하므로 순환이 생길 수 없고, 그래프는 DAG로 유지된다.
    """

    def __init__(self) -> None:
        self._commits: dict[str, Commit] = {}
        self._children: dict[str, list[str]] = {}

    def add(self, commit: Commit) -> None:
        """커밋을 추가한다. 해시가 중복되거나 부모가 없으면 ValueError를 던진다."""
        if commit.hash in self._commits:
            raise ValueError(f"Duplicate commit hash: {commit.hash}")
        for parent in commit.parents:
            if parent not in self._commits:
                raise ValueError(f"Unknown parent: {parent}")
        self._commits[commit.hash] = commit
        self._children[commit.hash] = []
        for parent in commit.parents:
            self._children[parent].append(commit.hash)

    def get(self, commit_hash: str) -> Commit | None:
        """해시에 해당하는 커밋을 돌려주고, 없으면 None을 돌려준다."""
        return self._commits.get(commit_hash)

    def parents(self, commit_hash: str) -> tuple[str, ...]:
        """부모 커밋 해시 목록을 돌려준다."""
        return self._commits[commit_hash].parents

    def children(self, commit_hash: str) -> list[str]:
        """자식 커밋 해시 목록을 생성 순서대로 돌려준다."""
        return self._children[commit_hash]

    def neighbors(self, commit_hash: str) -> list[str]:
        """간선을 무방향으로 볼 때 인접한 커밋 해시 목록을 돌려준다."""
        return [*self.parents(commit_hash), *self.children(commit_hash)]

    def __contains__(self, commit_hash: str) -> bool:
        return commit_hash in self._commits

    def __iter__(self) -> Iterator[str]:
        """커밋 해시를 생성 순서대로 순회한다."""
        return iter(self._commits)

    def __len__(self) -> int:
        return len(self._commits)
