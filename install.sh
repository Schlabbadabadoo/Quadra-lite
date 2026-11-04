#!/usr/bin/env bash
# Quadra Lite installer: downloads the launcher and adds it to the app menu.
# It installs nothing else: Quadra Lite's first-boot screen chooses the
# runtime that plays Roblox (Rosemary or Darling), and installs that runtime.
# The launcher needs only Python 3 with GTK 4 and libadwaita. Run it again to
# update, or to uninstall.
#
#   ./install.sh
#
# In a terminal it guides setup; without one it installs. The choices also
# work as options, see --help.
#
# Everything runs inside main(), called on the last line, so a download cut
# off halfway does nothing. The exit on that same line matters: main points
# stdin at the terminal (curl | bash), and bash would then read and run
# whatever is typed there as the rest of the script.

set -euo pipefail

REPO=https://github.com/Schlabbadabadoo/Quadra-Lite.git
DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
DIR=$DATA_HOME/QuadraLite
CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}
CACHE_HOME=${XDG_CACHE_HOME:-$HOME/.cache}

# Colours unless NO_COLOR is set or the output is no terminal; arrows and
# dots only where the locale is UTF-8.
if [[ -t 1 && -z ${NO_COLOR:-} && ${TERM:-dumb} != dumb ]]; then
  BOLD=$'\033[1m' DIM=$'\033[2m' RESET=$'\033[0m' ACCENT=$'\033[1;35m'
  GOOD=$'\033[1;32m' BAD=$'\033[1;31m' SELECTED=$'\033[1;97;45m'
  SHADES=($'\033[38;5;213m' $'\033[38;5;177m' $'\033[38;5;141m' $'\033[38;5;105m')
else
  BOLD='' DIM='' RESET='' ACCENT='' GOOD='' BAD='' SELECTED=''
  SHADES=('' '' '' '')
fi
case ${LC_ALL:-${LC_CTYPE:-${LANG:-}}} in
  *[Uu][Tt][Ff]-8* | *[Uu][Tt][Ff]8*)
    POINTER='❯' BULLET='•' ON='●' OFF='○' KEYS='↑/↓ move · enter choose · q quit' ;;
  *) POINTER='>' BULLET='-' ON='*' OFF='-' KEYS='up/down move, enter choose, q quit' ;;
esac

say() { printf '  %s%s%s %s\n' "$ACCENT" "$BULLET" "$RESET" "$*"; }
die() { printf '%sError:%s %s\n' "$BAD" "$RESET" "$*" >&2; exit 1; }


DARLING_RUNTIME=''
DARLING_EXECUTABLE=darling
PREFIX=${DPREFIX:-$HOME/.darling}

load_darling_selection() {
  local file=$CONFIG_HOME/quadralite/runtime.json saved
  [[ -f $file ]] && command -v python3 >/dev/null || return 0
  saved=$(python3 - "$file" <<'PY'
import json
import sys
try:
    data = json.load(open(sys.argv[1]))
    print('\n'.join(str(data[key]) for key in ('runtime', 'executable', 'prefix')))
except (OSError, ValueError, KeyError, TypeError):
    pass
PY
  ) || return 0
  [[ -n $saved ]] || return 0
  local selection
  mapfile -t selection <<< "$saved"
  DARLING_RUNTIME=${selection[0]}
  DARLING_EXECUTABLE=${selection[1]}
  [[ -n ${DPREFIX:-} ]] || PREFIX=${selection[2]}
}

darling_runtime_name() {
  if [[ $DARLING_RUNTIME == ciderdarling ]]; then
    printf '%s' "QuadraHQ's CiderDarling"
  else
    printf '%s' 'Regular Darling'
  fi
}

UPDATE_BACKUP=''

step() { printf '\n%s[%s/3] %s%s\n' "$BOLD" "$1" "$2" "$RESET"; }

distribution_name() {
  local PRETTY_NAME='' NAME=''
  [[ ! -r /etc/os-release ]] || . /etc/os-release
  printf '%s' "${PRETTY_NAME:-${NAME:-Linux}}"
}

setup_plan() {
  local operation='Install'
  is_installed && operation='Update'
  printf '  %sSetup plan%s\n\n' "$BOLD" "$RESET"
  printf '    1. Check for git, Python 3, GTK 4 and libadwaita.\n'
  printf '    2. %s the Quadra Lite launcher.\n' "$operation"
  printf '    3. Add the app menu entry and quadralite command.\n\n'
  printf '  Computer    %s (%s)\n' "$(distribution_name)" "$(uname -m)"
  printf '  Destination %s\n' "${DIR/#$HOME/\~}"
  printf '  %sNothing else is installed, and sudo is not used.%s\n' "$DIM" "$RESET"
  if is_installed; then
    printf '  %sUpdates keep settings, Roblox and existing backups.%s\n' "$DIM" "$RESET"
    printf '  %sLocal source changes are backed up before replacement.%s\n' "$DIM" "$RESET"
  else
    printf '  %sQuadra Lite'"'"'s first-boot screen picks your runtime, then installs it.%s\n' "$DIM" "$RESET"
  fi
}

# Keep recovery material outside the checkout. A reset can remove untracked
# files that obstruct incoming tracked paths; back those up too, and leave
# other untracked/ignored files in place instead of using git clean.
backup_checkout_changes() {
  local list_dir relative backup
  list_dir=$(mktemp -d)
  git -C "$DIR" diff --name-only -z HEAD > "$list_dir/tracked"
  git -C "$DIR" ls-files --others --exclude-standard -z > "$list_dir/untracked"
  if [[ ! -s $list_dir/tracked && ! -s $list_dir/untracked ]]; then
    rm -rf -- "$list_dir"
    return
  fi
  backup=$(umask 077; mkdir -p -- "$DATA_HOME/QuadraLite-backups";
    mktemp -d "$DATA_HOME/QuadraLite-backups/update-$(date -u +%Y%m%d-%H%M%S)-XXXXXX")
  git -C "$DIR" rev-parse HEAD > "$backup/revision"
  git -C "$DIR" diff --binary HEAD > "$backup/tracked.patch"
  cp -- "$list_dir/tracked" "$backup/tracked-paths"
  cp -- "$list_dir/untracked" "$backup/untracked-paths"
  while IFS= read -r -d '' relative; do
    [[ -e $DIR/$relative || -L $DIR/$relative ]] || continue
    mkdir -p -- "$backup/files/$(dirname -- "$relative")"
    cp -a -- "$DIR/$relative" "$backup/files/$relative"
  done < <(cat -- "$list_dir/tracked" "$list_dir/untracked")
  rm -rf -- "$list_dir"
  UPDATE_BACKUP=$backup
  say "Local changes saved to ${backup/#$HOME/\~}"
}

setup_success() {
  local version
  version=$(installed_version)
  printf '\n%s%s Setup complete%s\n' "$GOOD" "$ON" "$RESET"
  printf '  Quadra Lite%s is ready in your app menu.\n' "${version:+ $version}"
  printf '\n  %sNext steps%s\n' "$BOLD" "$RESET"
  printf '    1. Open Quadra Lite from the app menu, or run quadralite.\n'
  printf '    2. Pick a runtime on its welcome screen; it installs it.\n'
  printf '    3. Sign in to Roblox and choose a game.\n'
  [[ -z $UPDATE_BACKUP ]] || printf '\n  Source backup: %s\n' "${UPDATE_BACKUP/#$HOME/\~}"
  printf '\n'
}

# ------------------------------------------------------------------ install

check_requirements() {
  command -v git >/dev/null ||
    die "git is missing. Install it with your distribution's package manager, then rerun this installer."
  command -v python3 >/dev/null ||
    die "Python 3 is missing. Install it with your distribution's package manager, then rerun this installer."
  python3 - <<'PYTHON' 2>/dev/null ||
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk
PYTHON
    die "Python's GTK 4 and libadwaita bindings are missing (PyGObject, GTK 4, libadwaita). Install them with your distribution's package manager, then rerun this installer."
  say "git, Python 3, GTK 4 and libadwaita are installed"
}

do_install() {
  [[ ! -e $DIR ]] || { [[ -d $DIR/.git ]] && launcher_package "$DIR" >/dev/null; } ||
    die "$DIR already exists without a Git checkout. Move it aside before installing."
  step 1 "Check what the launcher needs"
  check_requirements

  step 2 "Prepare Quadra Lite"
  if [[ -d $DIR/.git ]]; then
    say "Updating Quadra Lite"

    # Fetch first, then preserve local repairs before replacing tracked files.
    # Session data, downloads and backups stay in the checkout unchanged.
    git -C "$DIR" config remote.origin.promisor true
    git -C "$DIR" config remote.origin.partialclonefilter blob:none
    git -C "$DIR" fetch --filter=blob:none origin main
    backup_checkout_changes
    git -C "$DIR" reset --hard origin/main

  else
    say "Downloading Quadra Lite"
    git clone --filter=blob:none --depth 1 --single-branch --branch main "$REPO" "$DIR"
  fi
  step 3 "Add the launcher to your desktop"
  "$DIR/launcher/install.sh"
  setup_success
}

# ---------------------------------------------------------------- uninstall

# The launcher's Python package in a checkout.
launcher_package() {
  if [[ -f $1/launcher/quadra/core/__init__.py ]]; then
    printf '%s' "$1/launcher/quadra"
    return 0
  fi
  return 1
}

# The checkout this script makes: nothing is deleted unless $DIR is one.
existing_checkout() {
  if [[ -f $DIR/build_debug_shim.sh ]] && launcher_package "$DIR" >/dev/null &&
     [[ -f $DIR/launcher/quadralite-launcher ]]; then
    printf '%s' "$DIR"
    return 0
  fi
  return 1
}
is_installed() {
  existing_checkout >/dev/null
}
installed_version() {
  local checkout package
  checkout=$(existing_checkout) || return 0
  package=$(launcher_package "$checkout") || return 0
  sed -n 's/^__version__ = "\(.*\)"/\1/p' "$package/__init__.py" 2>/dev/null
}

# Removes what do_install and the launcher put on this computer; with an
# argument, Darling's prefix as well. Darling and the other packages stay.
do_uninstall() {
  local purge=${1:-}
  if [[ ! -e $DIR ]]; then
    DIR=$(existing_checkout) || DIR=$DATA_HOME/QuadraLite
  fi
  if [[ -e $DIR ]] && ! [[ -f $DIR/build_debug_shim.sh &&
      -f $DIR/launcher/quadralite-launcher ]]; then
    die "$DIR does not look like Quadra Lite, so it is left alone."
  fi
  # Nothing in the prefix may change under a running Darling (it keeps
  # showing deleted files), and nothing should run from the folder that goes.
  if pgrep -u "$(id -u)" -x darlingserver >/dev/null 2>&1; then
    say "Stopping Roblox and Darling"
    DPREFIX="$PREFIX" "$DARLING_EXECUTABLE" shutdown >/dev/null 2>&1 || true
  fi
  if [[ -e $DIR ]]; then
    say "Removing the launcher and Roblox (${DIR/#$HOME/\~})"
    rm -rf -- "$DIR"
  fi
  say "Removing the app menu entries, icons and the quadralite command"
  local apps=$DATA_HOME/applications
  rm -f -- "$apps/io.github.schlabbadabadoo.QuadraLite.desktop" \
    "$apps/io.github.schlabbadabadoo.QuadraLite.URI.desktop" \
    "$apps/quadralite-roblox-window.desktop" \
    "$DATA_HOME"/icons/hicolor/*/apps/quadralite.png \
    "$DATA_HOME/icons/hicolor/scalable/apps/quadralite.svg"
  # Only our own CiderDarling entry; a user's entry of that name stays.
  local cider_entry=$apps/io.github.schlabbadabadoo.QuadraLite.CiderDarling.desktop
  if [[ -f $cider_entry && ! -L $cider_entry ]] && grep -qsx 'X-QuadraLite-Managed=true' "$cider_entry"; then
    rm -f -- "$cider_entry"
  fi
  local cider_link=$HOME/.local/bin/quadralite
  if [[ -L $cider_link && $(readlink "$cider_link") == */quadralite-launcher ]]; then
    rm -f -- "$cider_link"
  fi
  # Quadra Lite as the handler of Roblox links.
  if [[ -f $CONFIG_HOME/mimeapps.list ]]; then
    sed -i -e 's/io\.github\.schlabbadabadoo\.QuadraLite\.URI\.desktop;\{0,1\}//g' \
      -e '/^[^=[]*=$/d' "$CONFIG_HOME/mimeapps.list"
  fi
  update-mime-database "$DATA_HOME/mime" >/dev/null 2>&1 || true
  update-desktop-database "$apps" >/dev/null 2>&1 || true
  say "Removing settings and cache"
  rm -rf -- "$CONFIG_HOME/quadralite" "$CACHE_HOME/quadralite"
  if [[ -n $purge && -e $PREFIX ]]; then
    [[ $PREFIX == "$HOME"/?* ]] || die "Darling's prefix $PREFIX is not in your home folder, so it is left alone."
    say "Removing Darling's prefix (${PREFIX/#$HOME/\~}), with your Roblox sign-in"
    rm -rf -- "$PREFIX"
  fi
  # Rosemary and its Roblox client live in the user data folder, outside the
  # checkout, like Darling's prefix: kept unless asked.
  local rosemary_data=$DATA_HOME/quadralite
  if [[ -n $purge && -d $rosemary_data ]]; then
    [[ $rosemary_data == "$HOME"/?* ]] || die "Rosemary's folder $rosemary_data is not in your home folder, so it is left alone."
    say "Removing Rosemary and its Roblox client (${rosemary_data/#$HOME/\~})"
    rm -rf -- "$rosemary_data"
  elif [[ -d $rosemary_data ]]; then
    say "Rosemary's files stay in ${rosemary_data/#$HOME/\~}; --purge removes them."
  fi
  say "Quadra Lite is uninstalled."
  if command -v "$DARLING_EXECUTABLE" >/dev/null; then
    printf '    %s%s stays installed.%s\n' "$DIM" "$(darling_runtime_name)" "$RESET"
  fi
}

# --------------------------------------------------------------------- menu

# Drawn on the terminal's alternate screen, which gets its old contents back
# when the menu closes.
MENU_ON=''
MENU_SCREEN=''
menu_open() {
  MENU_ON=1
  if [[ ${TERM:-dumb} != dumb ]]; then
    MENU_SCREEN=1
    printf '\033[?1049h\033[?25l' >/dev/tty
  fi
}
menu_close() {
  [[ -n $MENU_ON ]] || return 0
  MENU_ON=''
  if [[ -n $MENU_SCREEN ]]; then
    MENU_SCREEN=''
    printf '\033[?25h\033[?1049l' >/dev/tty
  fi
}

banner() {
  printf '\n  %sQUADRA LITE%s\n  github.com/Schlabbadabadoo/Quadra-Lite\n' "$BOLD" "$RESET"
}

# choose TEXT ITEM...: a menu of "label|hint" items below TEXT (printf %b).
# Sets CHOICE to the chosen item's index, or to -1 for quit.
CHOICE=-1
choose() {
  local text=$1
  shift
  local count=$# index=0 key rest item label hint i
  if [[ -z $MENU_SCREEN ]]; then
    {
      banner
      printf '\n%b\n\n' "$text"
      i=1
      for item; do
        printf '  %s. %s  %s\n' "$i" "${item%%|*}" "${item#*|}"
        i=$((i + 1))
      done
    } >/dev/tty
    while :; do
      printf '\n  Choose 1-%s [1], or q to quit: ' "$count" >/dev/tty
      IFS= read -r key </dev/tty || { CHOICE=-1; return; }
      [[ -n $key ]] || key=1
      case $key in
        q | Q) CHOICE=-1; return ;;
        [1-9]) if ((key <= count)); then CHOICE=$((key - 1)); return; fi ;;
      esac
    done
  fi
  while :; do
    {
      printf '\033[H\033[2J\n'
      banner
      printf '\n%b\n\n' "$text"
      i=0
      for item; do
        label=${item%%|*}
        hint=${item#*|}
        if ((i == index)); then
          printf '  %s %s %-22s%s %s\n' "$SELECTED" "$POINTER" "$label" "$RESET" "$hint"
        else
          printf '     %-22s %s%s%s\n' "$label" "$DIM" "$hint" "$RESET"
        fi
        i=$((i + 1))
      done
      printf '\n  %s%s%s\n' "$DIM" "$KEYS" "$RESET"
    } >/dev/tty
    IFS= read -rsn1 key </dev/tty || { CHOICE=-1; return; }
    case $key in
      $'\033')
        rest=''
        IFS= read -rsn2 -t 0.05 rest </dev/tty || true
        case $rest in
          '[A' | 'OA') index=$(((index + count - 1) % count)) ;;
          '[B' | 'OB') index=$(((index + 1) % count)) ;;
          '') CHOICE=-1; return ;;
        esac ;;
      k | K) index=$(((index + count - 1) % count)) ;;
      j | J) index=$(((index + 1) % count)) ;;
      [1-9]) if ((key <= count)); then CHOICE=$((key - 1)); return; fi ;;
      q | Q) CHOICE=-1; return ;;
      '') CHOICE=$index; return ;;
    esac
  done
}

menu_main() {
  local text first="Start setup|Review what will be installed"
  if is_installed; then
    text="  ${BOLD}Welcome back to Quadra Lite${RESET}

  ${GOOD}${ON}${RESET} Version $(installed_version) is installed.
  Keep your launcher up to date.
  ${DIM}${DIR/#$HOME/\~}${RESET}"
    first="Update Quadra Lite|Review the update plan"
  else
    text="  ${BOLD}Welcome to Quadra Lite${RESET}
  ${DIM}First setup · 1 of 3${RESET}

  Play the macOS Roblox client on your Linux desktop.
  This installs the launcher only. When you open it, it helps you choose
  Rosemary or Darling, then installs Roblox and signs you in."
  fi
  choose "$text" "$first" "Uninstall|Remove Quadra Lite from this computer" "Quit|"
}

menu_install() {
  local operation='Install'
  is_installed && operation='Update'
  while :; do
    choose "  ${BOLD}Setup · 2 of 3${RESET}

$(setup_plan)" "Continue|Confirm this setup plan" "Back|Return to the welcome screen"
    [[ $CHOICE == 0 ]] || return 1
    choose "  ${BOLD}Ready to ${operation,,} Quadra Lite${RESET}
  ${DIM}Setup · 3 of 3${RESET}

  Destination: ${DIR/#$HOME/\~}
  Setup downloads the launcher and adds it to your app menu.
  When you open Quadra Lite, it guides you through the rest.

  ${DIM}Begin when you're ready.${RESET}" \
      "$operation Quadra Lite|Begin setup" "Back|Review the plan again"
    case $CHOICE in
      0) return 0 ;;
      1) ;;
      *) return 1 ;;
    esac
  done
}

# The uninstall screen. Sets PURGE; false for "back".
PURGE=''
menu_uninstall() {
  local where=${DIR/#$HOME/\~} prefix=${PREFIX/#$HOME/\~}
  choose "  ${BOLD}Uninstall removes${RESET}
    ${BULLET} $where (the launcher and Roblox)
    ${BULLET} the app menu entries, icons and the quadralite command
    ${BULLET} settings and cache

  ${DIM}Darling stays installed. Its prefix, $prefix, holds your Roblox sign-in.
  Rosemary's files, ${DATA_HOME/#$HOME/\~}/quadralite, stay too.${RESET}" \
    "Uninstall|keep $prefix and Rosemary's files" "Uninstall everything|also delete $prefix and Rosemary's files" "Back|"
  case $CHOICE in
    0)
      PURGE=''
      return 0 ;;
    1)
      choose "  ${BAD}Delete $prefix?${RESET}

  It is Darling's macOS home folder: your Roblox sign-in, and anything
  else installed or saved in Darling, goes with it. So do Rosemary's files,
  including its Roblox client." \
        "No, go back|" "Yes, delete it|"
      [[ $CHOICE == 1 ]] || return 1
      PURGE=1
      return 0 ;;
    *) return 1 ;;
  esac
}

usage() {
  cat <<USAGE
Quadra Lite installer

  install.sh               a menu in a terminal; without one, install or update
  install.sh --install     review the setup plan, then install or update
  install.sh --update      same as --install
  install.sh --install --yes
                           install or update without setup prompts
  install.sh --uninstall   remove Quadra Lite (asks first, unless --yes)
  install.sh --uninstall --purge
                           also delete the selected Darling prefix (Roblox sign-in)
                           and Rosemary's files, including its Roblox client

This installs the launcher only; it needs git, Python 3, GTK 4 and libadwaita.
Quadra Lite's first-boot screen chooses the runtime (Rosemary or Darling) and
installs it. Darling's tools are installed by install-runtime.sh in Quadra
Lite's folder, which that screen runs for you.
USAGE
}

main() {
  local action='' assume_yes='' reviewed='' arg
  while (($#)); do
    arg=$1
    case $arg in
      --install | --update) action=install ;;
      --uninstall) action=uninstall ;;
      --purge) PURGE=1 ;;
      -y | --yes) assume_yes=1 ;;
      -h | --help)
        usage
        return 0 ;;
      --backend | --backend=* | --darling | --darling=* | --install-runtime)
        die "$arg moved: Quadra Lite's first-boot screen chooses the runtime, and ${DIR/#$HOME/\~}/install-runtime.sh installs Darling." ;;
      *) die "Unknown option: $arg (see --help)" ;;
    esac
    shift
  done
  load_darling_selection
  # Questions are read from the terminal; with curl | bash stdin is this script.
  if [[ ! -t 0 ]] && (: </dev/tty) 2>/dev/null; then exec </dev/tty; fi
  [[ $EUID -ne 0 ]] || die "Run this as your user, not root."
  local terminal=''
  [[ -t 0 && -t 1 ]] && terminal=1

  if [[ -z $action && -n $terminal && -z $assume_yes ]]; then
    trap 'menu_close' EXIT
    trap 'menu_close; exit 130' INT TERM
    menu_open
    while [[ -z $action ]]; do
      menu_main
      case $CHOICE in
        0) if menu_install; then action=install; reviewed=1; fi ;;
        1) if menu_uninstall; then action=uninstall; fi ;;
        *) action=quit ;;
      esac
    done
    menu_close
    [[ $action == quit ]] || banner
  elif [[ $action == install && -n $terminal && -z $assume_yes ]]; then
    trap 'menu_close' EXIT
    trap 'menu_close; exit 130' INT TERM
    menu_open
    if ! menu_install; then
      menu_close
      say "Setup cancelled."
      return 0
    fi
    reviewed=1
    menu_close
    banner
  elif [[ $action == uninstall && -z $assume_yes ]]; then
    [[ -n $terminal ]] || die "Not uninstalling without a terminal to ask in; add --yes."
    local answer='' what="Quadra Lite"
    [[ -n $PURGE ]] && what+=" and Darling's prefix ${PREFIX/#$HOME/\~}"
    printf 'Remove %s? [y/N] ' "$what"
    IFS= read -r answer || true
    if [[ $answer != [Yy]* ]]; then
      say "Nothing removed."
      return 0
    fi
  fi

  case ${action:-install} in
    install)
      if [[ -z $reviewed ]]; then
        banner
        printf '\n'
        setup_plan
      fi
      do_install ;;
    uninstall) do_uninstall "$PURGE" ;;
    quit) ;;
  esac
}

main "$@"; exit
