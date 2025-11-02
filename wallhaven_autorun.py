#!/usr/bin/env python3
"""
wallhaven_autorun.py (resilient version)
- If the Wallhaven API cannot be reached (offline, timeout, etc.), the script skips
  downloads and still rotates existing wallpapers.
"""

from pathlib import Path
import requests
import json
import time
import sys
from subprocess import run
import argparse
import shutil
import socket

# ---------------- CONFIG ----------------
API_BASE = "https://wallhaven.cc/api/v1/search"
ROOT_DIR = Path.home() / "Pictures" / "Wallhaven"
CONFIG_DIR = Path.home() / ".config" / "wallswitch"
CONFIG_FILE = CONFIG_DIR / "config.json"
PAGE_TRACKER = CONFIG_DIR / "pages.json"

PER_PAGE = 24
PER_RUN_DOWNLOAD = 15
FOLDER_CAP = 150
MAX_PAGE_TRIES = 500
DEFAULT_CATEGORIES = "111"
DEFAULT_PURITY = "100"
SORTING = "date_added"
ORDER = "desc"
# -----------------------------------------

def ensure_dirs():
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))

def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Quick connectivity check (DNS server)."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def get_config_interactive():
    print("Interactive setup — set or change your wallpaper settings.")
    term = input("Search term (e.g. anime, nature) [leave empty to keep existing]: ").strip()
    print("Categories: choose which categories to include (3-digit flags, general+anime+people):")
    cats = input(f"Categories [default {DEFAULT_CATEGORIES}]: ").strip()
    interval_raw = input("Rotation interval seconds [default 10]: ").strip()
    try:
        interval = int(interval_raw) if interval_raw else 10
    except Exception:
        interval = 10
    return term, (cats if cats else DEFAULT_CATEGORIES), interval

def api_fetch_page(term, page, categories, purity=DEFAULT_PURITY):
    params = {
        "q": term,
        "categories": categories,
        "purity": purity,
        "sorting": SORTING,
        "order": ORDER,
        "page": page,
        "per_page": PER_PAGE
    }
    resp = requests.get(API_BASE, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", [])

def download_image(url, dest: Path):
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in r.iter_content(8192):
                if chunk:
                    fh.write(chunk)

def collect_and_download(term, folder: Path, start_page: int, categories: str, per_run_limit: int):
    existing_files = {p.name for p in folder.iterdir() if p.is_file()}
    downloaded = 0
    page = start_page
    pages_consumed = 0
    tries = 0

    if not check_internet():
        print("[!] No internet connection detected — skipping download phase, rotating existing wallpapers instead.")
        return 0, 0, start_page

    while downloaded < per_run_limit and tries < MAX_PAGE_TRIES:
        tries += 1
        if len(existing_files) >= FOLDER_CAP:
            break
        try:
            results = api_fetch_page(term, page, categories)
        except requests.RequestException as e:
            print(f"[!] Network/API error while fetching page {page}: {e}")
            break

        pages_consumed += 1
        if not results:
            page += 1
            continue

        for item in results:
            if downloaded >= per_run_limit or len(existing_files) >= FOLDER_CAP:
                break
            img_url = item.get("path")
            if not img_url:
                continue
            fname = img_url.split("/")[-1]
            if fname in existing_files:
                continue
            dest = folder / fname
            try:
                print(f"[↓] Downloading {fname} (page {page}) ...")
                download_image(img_url, dest)
                existing_files.add(fname)
                downloaded += 1
            except Exception as e:
                print(f"[!] Failed to download {fname}: {e}")
                if dest.exists():
                    dest.unlink(missing_ok=True)
                continue

        page += 1

    return downloaded, pages_consumed, page

def rotate_with_swww(folder: Path, interval: int):
    images = sorted([p for p in folder.iterdir() if p.is_file()])
    if not images:
        print("[!] No images available to rotate. Exiting.")
        return
    print(f"[*] Rotating {len(images)} images every {interval}s using swww.")
    try:
        while True:
            for img in images:
                print(f"[>] Setting {img.name}")
                run(["swww", "img", str(img)], check=False)
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Rotation stopped by user.")

def wait_for_hyprland_or_swww(timeout=60):
    import shutil as sh
    start = time.time()
    while True:
        now = time.time()
        if sh.which("swww"):
            try:
                r = run(["pgrep", "-x", "Hyprland"], check=False)
                if r.returncode == 0:
                    return True
                r2 = run(["pgrep", "-f", "Hyprland"], check=False)
                if r2.returncode == 0:
                    return True
            except Exception:
                pass
        if now - start > timeout:
            print("[!] Timeout waiting for Hyprland/swww. Proceeding anyway.")
            return False
        time.sleep(1)

def interactive_mode(args):
    cfg = load_json(CONFIG_FILE, {})
    term, cats, interval = get_interactive_inputs_from_user(cfg)
    cfg_changed = False
    if term:
        cfg["search_term"] = term
        cfg_changed = True
    if cats:
        cfg["categories"] = cats
        cfg_changed = True
    cfg["rotation_interval"] = interval
    cfg["per_run_download"] = PER_RUN_DOWNLOAD
    cfg["folder_cap"] = FOLDER_CAP
    if cfg_changed:
        print("[*] Saved new configuration.")
    save_json(CONFIG_FILE, cfg)

    ensure_dirs()
    folder = ROOT_DIR / cfg["search_term"]
    folder.mkdir(parents=True, exist_ok=True)
    pages = load_json(PAGE_TRACKER, {})
    start_page = int(pages.get(cfg["search_term"], 1))

    downloaded, pages_used, next_page = collect_and_download(
        cfg["search_term"], folder, start_page, cfg.get("categories", DEFAULT_CATEGORIES), PER_RUN_DOWNLOAD
    )
    print(f"[*] Downloaded {downloaded} new images (checked {pages_used} pages).")
    pages[cfg["search_term"]] = next_page
    save_json(PAGE_TRACKER, pages)

    wait_for_hyprland_or_swww(timeout=30)
    rotate_with_swww(folder, cfg["rotation_interval"])

def get_interactive_inputs_from_user(existing_cfg):
    print("---- Manual run (interactive) ----")
    curr_term = existing_cfg.get("search_term")
    if curr_term:
        print(f"Current search term: {curr_term}")
    term = input("Enter new search term (leave empty to keep current): ").strip()
    if not term and curr_term:
        term = curr_term
    curr_cats = existing_cfg.get("categories", DEFAULT_CATEGORIES)
    print(f"Current categories flags: {curr_cats}")
    cats = input("Categories flags [leave empty to keep current]: ").strip() or curr_cats
    curr_interval = existing_cfg.get("rotation_interval", 10)
    interval_raw = input(f"Rotation interval seconds (current {curr_interval}) [enter to keep]: ").strip()
    if interval_raw:
        try:
            interval = int(interval_raw)
        except Exception:
            interval = curr_interval
    else:
        interval = curr_interval
    return term, cats, interval

def service_mode(args):
    cfg = load_json(CONFIG_FILE, {})
    if "search_term" not in cfg:
        print("[!] No search_term configured. Run the script manually once to configure.")
        sys.exit(1)

    search_term = cfg["search_term"]
    categories = cfg.get("categories", DEFAULT_CATEGORIES)
    rotation_interval = int(cfg.get("rotation_interval", 10))
    per_run = int(cfg.get("per_run_download", PER_RUN_DOWNLOAD))
    cap = int(cfg.get("folder_cap", FOLDER_CAP))

    ensure_dirs()
    folder = ROOT_DIR / search_term
    folder.mkdir(parents=True, exist_ok=True)

    pages = load_json(PAGE_TRACKER, {})
    start_page = int(pages.get(search_term, 1))
    current_count = len([p for p in folder.iterdir() if p.is_file()])

    if current_count < cap:
        print(f"[*] Folder has {current_count}/{cap} images. Attempting to download up to {per_run} new images.")
        downloaded, pages_used, next_page = collect_and_download(search_term, folder, start_page, categories, per_run)
        print(f"[*] Downloaded {downloaded} new images (checked {pages_used} pages).")
        pages[search_term] = next_page
        save_json(PAGE_TRACKER, pages)
    else:
        print(f"[*] Folder has {current_count} images (>= cap {cap}) — skipping download.")

    wait_for_hyprland_or_swww(timeout=60)
    rotate_with_swww(folder, rotation_interval)

def main():
    parser = argparse.ArgumentParser(description="Wallhaven auto-downloader + swww rotator (resilient version)")
    parser.add_argument("--service", action="store_true", help="Run in service (non-interactive) mode.")
    parser.add_argument("--interactive", action="store_true", help="Force interactive mode.")
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_json(CONFIG_FILE, {})
    if not cfg:
        cfg = {
            "search_term": "",
            "categories": DEFAULT_CATEGORIES,
            "rotation_interval": 10,
            "per_run_download": PER_RUN_DOWNLOAD,
            "folder_cap": FOLDER_CAP
        }
        save_json(CONFIG_FILE, cfg)

    if args.interactive:
        interactive_mode(args)
    elif args.service:
        service_mode(args)
    else:
        if sys.stdin.isatty():
            interactive_mode(args)
        else:
            service_mode(args)

if __name__ == "__main__":
    main()
