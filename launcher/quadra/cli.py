"""Quadra Lite launcher command line."""

import sys


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    from quadra import paths

    paths.migrate_environment()

    # Linux has no LaunchServices. Keep the browser's Roblox argument opaque and
    # let the normal launcher process consume it once Darling is ready. Writing it
    # before starting GTK also covers a second protocol click while the first
    # launch is still preparing the prefix. Desktop entries pass the URI directly;
    # retain --uri as a compatibility spelling for older local entries.
    if len(argv) == 1 and not argv[0].startswith("-"):
        from quadra import uri

        uri.receive(argv[0])

    if argv[:1] == ["--uri"]:
        if len(argv) != 2:
            print("quadralite --uri requires one URI", file=sys.stderr)
            return 2
        from quadra import uri

        uri.receive(argv[1])

    # `quadralite --collect-diagnostics [options]` writes a report archive without
    # the interface (see `quadralite --collect-diagnostics --help`).
    if argv[:1] == ["--collect-diagnostics"]:
        try:
            from quadra import diagnostics
        except ImportError as error:
            print(
                f"Diagnostics are unavailable in this Quadra build: {error}",
                file=sys.stderr,
            )
            return 1
        return diagnostics.collect_cli(argv[1:])

    # `quadralite --watch-stalls` records what the game's threads do while it hangs
    # (see `quadralite --watch-stalls --help`); start it before or during the game.
    if argv[:1] == ["--watch-stalls"]:
        from quadra.darling import stallwatch

        return stallwatch.cli(argv[1:])

    if argv[:1] == ["--hardware-report"]:
        from quadra import hardware_report

        return hardware_report.cli(argv[1:])

    # `quadralite --ciderdarling-settings` opens Settings -> CiderDarling, also in an
    # already running launcher (the CiderDarling Settings menu entry).
    page = None
    if argv[:1] == ["--ciderdarling-settings"]:
        page = "ciderdarling"

    # `quadralite --settings` opens the settings window (also in a running Quadra);
    # plain `quadralite` starts Roblox straight away behind a small splash.
    open_settings = argv[:1] == ["--settings"]

    from quadra.ui import main as ui_main

    return ui_main(page, open_settings)
