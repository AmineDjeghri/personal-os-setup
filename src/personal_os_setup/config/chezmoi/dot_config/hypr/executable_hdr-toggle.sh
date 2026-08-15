#!/usr/bin/env bash
# Actually switches DP-1 between HDR and auto/SDR mode
# Meant to be wired to a Noctalia Control Center.

MONITORS_LUA="$HOME/.config/hypr/monitors.lua"

[ -f "$MONITORS_LUA" ] || exit 0

current_cm="$(sed -n 's/.*cm = "\([^"]*\)".*/\1/p' "$MONITORS_LUA" | head -n1)"
[ -n "$current_cm" ] || exit 0

if [ "$current_cm" = "hdr" ]; then
    new_cm="auto"
else
    new_cm="hdr"
fi

sed -i "s/cm = \"$current_cm\"/cm = \"$new_cm\"/" "$MONITORS_LUA"
hyprctl reload

if [ "$new_cm" = "hdr" ]; then
    notify-send "HDR" "Enabled"
else
    notify-send "HDR" "Disabled"
fi
