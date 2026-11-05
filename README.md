<p align="center">
  <img src="branding/quadrahq.webp" alt="Quadra Lite logo" width="160">
</p>

<h1 align="center">Quadra Lite</h1>

<p align="center">
  A lightweight, game-only fork of <a href="https://github.com/QuadraHQ/Quadra">Quadra</a> for the
  macOS Roblox Player client, running on Linux through
  <a href="https://github.com/microlift/rosemary">Rosemary</a> or
  <a href="https://darlinghq.org">Darling</a>. Roblox Studio, Wine, VR, Discord Rich Presence
  and Mods are removed; the launcher stays open while you play.
</p>

## Install

From a checkout of this fork:

```bash
./install.sh
```

Works on Arch and its relatives (CachyOS, EndeavourOS, Manjaro), Ubuntu 24.04+,
Debian 13, Linux Mint 22 and Fedora.

The installer downloads the launcher into `~/.local/share/QuadraLite` and adds a
menu entry. It installs no runtime: on first launch the setup screen chooses
between Rosemary (recommended) and Darling, and installs that runtime for you.

Run `./install.sh` again to update or uninstall. The launcher also checks for
updates itself.

**Dependencies (Debian/Ubuntu/Mint):**

```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
  gir1.2-webkit-6.0 unzip
```

**Dependencies (Arch/CachyOS/EndeavourOS/Manjaro):**

```bash
sudo pacman -S python python-gobject gtk4 libadwaita webkitgtk-6.0 unzip
```

Darling itself is installed through the setup screen (or beforehand via your
package manager).

## Usage

```bash
quadralite                # open the launcher
quadralite --settings     # open settings directly
quadralite --collect-diagnostics
```

Settings live in `~/.config/quadralite/settings.json`. Cache and logs are in
`~/.cache/quadralite/`.

## Fast flags

Fast flags are edited in the launcher (Settings → Fast flags) and are kept.

## Playtime

Playtime tracking has been removed in this fork.

## Troubleshooting

- **Roblox won't start / wrong renderer:** check Settings → Roblox and Settings →
  Quadra M2VK. Metal (Quadra M2VK) needs a Vulkan-capable GPU.
- **Missing libraries:** install the dependencies above.
- **Logs:** `~/.local/share/quadralite/logs/` (or open the logs folder from the
  launcher menu).
- **Last error:** `~/.cache/quadralite/last-error.txt`.

Submit bugs through the upstream report flow or open an issue on this fork.

## License

GPL-3.0-or-later. Roblox® is a registered trademark of Roblox Corporation.
Quadra Lite is not affiliated with or endorsed by Roblox Corporation.