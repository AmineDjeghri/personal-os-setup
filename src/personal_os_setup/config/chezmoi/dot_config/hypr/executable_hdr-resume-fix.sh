#!/usr/bin/env bash
# Forces Hyprland to re-commit DP-1's HDR state after suspend/resume.
# A same-value cm="hdr" reapply is a no-op (confirmed live) -- must be a real value
# transition (auto -> hdr) to force Hyprland to actually redo the DRM commit.
# See: https://github.com/hyprwm/Hyprland/issues/9724
# Called from noctalia/config.toml's [idle.behavior.lock-and-suspend] resume_command.

MONITORS_LUA="$HOME/.config/hypr/monitors.lua"

[ -f "$MONITORS_LUA" ] || exit 0

sed -i 's/cm = "hdr"/cm = "auto"/' "$MONITORS_LUA"
hyprctl reload
sleep 0.3
sed -i 's/cm = "auto"/cm = "hdr"/' "$MONITORS_LUA"
hyprctl reload
