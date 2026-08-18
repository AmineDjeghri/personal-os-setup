-- Hyprland 0.55+ Lua config.
-- Personal Hyprland configuration (modular, flat layout)
--
-- monitors.lua / workspaces.lua are generated with nwg-displays

TERMINAL     = "ghostty"
FILE_MANAGER = "dolphin"
BROWSER      = "helium-browser"
EDITOR       = "gnome-text-editor --new-window"

-- Clipboard history: Vicinae's clipboard command if installed, otherwise Noctalia's own clipboard panel
local function commandExists(path)
    local f = io.open(path, "r")
    if f then f:close() end
    return f ~= nil
end

CLIPBOARD = commandExists("/usr/bin/vicinae") and "vicinae cmd launch clipboard:history" or "noctalia msg panel-toggle clipboard"

-- App launcher: Vicinae if installed, otherwise Noctalia's own launcher panel
APP_LAUNCHER = commandExists("/usr/bin/vicinae") and "vicinae toggle" or "noctalia msg panel-toggle launcher"

-- Monitors
MONITOR1 = "DP-1"
MONITOR2 = "DP-2"
MONITOR3 = ""
PRIMARY_MONITOR = MONITOR1

-- Workspaces
NUM_WPM = 3 -- Number of workspaces per monitor (max 10); used by binds.lua's monitor-relative window-move bind

-- A bare require() throws on failure and aborts the rest of this file
local function requireModule(name)
    local ok, err = pcall(require, name)
    if not ok then
        print(name .. ".lua not loaded: " .. tostring(err))
    end
end

requireModule("colors")
requireModule("environment")
requireModule("decorations")
requireModule("animations")
requireModule("misc")
requireModule("xwayland")
requireModule("autostart")
requireModule("inputs")
requireModule("binds")
requireModule("hyprbars")
requireModule("windowrules")

local monitorsOk, monitorsErr = pcall(require, "monitors")
if not monitorsOk then
    print("monitors.lua not loaded, falling back to auto monitor placement: " .. tostring(monitorsErr))
end

local workspacesOk, workspacesErr = pcall(require, "workspaces")
if not workspacesOk then
    print("workspaces.lua not loaded, no workspace-to-monitor pinning applied: " .. tostring(workspacesErr))
end

-- For Noctalia Color templates
local noctaliaOk, noctalia = pcall(require, "noctalia")
if noctaliaOk then
    noctalia.apply_theme()
else
    print("noctalia.lua not loaded, skipping Noctalia border-color theme: " .. tostring(noctalia))
end
