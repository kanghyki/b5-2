"""mini-git REPL의 엔트리 포인트."""

from minigit.repl import Repl


def main() -> None:
    """REPL을 실행한다."""
    Repl().run()


if __name__ == "__main__":
    main()
