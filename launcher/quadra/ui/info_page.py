"""The Info page."""

import threading

from gi.repository import Adw, Gdk, GLib, Gtk

from .. import author, hardware
from ..i18n import _
from . import system

__all__ = [
    "ABOUT",
    "InfoPage",
]

ABOUT = (
    "Quadra runs the real Roblox client for macOS on Linux through Darling. "
    "It is not made by Roblox and is not affiliated with it."
)


class InfoPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__(title=_("Info"), icon_name="help-about-symbolic")
        self.window = window

        about = Adw.PreferencesGroup(title="Quadra", description=_(ABOUT))
        self.add(about)

        community = Adw.PreferencesGroup(title=_("Community"))
        for title, icon, uri in system._links():
            row = Adw.ActionRow(title=title, activatable=True)
            row.add_prefix(Gtk.Image(icon_name=icon))
            row.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
            row.connect("activated", lambda *_args, u=uri: system._open_uri(window, u))
            community.add(row)
        self.add(community)

        hardware_group = Adw.PreferencesGroup(title=_("Hardware"))
        self.hardware_rows = {}
        for key, title in (
            ("cpu", _("CPU")),
            ("gpu", _("GPU")),
            ("vram", _("VRAM")),
            ("ram", _("Memory")),
            ("display", _("Display")),
            ("driver", _("GPU driver")),
            ("renderers", _("Available renderers")),
            ("selected_gpu", _("Selected GPU")),
            ("recommended", _("Recommended renderer")),
        ):
            row = Adw.ActionRow(title=title)
            value = Gtk.Label(xalign=1, css_classes=["dim-label"])
            row.add_suffix(value)
            self.hardware_rows[key] = value
            hardware_group.add(row)
        refresh_btn = Adw.ActionRow(title=_("Refresh hardware info"), activatable=True)
        refresh_btn.add_suffix(Gtk.Image(icon_name="view-refresh-symbolic"))
        refresh_btn.connect("activated", lambda *_args: self._refresh_hardware())
        hardware_group.add(refresh_btn)
        self.add(hardware_group)

        self._refresh_hardware()
        self.avatar = Adw.Avatar(size=48, text=author.NAME, show_initials=True)
        profile = Adw.ActionRow(
            title=author.NAME,
            activatable=True,
            subtitle=_("{user} on Roblox", user="@" + author.ROBLOX_USER),
        )
        profile.add_prefix(self.avatar)
        profile.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
        profile.connect(
            "activated", lambda *_args: system._open_uri(window, author.PROFILE_URL)
        )
        made_by.add(profile)
        maintainer_avatar = Adw.Avatar(
            size=48, text=author.MAINTAINER, show_initials=True
        )
        try:
            maintainer_avatar.set_custom_image(
                Gdk.Texture.new_from_filename(str(author.MAINTAINER_AVATAR))
            )
        except GLib.Error:
            pass
        maintainer = Adw.ActionRow(
            title=author.MAINTAINER,
            activatable=True,
            subtitle=_("Maintains this version: stability and performance fixes"),
        )
        maintainer.add_prefix(maintainer_avatar)
        maintainer.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
        maintainer.connect(
            "activated", lambda *_args: system._open_uri(window, author.MAINTAINER_URL)
        )
        made_by.add(maintainer)

        self.ui_contributor_avatar = Adw.Avatar(
            size=48, text=author.UI_CONTRIBUTOR, show_initials=True
        )
        ui_contributor = Adw.ActionRow(
            title=author.UI_CONTRIBUTOR, activatable=True, subtitle=_("Better UI, Mods")
        )
        ui_contributor.add_prefix(self.ui_contributor_avatar)
        ui_contributor.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
        ui_contributor.connect(
            "activated",
            lambda *_args: system._open_uri(window, author.UI_CONTRIBUTOR_URL),
        )
        made_by.add(ui_contributor)

        claude = Adw.ActionRow(
            title=_("Assisted with Claude Opus 5.5"),
            activatable=True,
            subtitle=_(
                "Anthropic's AI assisted writing the code together with the authors"
            ),
        )
        claude.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic"))
        claude.connect(
            "activated",
            lambda *_args: system._open_uri(window, "https://www.anthropic.com/claude"),
        )
        made_by.add(claude)
        self.add(made_by)

        settings = dict(window.settings)
        threading.Thread(
            target=lambda: GLib.idle_add(self._show_avatar, author.avatar(settings)),
            daemon=True,
        ).start()
        threading.Thread(
            target=lambda: GLib.idle_add(
                self._show_tinytosha_avatar, author.tinytosha_avatar()
            ),
            daemon=True,
        ).start()

    def _refresh_hardware(self):
        def work():
            profile = hardware.detect(force=True)
            GLib.idle_add(self._apply_hardware, profile)

        threading.Thread(target=work, daemon=True).start()

    def _apply_hardware(self, profile):
        cpu = profile.get("cpu", {})
        self.hardware_rows["cpu"].set_label(cpu.get("name") or "unknown")
        gpus = profile.get("gpus", [])
        gpu_name = gpus[0]["name"] if gpus else "unknown"
        self.hardware_rows["gpu"].set_label(gpu_name)
        vram = gpus[0].get("vram_bytes") if gpus else None
        self.hardware_rows["vram"].set_label(hardware.format_bytes(vram) if vram else "unknown")
        mem = profile.get("memory", {})
        total = mem.get("total_bytes")
        avail = mem.get("available_bytes")
        ram_str = hardware.format_bytes(total) if total else "unknown"
        if avail:
            ram_str += f" ({hardware.format_bytes(avail)} free)"
        self.hardware_rows["ram"].set_label(ram_str)
        disp = profile.get("display", {})
        w, h = disp.get("width"), disp.get("height")
        if w and h:
            disp_str = f"{w}x{h}"
            if disp.get("refresh_hz"):
                disp_str += f" @ {disp['refresh_hz']:.0f} Hz"
        else:
            disp_str = "unknown"
        self.hardware_rows["display"].set_label(disp_str)
        drv = gpus[0].get("driver") if gpus else None
        self.hardware_rows["driver"].set_label(drv or "unknown")
        g = profile.get("graphics", {})
        renderers = []
        if g.get("opengl_version"):
            renderers.append("OpenGL")
        if g.get("vulkan_available"):
            renderers.append("Vulkan")
        self.hardware_rows["renderers"].set_label(", ".join(renderers) if renderers else "OpenGL")
        self.hardware_rows["selected_gpu"].set_label(profile.get("selected_gpu") or "Automatic")
        r, reason = hardware.recommend_renderer(profile)
        self.hardware_rows["recommended"].set_label(f"{r} ({reason})")
        # warnings
        for w in profile.get("warnings", []):
            pass
        return False

    def _show_avatar(self, path):
        if path:
            try:
                self.avatar.set_custom_image(Gdk.Texture.new_from_filename(str(path)))
            except GLib.Error:
                pass
        return False

    def _show_tinytosha_avatar(self, path):
        if path:
            try:
                self.ui_contributor_avatar.set_custom_image(
                    Gdk.Texture.new_from_filename(str(path))
                )
            except GLib.Error:
                pass
        return False
