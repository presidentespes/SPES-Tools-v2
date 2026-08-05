from __future__ import annotations

import json
import re
import tempfile
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from spes_tools.version import APP_VERSION

GITHUB_REPOSITORY = "presidentespes/SPES-Tools-v2"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    page_url: str
    installer_url: str = ""
    installer_name: str = ""


def _version_tuple(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value)
    return tuple(int(number) for number in numbers) or (0,)


def check_for_update(timeout: float = 8.0) -> ReleaseInfo | None:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "SPES-Configurator"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    tag = str(payload.get("tag_name", "")).lstrip("vV")
    if not tag or _version_tuple(tag) <= _version_tuple(APP_VERSION):
        return None

    installer_url = ""
    installer_name = ""
    for asset in payload.get("assets", []):
        name = str(asset.get("name", ""))
        if name.lower().endswith("setup.exe"):
            installer_url = str(asset.get("browser_download_url", ""))
            installer_name = name
            break

    return ReleaseInfo(
        version=tag,
        page_url=str(payload.get("html_url", f"https://github.com/{GITHUB_REPOSITORY}/releases")),
        installer_url=installer_url,
        installer_name=installer_name,
    )


def download_installer(release: ReleaseInfo, destination_dir: str | Path | None = None) -> Path:
    if not release.installer_url:
        raise ValueError("La release non contiene un installer Setup.exe.")
    folder = Path(destination_dir) if destination_dir else Path(tempfile.gettempdir()) / "SPES_Updates"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (release.installer_name or f"SPES_Configuratore_Contabile_{release.version}_Setup.exe")
    request = urllib.request.Request(release.installer_url, headers={"User-Agent": "SPES-Configurator"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    return target


def open_release_page(release: ReleaseInfo) -> None:
    webbrowser.open(release.page_url)
