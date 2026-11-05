"""Roblox game metadata (name, creator, icon) with an on-disk cache.

Used by the launcher's "this game was updated recently" notice. Fetched from
Roblox's public, unauthenticated APIs."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import urllib.request

from . import core

log = logging.getLogger("quadra.game_info")

CACHE_FILE = core.DATA_DIR / "game_cache.json"

_GAME_CACHE: dict[int, dict] = {}
_CACHE_LOCK = threading.RLock()
_CACHE_LIMIT = 512
_CACHE_FILE_LIMIT = 2 * 1024 * 1024
_HTTP_BODY_LIMIT = 1024 * 1024
_PLACEHOLDER_NAMES = {"[TITLE UNAVAILABLE]", "[UNKNOWN]"}


def _known(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if value.strip() in _PLACEHOLDER_NAMES:
        return None
    return value


def _cache_entry(place_id: int, value) -> dict | None:
    if place_id <= 0 or not isinstance(value, dict):
        return None
    universe_id = value.get("universe_id")
    if (
        not isinstance(universe_id, int)
        or isinstance(universe_id, bool)
        or universe_id <= 0
    ):
        return None
    name, creator, icon = (
        value.get("name"),
        value.get("creator", ""),
        value.get("icon_url"),
    )
    if _known(name) is None or len(name) > 1024:
        return None
    if not isinstance(creator, str) or len(creator) > 1024:
        return None
    if icon is not None and (not isinstance(icon, str) or len(icon) > 4096):
        return None
    return {
        "place_id": place_id,
        "universe_id": universe_id,
        "name": name,
        "creator": _known(creator) or "",
        "icon_url": icon,
    }


def _cached_game_info(place_id: int) -> dict | None:
    with _CACHE_LOCK:
        value = _GAME_CACHE.pop(place_id, None)
        if value is None:
            return None
        _GAME_CACHE[place_id] = value
        return dict(value)


def _load_cache():
    try:
        with CACHE_FILE.open("rb") as source:
            body = source.read(_CACHE_FILE_LIMIT + 1)
        if len(body) > _CACHE_FILE_LIMIT:
            return
        raw = json.loads(body)
        if not isinstance(raw, dict):
            return
        loaded = {}
        for key, value in raw.items():
            try:
                place_id = int(key)
            except (ValueError, TypeError):
                continue
            entry = _cache_entry(place_id, value)
            if entry:
                loaded[place_id] = entry
                if len(loaded) > _CACHE_LIMIT:
                    loaded.pop(next(iter(loaded)))
        with _CACHE_LOCK:
            _GAME_CACHE.clear()
            _GAME_CACHE.update(loaded)
    except FileNotFoundError:
        pass
    except Exception as e:
        log.debug("Failed to load game cache: %s", e)


def _save_cache():
    # Serialize writers and replace the complete file atomically. A failed
    # write must leave the previous cache readable.
    with _CACHE_LOCK:
        temporary = None
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            entries = [
                (
                    key,
                    (
                        json.dumps(str(key))
                        + ":"
                        + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                    ).encode("utf-8"),
                )
                for key, value in _GAME_CACHE.items()
            ]
            size = 2 + sum(len(body) for _, body in entries) + max(0, len(entries) - 1)
            first = 0
            while size > _CACHE_FILE_LIMIT and first < len(entries):
                key, body = entries[first]
                _GAME_CACHE.pop(key, None)
                size -= len(body) + (1 if first + 1 < len(entries) else 0)
                first += 1
            body = b"{" + b",".join(body for _, body in entries[first:]) + b"}"
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=CACHE_FILE.parent, prefix=".game_cache-", delete=False
            ) as output:
                temporary = output.name
                output.write(body)
            os.replace(temporary, CACHE_FILE)
            temporary = None
        except Exception as e:
            log.debug("Failed to save game cache: %s", e)
        finally:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass


def _store_game_info(place_id: int, info: dict):
    entry = _cache_entry(place_id, info)
    if entry is None:
        return
    with _CACHE_LOCK:
        _GAME_CACHE.pop(place_id, None)
        _GAME_CACHE[place_id] = entry
        while len(_GAME_CACHE) > _CACHE_LIMIT:
            _GAME_CACHE.pop(next(iter(_GAME_CACHE)))
        _save_cache()


def _public_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read(_HTTP_BODY_LIMIT + 1)
    if len(body) > _HTTP_BODY_LIMIT:
        raise ValueError("Public game metadata response exceeded size limit")
    return json.loads(body)


_load_cache()


def fetch_game_info(
    place_id: int,
    universe_id: int | None = None,
    *,
    cancelled=None,
    refresh: bool = False,
) -> dict | None:
    cached = _cached_game_info(place_id)
    if cached and not refresh:
        return cached
    known = cached or {}

    def stopped():
        return cancelled is not None and cancelled()

    try:
        if stopped():
            return None
        universe_id = universe_id or known.get("universe_id")
        if not universe_id:
            data = _public_json(
                f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
            )
            universe_id = data.get("universeId")

        if stopped() or not universe_id:
            return None

        data = _public_json(
            f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        )
        entries = data.get("data", [])
        if stopped() or not entries:
            return None
        entry = entries[0]
        name = _known(entry.get("name")) or known.get("name")
        creator = _known((entry.get("creator") or {}).get("name"))
        creator = creator or known.get("creator", "")

        icon_url = None
        try:
            if stopped():
                return None
            idata = _public_json(
                f"https://thumbnails.roblox.com/v1/games/icons?universeIds={universe_id}&returnPolicy=PlaceHolder&size=512x512&format=Png&isCircular=false"
            )
            ientries = idata.get("data", [])
            if ientries and ientries[0].get("state") == "Completed":
                icon_url = _known(ientries[0].get("imageUrl"))
        except Exception:
            pass

        info = _cache_entry(
            place_id,
            {
                "universe_id": universe_id,
                "name": name,
                "creator": creator,
                "icon_url": icon_url or known.get("icon_url"),
            },
        )
        if stopped() or info is None:
            return None
        if info != cached:
            _store_game_info(place_id, info)
        return info
    except Exception as e:
        log.debug("Failed to fetch game info for place %s: %s", place_id, e)
        return None
