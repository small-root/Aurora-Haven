# Aurora-Haven
A minimal, automated wallpaper daemon for Wayland compositors.
AuroraHAVEN fetches fresh wallpapers from Wallhaven.cc 
It runs quietly in the background via a user-level systemd timer — refreshing your desktop every few hours while keeping things minimal, fast, and offline-friendly.

**Features**
============

=> Downloads and rotates wallpapers from Wallhaven automatically.
=> Smart caching : skips already downloaded images. (Just a buzzword for if exists logic :) 
=> Works offline using already existing wallpaper set.
=> Fully Wayland-native with swww.
=> Autostarts on login, startup, reboot.
=> Written in pure Python + Bash, no bloat, no crap.

[X] Quick Setup [X]

git clone https://github.com//Aurora-Haven.git
cd Aurora-Haven
chmod +x install.sh wallhaven_autostart.py
bash install.sh
