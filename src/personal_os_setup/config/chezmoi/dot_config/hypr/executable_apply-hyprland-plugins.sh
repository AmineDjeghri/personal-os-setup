#!/usr/bin/env bash
# Loads already-built Hyprland plugins (hyprctl plugin load, no sudo) and re-applies
# their hl.plugin.<name> lua config blocks.
#
# Shared by two trigger points so the plugin list only lives in one place:
#   - run_after_check-hyprland-plugins.sh.tmpl (chezmoi apply, after a dotfiles sync)
#   - autostart.lua's hyprland.start hook (every fresh Hyprland session)
set -eu

script_name="apply-hyprland-plugins.sh"
notify() { command -v notify-send >/dev/null 2>&1 && notify-send "$1" "[$script_name] $2"; }

command -v hyprctl >/dev/null 2>&1 || exit 0

if ! command -v hyprpm >/dev/null 2>&1; then
  echo "hyprpm not found, skipping Hyprland plugin check"
  notify "Hyprland plugins" "hyprpm not found, skipped"
  exit 0
fi

hyprpm_cache="/var/cache/hyprpm/$(id -un)"

plugin_is_loaded() {
  hyprctl plugin list 2>/dev/null | grep -q "^Plugin $1 by"
}

# To track a new plugin, add a "name repo_url" entry here.
plugins=(
  "hymission https://github.com/gfhdhytghd/hymission"
  "hyprbars https://github.com/hyprwm/hyprland-plugins"
)

missing=0
enabled_names=""
for entry in "${plugins[@]}"; do
  set -- $entry
  plugin_name="$1"
  repo_url="$2"
  repo_name="${repo_url##*/}"
  so_path="$hyprpm_cache/$repo_name/$plugin_name.so"

  if [ ! -f "$so_path" ]; then
    echo "$plugin_name not built -- run 'hyprpm add $repo_url' in a terminal, then rerun to load it" >&2
    missing=$((missing + 1))
    continue
  fi

  if ! plugin_is_loaded "$plugin_name"; then
    load_err=$(hyprctl plugin load "$so_path" 2>&1 >/dev/null) || true
  fi

  if plugin_is_loaded "$plugin_name"; then
    enabled_names="${enabled_names:+$enabled_names, }$plugin_name"
  else
    echo "$plugin_name is built but 'hyprctl plugin load' failed: ${load_err:-no output captured}" >&2
    echo "  hyprctl plugin load $so_path" >&2
    missing=$((missing + 1))
  fi
done

# Re-applies lua `if hl.plugin.<name> then` blocks after a (hot-)load -- no sudo needed.
for entry in "${plugins[@]}"; do
  set -- $entry
  plugin_name="$1"
  if plugin_is_loaded "$plugin_name"; then
    hyprctl eval "hl.config({ plugin = { $plugin_name = { enabled = false } } })" >/dev/null 2>&1 || true
    hyprctl eval "hl.config({ plugin = { $plugin_name = { enabled = true } } })" >/dev/null 2>&1 || true
  fi
done

if [ "$missing" -eq 0 ]; then
  notify "Hyprland plugins" "$enabled_names already enabled"
else
  notify "Hyprland plugins" "$missing plugin(s) not built/loaded -- see logs for the command, then rerun"
fi
