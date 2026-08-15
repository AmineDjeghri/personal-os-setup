#!/usr/bin/env bash
# Forces Hyprland to re-commit DP-1's color-management state after suspend/resume.
# Problem happened only with HDR and not "auto" (SDR) mode

# See: https://github.com/hyprwm/Hyprland/issues/9724
# Called from noctalia/config.toml's [idle.behavior.lock-and-suspend] resume_command.

MONITORS_LUA="$HOME/.config/hypr/monitors.lua"

[ -f "$MONITORS_LUA" ] || exit 0

current_cm="$(sed -n 's/.*cm = "\([^"]*\)".*/\1/p' "$MONITORS_LUA" | head -n1)"
[ -n "$current_cm" ] || exit 0

if [ "$current_cm" = "hdr" ]; then
    bounce_cm="auto"
else
    bounce_cm="hdr"
fi

sed -i "s/cm = \"$current_cm\"/cm = \"$bounce_cm\"/" "$MONITORS_LUA"
hyprctl reload
sleep 0.3
sed -i "s/cm = \"$bounce_cm\"/cm = \"$current_cm\"/" "$MONITORS_LUA"
hyprctl reload
