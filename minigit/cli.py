"""명령 파싱, 실행, 출력을 반복하는 REPL 인터페이스."""

import shlex

from minigit.graph import Commit
from minigit.repository import SORT_KEYS, MiniGitError, Repository

PROMPT = "mini-git> "
INVALID_ARGS = "Invalid args"
EXIT_COMMANDS = ("exit", "quit")


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


class MiniGitCli:
    """입력 한 줄을 저장소 호출로 바꾸고 결과를 문자열로 돌려준다."""

    def __init__(self, repository: Repository | None = None) -> None:
        self._repo = repository or Repository()
        self._handlers = {
            "init": self._init,
            "branch": self._branch,
            "switch": self._switch,
            "commit": self._commit,
            "log": self._log,
            "path": self._path,
            "ancestors": self._ancestors,
            "search": self._search,
        }

    def execute(self, line: str) -> str:
        """명령 한 줄을 실행해 출력할 문자열을 돌려준다. 빈 줄이면 빈 문자열이다."""
        try:
            tokens = shlex.split(line)
        except ValueError:
            return INVALID_ARGS
        if not tokens:
            return ""
        name, args = tokens[0], tokens[1:]
        handler = self._handlers.get(name.lower())
        if handler is None:
            return f"Unknown command: {name}"
        try:
            return handler(args)
        except MiniGitError as error:
            return str(error)

    def run(self) -> None:
        """exit, quit, EOF, Ctrl-C 중 하나가 들어올 때까지 명령을 처리한다."""
        while True:
            try:
                line = input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if line.strip().lower() in EXIT_COMMANDS:
                return
            output = self.execute(line)
            if output:
                print(output)

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
