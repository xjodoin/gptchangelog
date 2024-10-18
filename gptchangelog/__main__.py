"""The main entry point. Invoke as `gptchangelog' or `python -m gptchangelog'.

"""


def main():
    from gptchangelog.cli import app

    app()


if __name__ == '__main__':  # pragma: nocover
    main()
