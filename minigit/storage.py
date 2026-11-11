"""저장소 상태를 .minigit 디렉터리의 JSON 파일로 저장하고 불러온다."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from minigit.graph import Commit
from minigit.repository import MiniGitError, Repository, RepositoryState

REPOSITORY_DIR = ".minigit"
STATE_FILE = "state.json"
FORMAT_VERSION = 1


def find_root(start: Path) -> Path | None:
    """start부터 상위 디렉터리로 올라가며 .minigit이 있는 디렉터리를 찾는다."""
    for directory in (start, *start.parents):
        if (directory / REPOSITORY_DIR).is_dir():
            return directory
    return None


def state_path(root: Path) -> Path:
    """root 저장소의 상태 파일 경로."""
    return root / REPOSITORY_DIR / STATE_FILE


def load(root: Path) -> Repository:
    """root의 상태 파일로 저장소를 다시 만든다.

    파일을 읽을 수 없거나 내용이 맞지 않으면 MiniGitError를 던진다.
    """
    path = state_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Repository.from_state(decode(data))
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
        raise MiniGitError(f"Corrupted repository: {path}") from error


def save(repository: Repository, root: Path) -> None:
    """저장소 상태를 root/.minigit/state.json에 쓴다. 쓸 수 없으면 MiniGitError를 던진다.

    같은 디렉터리의 임시 파일에 다 쓴 뒤 이름을 바꾸므로, 쓰는 도중에 멈춰도 기존 파일은
    온전히 남는다.
    """
    directory = root / REPOSITORY_DIR
    content = json.dumps(encode(repository.state()), ensure_ascii=False, indent=2)
    try:
        directory.mkdir(exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".state-", suffix=".tmp")
    except OSError as error:
        raise MiniGitError(f"Cannot write repository: {directory}") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content + "\n")
        os.replace(temporary, state_path(root))
    except BaseException as error:
        Path(temporary).unlink(missing_ok=True)
        if isinstance(error, OSError):
            raise MiniGitError(f"Cannot write repository: {directory}") from error
        raise


def encode(state: RepositoryState) -> dict:
    """상태를 JSON으로 바꿀 수 있는 dict로 만든다. 커밋은 생성 순서를 유지한다."""
    return {
        "version": FORMAT_VERSION,
        "user": state.user,
        "current_branch": state.current_branch,
        "branches": state.branches,
        "hash_counter": state.hash_counter,
        "commits": [
            {
                "hash": commit.hash,
                "message": commit.message,
                "author": commit.author,
                "timestamp": commit.timestamp.isoformat(),
                "parents": list(commit.parents),
                "branch": commit.branch,
            }
            for commit in state.commits
        ],
    }


def decode(data: dict) -> RepositoryState:
    """encode()가 만든 dict를 상태로 되돌린다. 형식이 다르면 ValueError를 던진다."""
    if data["version"] != FORMAT_VERSION:
        raise ValueError(f"Unsupported format version: {data['version']}")
    branches = data["branches"]
    if not isinstance(branches, dict):
        raise ValueError("branches must be an object")
    commits = tuple(
        Commit(
            hash=_text(item["hash"]),
            message=_text(item["message"]),
            author=_text(item["author"]),
            timestamp=datetime.fromisoformat(item["timestamp"]),
            parents=tuple(_text(parent) for parent in item["parents"]),
            branch=_text(item["branch"]),
        )
        for item in data["commits"]
    )
    counter = data["hash_counter"]
    if not isinstance(counter, int) or isinstance(counter, bool):
        raise ValueError("hash_counter must be an integer")
    return RepositoryState(
        user=_optional_text(data["user"]),
        current_branch=_optional_text(data["current_branch"]),
        branches={_text(name): _optional_text(head) for name, head in branches.items()},
        commits=commits,
        hash_counter=counter,
    )


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Expected a string: {value!r}")
    return value


def _optional_text(value: object) -> str | None:
    return None if value is None else _text(value)
