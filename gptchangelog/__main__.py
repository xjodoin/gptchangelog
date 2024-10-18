"""The main entry point. Invoke as `gptchangelog' or `python -m gptchangelog'.

"""


def main():
    try:
        from gptchangelog.cli import app
        exit_status = app()
    except KeyboardInterrupt:
        from gptchangelog.status import ExitStatus
        exit_status = ExitStatus.ERROR_CTRL_C

    return exit_status.value


if __name__ == '__main__':  # pragma: nocover
    import sys
    sys.exit(main())