"""한 줄씩 입력받아 명령을 반복 실행하는 REPL 인터페이스."""

import shlex

from minigit.commands import INVALID_ARGS, CommandRunner
from minigit.repository import MiniGitError

PROMPT = "mini-git> "
EXIT_COMMANDS = ("exit", "quit")


class Repl:
    """mini-git> 프롬프트에서 받은 줄을 명령으로 실행한다. 저장소는 메모리에만 있다."""

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = CommandRunner() if runner is None else runner

    def execute(self, line: str) -> str:
        """명령 한 줄을 실행해 출력할 문자열을 돌려준다. 빈 줄이면 빈 문자열이다.

        공백이 있는 인자는 따옴표로 감싸고, 오류는 메시지 문자열로 돌려준다.
        """
        try:
            tokens = shlex.split(line)
        except ValueError:
            return INVALID_ARGS
        if not tokens:
            return ""
        try:
            return self._runner.run(tokens)
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
