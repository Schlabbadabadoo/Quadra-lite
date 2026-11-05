<h1 align="center">Quadra Lite</h1>

<p align="center">
  <a href="https://github.com/Schlabbadabadoo/Quadra-Lite/releases"><img src="https://img.shields.io/github/v/release/Schlabbadabadoo/Quadra-Lite?style=flat-square&color=8a2be2" alt="release"></a>
  <a href="https://github.com/Schlabbadabadoo/Quadra-Lite/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Schlabbadabadoo/Quadra-Lite?style=flat-square" alt="license"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square" alt="python">
  <img src="https://img.shields.io/badge/platform-linux-lightgrey?style=flat-square" alt="platform">
  <a href="https://discord.gg/tEprTnKu7A"><img src="https://img.shields.io/badge/discord-join-5865F2?style=flat-square&logo=discord&logoColor=white" alt="discord"></a>
</p>

<p align="center">
  A lightweight, game-only fork of <a href="https://github.com/QuadraHQ/Quadra">Quadra</a> for the
  macOS Roblox Player client on Linux. Runs through
  <a href="https://github.com/microlift/rosemary">Rosemary</a> or
  <a href="https://darlinghq.org">Darling</a>. Roblox Studio, Wine, VR, Discord Rich Presence
  and Mods are removed; the launcher stays open while you play.
</p>

## Why Quadra Lite?

- **Game only** — no Roblox Studio, no Wine, no WebView2/Kombucha layer.
- **Smaller footprint** — fewer settings, fewer pages, faster startup.
- **Still fully functional** — playtime-free, fast flags, runtime choice (Rosemary/Darling),
  graphics, DNS, diagnostics, all intact.
- **Coexists with upstream Quadra** — separate binary (`quadralite`), app ID, and data
  directories (`~/.local/share/quadralite`, `~/.config/quadralite`, `~/.cache/quadralite`).

## Features

| Feature | Status |
|---|---|
| Play Roblox on Linux | ✅ |
| Rosemary / Darling runtime choice | ✅ |
| Fast flags editor | ✅ |
| Graphics & renderer (OpenGL / Metal / Vulkan) | ✅ |
| DNS override & telemetry blocking | ✅ |
| Server location lookup | ✅ |
| Diagnostics & hardware report | ✅ |
| Playtime counter | ❌ removed |
| VR (OpenXR) | ❌ removed |
| Discord Rich Presence | ❌ removed |
| Mods | ❌ removed |
| Roblox Studio | ❌ removed |
| Grid / Monochrome launcher themes | ❌ GNOME only |

## Install

```bash
git clone https://github.com/Schlabbadabadoo/Quadra-Lite.git
cd Quadra-Lite
./install.sh
```

Or in one line:

```bash
curl -fsSL https://raw.githubusercontent.com/Schlabbadabadoo/Quadra-Lite/main/install.sh | bash
```

Works on Arch and relatives (CachyOS, EndeavourOS, Manjaro), Ubuntu 24.04+,
Debian 13, Linux Mint 22 and Fedora.

The installer drops the launcher in `~/.local/share/QuadraLite` and adds a menu
entry. It installs no runtime: on first launch the setup screen picks between
Rosemary (recommended) and Darling and installs that runtime for you. Run
`./install.sh` again to update or uninstall.

**Dependencies (Debian/Ubuntu/Mint):**

```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  gir1.2-webkit-6.0 unzip
```

WebKitGTK is used only by the launcher for the embedded sign-in web view;
Roblox itself does not depend on it.

**Dependencies (Arch/CachyOS/EndeavourOS/Manjaro):**

```bash
sudo pacman -S python python-gobject gtk4 libadwaita webkitgtk-6.0 unzip
```

## Usage

```bash
quadralite              # open the launcher
quadralite --settings   # open settings directly
quadralite --collect-diagnostics
```

Settings: `~/.config/quadralite/settings.json`  
Cache/logs: `~/.cache/quadralite/`

## Troubleshooting

Join the [Discord server](https://discord.gg/tEprTnKu7A) for help and questions.

- **Roblox won't start / wrong renderer:** Settings → Roblox and Settings →
  Quadra M2VK. Metal (Quadra M2VK) needs a Vulkan-capable GPU.
- **Missing libraries:** install the dependencies above.
- **Logs:** `~/.local/share/QuadraLite/logs/`, or use the launcher menu.
- **Last error:** `~/.cache/quadralite/last-error.txt`.

## Development

```bash
PYTHONPATH=launcher python3 -m unittest discover -s tests -p '*_test.py'
```

## License

GPL-3.0-or-later. Roblox® is a registered trademark of Roblox Corporation.
Quadra Lite is not affiliated with or endorsed by Roblox Corporation.
