# Mini Git

Git의 커밋 구조를 메모리에서 재현한 CLI 프로그램입니다. 브랜치를 만들어 커밋을 쌓고, 커밋 그래프를 탐색하고, 메시지와 작성자로 커밋을 검색할 수 있습니다. 파일 내용은 추적하지 않고 커밋 메타데이터만 다루며, 프로그램을 종료하면 데이터는 사라집니다.

## 실행

Python 3.10 이상이 필요하고, 별도로 설치할 패키지는 없습니다.

```bash
python main.py                # 환경에 따라 python3 main.py
python -m unittest            # 테스트
```

## 명령어

명령어 이름은 대소문자를 구분하지 않습니다. 공백이 있는 문자열은 따옴표로 감쌉니다.

| 명령어 | 동작 |
| --- | --- |
| `INIT <user_name>` | 저장소를 초기화하고 `main` 브랜치와 사용자를 설정 |
| `BRANCH <branch_name>` | 현재 커밋을 가리키는 브랜치 생성 |
| `SWITCH <branch_name>` | HEAD를 지정한 브랜치로 이동 |
| `COMMIT <message>` | 현재 HEAD를 부모로 하는 커밋 생성 |
| `LOG` | 모든 커밋을 부모가 먼저 오는 순서로 출력 |
| `LOG --sort-by=date\|author` | 시각 또는 작성자 오름차순으로 출력 |
| `PATH <commit1> <commit2>` | 두 커밋 사이의 최단 경로 출력, 없으면 `No path` |
| `ANCESTORS <commit_hash>` | 커밋의 모든 조상 출력 |
| `SEARCH <keyword>` | 키워드가 메시지에 들어 있는 커밋 출력 |
| `SEARCH --author=<name>` | 해당 작성자의 커밋 출력 |
| `exit`, `quit` | 프로그램 종료 |

오류는 `Invalid args`, `Unknown branch: <name>`, `Unknown commit: <hash>`, `Branch already exists: <name>`, `Unknown command: <name>`, `Repository not initialized`로 출력합니다.

```text
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice
mini-git> commit "Initial commit"
[main e3779b1] Initial commit
mini-git> branch feature
Created branch: feature
mini-git> switch feature
Switched to branch: feature
mini-git> commit "Add login feature"
[feature c6ef362] Add login feature
mini-git> path e3779b1 c6ef362
Path: e3779b1 -> c6ef362
mini-git> search "login"
Found 1 commit:
- c6ef362: Add login feature
```

## 동작 규칙

- **INIT 재실행:** 이력과 현재 브랜치를 유지한 채 사용자만 바꿉니다. 사용자를 바꾸는 유일한 방법이므로, 작성자가 여러 명인 이력은 이 방식으로 만듭니다.
- **커밋이 없을 때의 BRANCH:** 빈 브랜치를 만듭니다. 그 브랜치의 첫 커밋은 부모가 없는 별도의 뿌리 커밋이 되고, 이렇게 연결되지 않은 커밋 사이에서 `PATH`는 `No path`를 출력합니다.
- **LOG 범위:** 현재 브랜치뿐 아니라 저장소의 모든 커밋을 출력합니다. 대괄호 안의 이름은 커밋이 만들어진 브랜치입니다.
- **정렬:** 오름차순입니다. 작성자는 대소문자 구분 없이 비교하고, 같은 값은 생성 순서를 유지합니다.
- **키워드 검색:** 공백으로 나눈 토큰 단위로 대소문자 구분 없이 일치시킵니다. `login`은 `relogin`이나 `login,`과 일치하지 않습니다. 공백이 있는 키워드는 토큰이 메시지에 연속으로 나타나는 커밋을 찾습니다.
- **작성자 검색:** 이름이 대소문자까지 정확히 같아야 합니다.

## 구조

```text
main.py               엔트리 포인트
minigit/graph.py      커밋 노드와 커밋 그래프
minigit/traversal.py  위상 정렬, 조상 탐색, 최단 경로
minigit/sorting.py    병합 정렬
minigit/index.py      역색인
minigit/repository.py 브랜치, HEAD, 커밋 생성, 검색
minigit/cli.py        명령 파싱과 REPL
tests/                단위 테스트와 REPL 테스트
```

## 설계

아래에서 V는 커밋 수, E는 부모-자식 간선 수입니다.

### 커밋 그래프가 DAG인 이유

커밋은 부모를 가리키고, 한 번 만들어지면 바뀌지 않습니다. 부모는 항상 이미 존재하는 커밋이므로 간선은 나중 커밋에서 먼저 만들어진 커밋으로만 향합니다. 따라서 어떤 커밋도 자기 자신으로 돌아올 수 없어 순환이 생기지 않습니다. 또한 브랜치가 갈라지면 한 부모에 자식이 여럿 생기고, 병합 커밋은 부모를 둘 이상 가질 수 있으므로 단순한 리스트나 트리가 아닌 그래프로 표현합니다.

`CommitGraph`는 해시맵으로 커밋을 O(1)에 찾고, `add`에서 존재하지 않는 부모를 거부해 이 성질을 유지합니다. 해시는 카운터 값에 홀수를 곱해 2^28로 나눈 나머지입니다. 이 연산은 일대일 대응이므로 2^28 - 1개까지 충돌 없이 만들 수 있고, 그 이후에는 오류로 처리합니다.

### 부모가 먼저 나오는 로그

부모마다 자식이 여럿일 수 있어 단순히 최신순으로 나열하는 방식으로는 그래프의 선후 관계를 표현할 수 없습니다. 그래서 위상 정렬인 Kahn 알고리즘을 사용합니다. 커밋마다 아직 출력되지 않은 부모 수를 세고, 0이 된 커밋을 큐에서 꺼내 출력한 뒤 자식의 수를 1씩 줄입니다. 커밋은 모든 부모가 출력된 뒤에야 큐에 들어가므로 부모가 항상 먼저 나옵니다. 시간복잡도는 O(V+E)입니다.

### 최단 경로와 조상 탐색

간선 가중치가 모두 같으므로 BFS가 간선 수 기준 최단 거리를 보장합니다.

- **PATH:** 간선을 무방향으로 보고 목적지에서 BFS로 거리를 구합니다. 그다음 출발지에서 시작해 거리가 1 줄어드는 이웃 중 해시가 가장 작은 쪽을 고릅니다. 앞자리부터 가장 작은 값을 고르므로 최단 경로 중 사전순으로 가장 앞선 경로가 됩니다. 시간복잡도는 O(V+E)입니다.
- **ANCESTORS:** 부모 간선만 따라 BFS로 탐색합니다. 방문 집합이 있어 여러 경로로 닿는 조상도 한 번만 출력합니다. 시간복잡도는 O(V+E)입니다.

### 병합 정렬

| 평균 시간 | 최악 시간 | 추가 공간 | 안정 정렬 |
| --- | --- | --- | --- |
| O(n log n) | O(n log n) | O(n) | 예 |

입력 상태와 상관없이 최악에도 O(n log n)을 보장하고, 같은 값의 순서를 유지하므로 동률인 커밋을 생성 순서대로 보여 줄 수 있습니다. `key` 함수만 바꾸면 비교 기준을 바꿀 수 있어 날짜와 작성자 정렬이 같은 코드를 사용합니다.

### 역색인

모든 커밋을 순회하는 검색은 메시지를 전부 확인해야 하므로 커밋 수에 비례합니다. 역색인은 커밋을 만들 때 메시지 토큰과 작성자를 키로 해시 목록을 미리 저장합니다.

| 방식 | 단일 키워드 검색 | 비고 |
| --- | --- | --- |
| 전체 순회 | O(V × L) | L은 메시지 평균 길이 |
| 역색인 | O(K) | K는 일치하는 커밋 수 |

검색 비용을 커밋 수가 아닌 결과 수에 비례하게 만드는 대신, 커밋을 만들 때 토큰 수만큼의 색인 갱신 비용과 추가 메모리를 사용합니다. 공백이 있는 키워드는 각 토큰의 해시 목록을 교집합으로 좁힌 뒤, 남은 후보에서만 토큰이 연속으로 나타나는지 확인합니다.
