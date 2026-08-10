-- Hyprland 0.55+ Lua config.
-- Personal Hyprland configuration (modular, flat layout)
--
-- monitors.lua / workspaces.lua are generated with nwg-displays

require("variables")
require("colors")
require("environment")
require("decorations")
require("animations")
require("misc")
require("xwayland")
require("autostart")
require("binds")
require("hyprbars")
require("windowrules")

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

-- For Noctalia Color templates
require("noctalia").apply_theme()
