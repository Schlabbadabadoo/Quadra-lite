#!/usr/bin/env bash
# Installs the Quadra Lite launcher for the current user: menu entry, icons
# and a `quadralite` command. Run again after moving the project folder.
set -euo pipefail
launcher_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
project_dir=$(dirname -- "$launcher_dir")
data_home=${XDG_DATA_HOME:-$HOME/.local/share}

for size in 16 22 24 32 48 64 128 256 512 1024; do
  install -Dm644 "$project_dir/branding/icons/quadralite-$size.png" \
    "$data_home/icons/hicolor/${size}x${size}/apps/quadralite.png"
done

install -d "$HOME/.local/bin"
ln -sf "$launcher_dir/quadralite-launcher" "$HOME/.local/bin/quadralite"

# The launcher's path as a quoted Exec argument (Desktop Entry spec): a
# project folder with a space in its path broke the menu entries.
exec_path=${launcher_dir//\\/\\\\\\\\}
exec_path=${exec_path//\"/\\\\\"}
exec_path=${exec_path//\`/\\\\\`}
exec_path=${exec_path//\$/\\\\\$}
exec_path=\"${exec_path//\%/%%}/quadralite-launcher\"

install -d "$data_home/applications"
cat > "$data_home/applications/io.github.schlabbadabadoo.QuadraLite.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Quadra Lite
Comment=Run the macOS Roblox client on Linux through Rosemary or Darling
GenericName=Roblox launcher
Exec=$exec_path
Icon=quadralite
Terminal=false
Categories=Game;
Keywords=roblox;rosemary;darling;
StartupNotify=true
Actions=settings;

[Desktop Action settings]
Name=Settings
Exec=$exec_path --settings
Icon=quadralite
DESKTOP

# Roblox links are LaunchServices protocol handoffs on macOS.  Keep a
# separate hidden entry for Linux so the complete URI is substituted into one
# launcher argument and can reach RobloxPlayer unchanged.
cat > "$data_home/applications/io.github.schlabbadabadoo.QuadraLite.URI.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Quadra Lite Roblox Link Handler
Comment=Open Roblox links in Quadra Lite
Exec=$exec_path %u
Icon=quadralite
Terminal=false
NoDisplay=true
MimeType=x-scheme-handler/roblox;x-scheme-handler/roblox-player;
DESKTOP

# A shortcut to CiderDarling's settings, only while CiderDarling is installed
# (packaging/io.github.schlabbadabadoo.QuadraLite.CiderDarling.desktop; the
# launcher keeps it in step when runtimes change later). Its marker line
# identifies our copy.
ciderdarling_entry=$data_home/applications/io.github.schlabbadabadoo.QuadraLite.CiderDarling.desktop
ciderdarling_state=0
PYTHONPATH=$launcher_dir python3 -c '
import sys
from quadra.darling import runtime
try:
    installed = "ciderdarling" in runtime.installed_runtimes()
except Exception:
    sys.exit(2)
sys.exit(0 if installed else 1)' 2>/dev/null || ciderdarling_state=$?
ciderdarling_ours=''
if [[ ! -e $ciderdarling_entry && ! -L $ciderdarling_entry ]] ||
    { [[ ! -L $ciderdarling_entry ]] && grep -qsx 'X-QuadraLite-Managed=true' "$ciderdarling_entry"; }; then
  ciderdarling_ours=1  # absent, or ours: a user's own entry of that name stays
fi
if [[ $ciderdarling_state == 0 && -n $ciderdarling_ours ]]; then
  cat > "$ciderdarling_entry" <<DESKTOP
[Desktop Entry]
Type=Application
Name=CiderDarling Settings
Comment=Graphics card, runtime and diagnostics settings for CiderDarling
Exec=$exec_path --ciderdarling-settings
Icon=quadralite
Terminal=false
Categories=Game;
Keywords=ciderdarling;darling;gpu;
StartupNotify=true
X-QuadraLite-Managed=true
DESKTOP
elif [[ $ciderdarling_state == 1 && -n $ciderdarling_ours && -e $ciderdarling_entry ]]; then
  rm -f -- "$ciderdarling_entry"
fi
if command -v xdg-mime >/dev/null; then
  for type in x-scheme-handler/roblox x-scheme-handler/roblox-player; do
    xdg-mime default io.github.schlabbadabadoo.QuadraLite.URI.desktop "$type"
  done
fi

# The game window itself (X11 class RobloxPlayer) gets the same icon in docks.
cat > "$data_home/applications/quadralite-roblox-window.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Roblox (Quadra Lite)
Exec=$exec_path
Icon=quadralite
NoDisplay=true
StartupWMClass=RobloxPlayer
DESKTOP

update-desktop-database "$data_home/applications" 2>/dev/null || true
# No gtk-update-icon-cache: with -t it wrote a cache into the user's icon
# folder that other apps do not update, which can hide their icons.
echo "Quadra Lite installed: find it in the app menu or run: quadralite"
