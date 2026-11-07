"""테스트에서 공유하는 그래프 생성 도구."""

from datetime import datetime

from minigit.graph import Commit, CommitGraph


def make_commit(commit_hash, parents=(), author="Alice", message="msg", timestamp=None):
    """테스트에 필요한 필드만 지정해 커밋을 만든다."""
    return Commit(
        hash=commit_hash,
        message=message,
        author=author,
        timestamp=timestamp or datetime(2024, 1, 1),
        parents=tuple(parents),
    )


def make_graph(edges):
    """(해시, 부모 목록) 쌍을 순서대로 추가한 그래프를 만든다."""
    graph = CommitGraph()
    for commit_hash, parents in edges:
        graph.add(make_commit(commit_hash, parents))
    return graph
