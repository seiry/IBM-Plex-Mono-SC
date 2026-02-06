import io
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackageSpec:
    tag_prefix: str
    asset_prefix: str
    zip_out: Path
    extract_dir: Path


def _http_get_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "merge-font-workflow",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def _download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "merge-font-workflow"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    out_path.write_bytes(data)


def _extract_zip(zip_path: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)


def _find_latest_release_tag(releases, tag_prefix: str) -> dict:
    prefix = f"{tag_prefix}@"
    for release in releases:
        tag = release.get("tag_name") or ""
        if tag.startswith(prefix):
            return release
    raise RuntimeError(f"Could not find a release tag starting with {prefix}")


def _find_zip_asset(release: dict, asset_prefix: str) -> dict:
    assets = release.get("assets") or []
    for asset in assets:
        name = (asset.get("name") or "")
        if name.lower().startswith(asset_prefix.lower()) and name.lower().endswith(".zip"):
            return asset

    asset_list = "\n".join(["- " + (a.get("name") or "") for a in assets])
    tag = release.get("tag_name")
    raise RuntimeError(
        f"Could not find {asset_prefix}*.zip in {tag}. Assets:\n{asset_list}\n"
    )


def _find_file(root: Path, filename: str, prefer_unhinted: bool) -> Path:
    candidates = list(root.rglob(filename))
    if not candidates:
        raise FileNotFoundError(f"{filename} not found under {root}")

    if prefer_unhinted:
        for path in candidates:
            if re.search(r"(^|/)unhinted(/|$)", str(path).replace(os.sep, "/"), re.I):
                return path

    return candidates[0]


def main() -> int:
    repo = "IBM/plex"
    releases_url = f"https://api.github.com/repos/{repo}/releases?per_page=100&page=1"

    downloads_dir = Path("_downloads")
    src_dir = Path("_src")

    specs = [
        PackageSpec(
            tag_prefix="@ibm/plex-mono",
            asset_prefix="ibm-plex-mono",
            zip_out=downloads_dir / "ibm-plex-mono.zip",
            extract_dir=src_dir / "mono",
        ),
        PackageSpec(
            tag_prefix="@ibm/plex-sans-sc",
            asset_prefix="ibm-plex-sans-sc",
            zip_out=downloads_dir / "ibm-plex-sans-sc.zip",
            extract_dir=src_dir / "sans-sc",
        ),
    ]

    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)
    if src_dir.exists():
        shutil.rmtree(src_dir)

    releases = _http_get_json(releases_url)

    for spec in specs:
        release = _find_latest_release_tag(releases, spec.tag_prefix)
        tag = release.get("tag_name")
        asset = _find_zip_asset(release, spec.asset_prefix)
        zip_url = asset["browser_download_url"]

        print(f"Downloading {asset['name']} from {tag}...")
        _download(zip_url, spec.zip_out)

        print(f"Extracting {spec.zip_out}...")
        _extract_zip(spec.zip_out, spec.extract_dir)

    mono_ttf = _find_file(src_dir / "mono", "IBMPlexMono-Regular.ttf", prefer_unhinted=False)
    sans_sc_ttf = _find_file(
        src_dir / "sans-sc", "IBMPlexSansSC-Regular.ttf", prefer_unhinted=True
    )

    shutil.copyfile(mono_ttf, Path("IBMPlexMono-Regular.ttf"))
    shutil.copyfile(sans_sc_ttf, Path("IBMPlexSansSC-Regular.ttf"))

    print("Prepared input TTFs:")
    print(f"- {mono_ttf} -> IBMPlexMono-Regular.ttf")
    print(f"- {sans_sc_ttf} -> IBMPlexSansSC-Regular.ttf")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
