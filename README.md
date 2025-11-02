# Aurora-Haven

A minimal, automated wallpaper daemon for **Wayland compositors**.  
Aurora-Haven fetches fresh wallpapers from [Wallhaven.cc](https://wallhaven.cc)  
and runs quietly in the background via a user-level `systemd` timer —  
refreshing your desktop every few hours while keeping things minimal, fast, and offline-friendly.

---

## Features

- Downloads and rotates wallpapers from Wallhaven automatically  
- Smart caching — skips already downloaded images (buzzword for simple “if exists” logic :)  
- Works offline using the existing wallpaper set  
- Fully Wayland-native with [`swww`](https://github.com/LGFae/swww)  
- Autostarts on login, reboot, or startup  
- Written in pure Python and Bash — no bloat, no unnecessary dependencies  

---

## Quick Setup

```bash
git clone https://github.com/<your-username>/Aurora-Haven.git
cd Aurora-Haven
chmod +x install.sh wallhaven_autorun.py
bash install.sh
