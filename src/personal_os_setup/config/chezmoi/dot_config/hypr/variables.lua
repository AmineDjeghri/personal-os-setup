-- Hyprland default apps

TERMINAL     = "ghostty"
FILE_MANAGER = "dolphin"
BROWSER      = "helium-browser"
EDITOR       = "gnome-text-editor --new-window"
CALCULATOR   = "gnome-calculator"

-- Clipboard history: Vicinae's clipboard command if installed, otherwise Noctalia's own clipboard panel
local function commandExists(path)
    local f = io.open(path, "r")
    if f then f:close() end
    return f ~= nil
end

CLIPBOARD = commandExists("/usr/bin/vicinae") and "vicinae cmd launch clipboard:history" or "noctalia msg panel-toggle clipboard"

-- Monitors
MONITOR1 = "DP-1"
MONITOR2 = "DP-2"
MONITOR3 = ""
PRIMARY_MONITOR = MONITOR1

-- Workspaces
NUM_WPM = 3 -- Number of workspaces per monitor (max 10); used by binds.lua's monitor-relative window-move bind
