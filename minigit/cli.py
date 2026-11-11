"""셸에서 명령 하나를 실행하고 끝나는 CLI 인터페이스."""

import sys
from pathlib import Path
from typing import TextIO

from minigit import storage
from minigit.commands import CommandRunner
from minigit.repository import MiniGitError, Repository

STATE_CHANGING_COMMANDS = ("init", "branch", "switch", "commit")
REPOSITORY_FREE_COMMANDS = ("diff",)


def run_cli(
    argv: list[str],
    cwd: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """[명령 이름, 인자...]를 실행하고 종료 코드를 돌려준다(성공 0, 실패 1).

    실행할 때마다 프로세스가 새로 뜨므로, cwd에서 상위로 올라가며 찾은 .minigit에서
    저장소를 불러오고 상태를 바꾸는 명령이 성공하면 다시 저장한다. 저장소가 없을 때
    INIT은 cwd에 새로 만든다. 인자는 셸이 이미 나눴으므로 다시 나누지 않는다.
    결과는 stdout에, 오류는 stderr에 출력한다.
    """
    cwd = Path.cwd() if cwd is None else cwd
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    name = argv[0].lower()
    try:
        root = None if name in REPOSITORY_FREE_COMMANDS else storage.find_root(cwd)
        repository = Repository() if root is None else storage.load(root)
        output = CommandRunner(repository).run(argv)
        if name in STATE_CHANGING_COMMANDS:
            storage.save(repository, cwd if root is None else root)
    except MiniGitError as error:
        print(error, file=stderr)
        return 1
    if output:
        print(output, file=stdout)
    return 0
