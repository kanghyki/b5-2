"""mini-git의 엔트리 포인트. 인자가 없으면 REPL, 있으면 CLI로 동작한다."""

import sys

from minigit.cli import run_cli
from minigit.repl import Repl


def main(argv: list[str] | None = None) -> int:
    """인자가 없으면 REPL을 실행하고, 있으면 명령 하나를 실행해 종료 코드를 돌려준다."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        Repl().run()
        return 0
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
