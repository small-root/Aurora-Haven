#!/usr/bin/env bash
# install.sh — sets up Wallhaven auto-downloader + swww rotator as a user service + timer

set -e

USER_HOME="$HOME"
BIN_DIR="$USER_HOME/.local/bin"
SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"

# Ensure required directories exist
mkdir -p "$BIN_DIR"
mkdir -p "$SYSTEMD_USER_DIR"

# Copy the Python script into ~/.local/bin
SCRIPT_SRC="$(dirname "$0")/wallhaven_autorun.py"
SCRIPT_DEST="$BIN_DIR/wallhaven_autorun.py"
cp "$SCRIPT_SRC" "$SCRIPT_DEST"
chmod +x "$SCRIPT_DEST"

# Create wallhaven.service
cat > "$SYSTEMD_USER_DIR/wallhaven.service" <<EOF
[Unit]
Description=Wallhaven downloader & swww rotator (user)
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStartPre=/usr/bin/sleep 10
ExecStart=/usr/bin/env python3 $SCRIPT_DEST --service
Restart=on-failure
RestartSec=10

# Wayland and user env setup
Environment=WAYLAND_DISPLAY=wayland-1
Environment=XDG_RUNTIME_DIR=%t
Environment=PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin

[Install]
WantedBy=default.target
EOF

# Create wallhaven.timer
cat > "$SYSTEMD_USER_DIR/wallhaven.timer" <<EOF
[Unit]
Description=Periodic Wallhaven downloader and rotator

[Timer]
OnBootSec=45s
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF
pip3 install --user -r requirements.txt --break-system-packages
# Reload systemd user daemon and enable/start timer
systemctl --user daemon-reload
systemctl --user enable wallhaven.timer
systemctl --user start wallhaven.timer

echo "✅ Wallhaven auto-rotation service installed successfully!"
echo "→ Python script: $SCRIPT_DEST"
echo "→ Service + Timer: $SYSTEMD_USER_DIR"
echo "→ You can view status with: systemctl --user status wallhaven.service"
echo "ALSO MANUALLLY RUN THE PYTHON SCRIPT FOR FIRST TIME SETUP OFCOURSE"
