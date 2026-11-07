"""커밋 그래프 탐색 알고리즘. V는 커밋 수, E는 부모-자식 간선 수를 뜻한다."""

from collections import deque

from minigit.graph import CommitGraph


def topological_order(graph: CommitGraph) -> list[str]:
    """부모가 항상 자식보다 먼저 나오는 해시 목록을 돌려준다(Kahn 알고리즘, O(V+E)).

    아직 출력되지 않은 부모 수를 세고, 그 수가 0이 된 커밋부터 꺼낸다. 큐를 쓰므로
    출력 준비가 먼저 끝난 커밋이 먼저 나온다.
    """
    pending_parents = {commit: len(graph.parents(commit)) for commit in graph}
    ready = deque(commit for commit, count in pending_parents.items() if count == 0)
    order = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for child in graph.children(current):
            pending_parents[child] -= 1
            if pending_parents[child] == 0:
                ready.append(child)
    return order


def find_ancestors(graph: CommitGraph, commit_hash: str) -> list[str]:
    """시작 커밋을 제외한 모든 조상을 가까운 순서로 돌려준다(BFS, O(V+E)).

    방문 집합이 있어 여러 경로로 닿는 조상도 한 번만 포함된다.
    """
    visited = {commit_hash}
    queue = deque([commit_hash])
    ancestors = []
    while queue:
        for parent in graph.parents(queue.popleft()):
            if parent not in visited:
                visited.add(parent)
                ancestors.append(parent)
                queue.append(parent)
    return ancestors


def _distances_from(graph: CommitGraph, source: str) -> dict[str, int]:
    """간선을 무방향으로 보고 source에서 닿는 커밋까지의 거리를 BFS로 구한다."""
    distances = {source: 0}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        for neighbor in graph.neighbors(current):
            if neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    return distances


def shortest_path(graph: CommitGraph, start: str, goal: str) -> list[str] | None:
    """간선 수가 최소인 경로 중 사전순으로 가장 앞선 경로를 돌려준다(O(V+E)).

    goal 기준 거리를 먼저 구하면, 각 위치에서 거리가 1 줄어드는 이웃만 최단 경로에
    속한다. 그중 해시가 가장 작은 이웃을 고르면 사전순 최소 경로가 된다. 해시 문자가
    구분자 "->"의 "-"보다 뒤에 오는 영숫자이므로 문자열로 이어 붙여 비교해도 같다.
    경로가 없으면 None을 돌려준다.
    """
    distances = _distances_from(graph, goal)
    if start not in distances:
        return None
    path = [start]
    current = start
    while current != goal:
        closer = distances[current] - 1
        current = min(n for n in graph.neighbors(current) if distances[n] == closer)
        path.append(current)
    return path
