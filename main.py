"""mini-git REPL의 엔트리 포인트."""

from minigit.cli import MiniGitCli


def main() -> None:
    """REPL을 실행한다."""
    MiniGitCli().run()


if __name__ == "__main__":
    main()
