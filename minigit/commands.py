"""REPL과 CLI가 함께 쓰는 명령 실행기와 출력 형식."""

from pathlib import Path

from minigit.diff import ADDED, DELETED, diff_lines
from minigit.graph import Commit
from minigit.repository import SORT_KEYS, MiniGitError, Repository

INVALID_ARGS = "Invalid args"


def parse_option(token: str) -> tuple[str, str] | None:
    """--name=value 형식이면 (소문자 이름, 값)을 돌려주고, 아니면 None을 돌려준다."""
    if not token.startswith("--") or "=" not in token:
        return None
    name, value = token[2:].split("=", 1)
    return name.lower(), value


def format_log(commits: list[Commit]) -> str:
    """커밋마다 해시, 작성자, 시각, 브랜치, 메시지를 보여 주는 로그를 만든다."""
    if not commits:
        return "No commits"
    lines = []
    for commit in commits:
        timestamp = commit.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"commit {commit.hash} ({commit.author}, {timestamp}) [{commit.branch}]")
        lines.append(f"    {commit.message}")
    return "\n".join(lines)


def format_found(commits: list[Commit], noun: str) -> str:
    """찾은 커밋의 개수와 "- 해시: 메시지" 목록을 만든다."""
    if not commits:
        return f"No {noun}s found"
    plural = "" if len(commits) == 1 else "s"
    lines = [f"Found {len(commits)} {noun}{plural}:"]
    lines.extend(f"- {commit.hash}: {commit.message}" for commit in commits)
    return "\n".join(lines)


def format_diff(old_name: str, new_name: str, entries: list[tuple[str, str]]) -> str:
    """파일 이름 머리글, 표시가 붙은 줄, 추가/삭제/공통 줄 수 요약을 만든다."""
    added = sum(1 for mark, _ in entries if mark == ADDED)
    deleted = sum(1 for mark, _ in entries if mark == DELETED)
    common = len(entries) - added - deleted
    lines = [f"--- {old_name}", f"+++ {new_name}"]
    lines.extend(f"{mark} {line}" for mark, line in entries)
    lines.append(f"{added} added, {deleted} deleted, {common} common")
    return "\n".join(lines)


def read_lines(path: str) -> list[str]:
    """UTF-8 텍스트 파일을 줄 목록으로 읽는다. 읽을 수 없으면 MiniGitError를 던진다."""
    try:
        return Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise MiniGitError(f"Cannot read file: {path}") from error


class CommandRunner:
    """이미 토큰으로 나뉜 명령을 저장소 호출로 바꾸고 결과를 문자열로 돌려준다.

    입력을 어떻게 받는지(REPL의 한 줄, 셸의 인자 목록)와 오류를 어디에 출력하는지는
    호출하는 쪽이 정한다. 실패는 모두 MiniGitError로 알린다.
    """

    def __init__(self, repository: Repository | None = None) -> None:
        self._repo = Repository() if repository is None else repository
        self._handlers = {
            "init": self._init,
            "branch": self._branch,
            "switch": self._switch,
            "commit": self._commit,
            "log": self._log,
            "path": self._path,
            "ancestors": self._ancestors,
            "search": self._search,
            "diff": self._diff,
        }

    def run(self, tokens: list[str]) -> str:
        """[명령 이름, 인자...]를 실행해 출력할 문자열을 돌려준다.

        명령 이름은 대소문자를 구분하지 않는다. 알 수 없는 명령이거나 실행에 실패하면
        MiniGitError를 던진다.
        """
        name, args = tokens[0], tokens[1:]
        handler = self._handlers.get(name.lower())
        if handler is None:
            raise MiniGitError(f"Unknown command: {name}")
        return handler(args)

    @staticmethod
    def _single_text(args: list[str]) -> str:
        """공백만이 아닌 문자열 인자 하나를 꺼낸다."""
        if len(args) != 1 or not args[0].strip():
            raise MiniGitError(INVALID_ARGS)
        return args[0]

    @staticmethod
    def _single_name(args: list[str]) -> str:
        """공백이 없는 이름 또는 해시 인자 하나를 꺼낸다."""
        if len(args) != 1 or not args[0] or len(args[0].split()) != 1:
            raise MiniGitError(INVALID_ARGS)
        return args[0]

    def _init(self, args: list[str]) -> str:
        user = self._single_text(args)
        created = self._repo.init(user)
        status = "Initialized repository." if created else "Reinitialized repository."
        return (
            f"{status}\n"
            f"Current branch: {self._repo.current_branch}\n"
            f"Current user: {self._repo.current_user}"
        )

    def _branch(self, args: list[str]) -> str:
        name = self._single_name(args)
        self._repo.create_branch(name)
        return f"Created branch: {name}"

    def _switch(self, args: list[str]) -> str:
        name = self._single_name(args)
        self._repo.switch(name)
        return f"Switched to branch: {name}"

    def _commit(self, args: list[str]) -> str:
        commit = self._repo.commit(self._single_text(args))
        return f"[{commit.branch} {commit.hash}] {commit.message}"

    def _log(self, args: list[str]) -> str:
        if not args:
            return format_log(self._repo.log())
        option = parse_option(args[0]) if len(args) == 1 else None
        if option is None or option[0] != "sort-by":
            raise MiniGitError(INVALID_ARGS)
        criterion = option[1].lower()
        if criterion not in SORT_KEYS:
            raise MiniGitError(INVALID_ARGS)
        return format_log(self._repo.log_sorted_by(criterion))

    def _path(self, args: list[str]) -> str:
        if len(args) != 2:
            raise MiniGitError(INVALID_ARGS)
        path = self._repo.path(args[0], args[1])
        return "No path" if path is None else "Path: " + " -> ".join(path)

    def _ancestors(self, args: list[str]) -> str:
        return format_found(self._repo.ancestors(self._single_name(args)), "ancestor")

    def _search(self, args: list[str]) -> str:
        text = self._single_text(args)
        if not text.startswith("--"):
            return format_found(self._repo.search_keyword(text), "commit")
        option = parse_option(text)
        if option is None or option[0] != "author" or not option[1].strip():
            raise MiniGitError(INVALID_ARGS)
        return format_found(self._repo.search_author(option[1]), "commit")

    def _diff(self, args: list[str]) -> str:
        if len(args) != 2 or not args[0] or not args[1]:
            raise MiniGitError(INVALID_ARGS)
        old_lines, new_lines = read_lines(args[0]), read_lines(args[1])
        return format_diff(args[0], args[1], diff_lines(old_lines, new_lines))
