"""The main entry point. Invoke as `gptchangelog' or `python -m gptchangelog'."""


def main():
    from gptchangelog.cli import app

    return app()


if __name__ == "__main__":  # pragma: nocover
    import sys

    sys.exit(main())
