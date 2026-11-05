#!/usr/bin/env bash
# Quadra Lite uninstaller: removes the launcher installed by install.sh.
# Delegates to install.sh --uninstall; pass --yes to skip the prompt and
# --purge to also delete the selected Darling prefix and Rosemary files.
set -euo pipefail
cd "$(dirname "$0")"
exec ./install.sh --uninstall "$@"
