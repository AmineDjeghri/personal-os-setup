-- Hyprland 0.55+ Lua config.
-- Personal Hyprland configuration (modular, flat layout)
--
-- monitors.lua / workspaces.lua are generated with nwg-displays

require("config/variables")
require("config/colors")
require("config/environment")
require("config/decorations")
require("config/animations")
require("config/misc")
require("config/xwayland")
require("config/autostart")
require("config/inputs")
require("config/binds")
require("config/hyprbars")
require("config/windowrules")

local monitorsOk, monitorsErr = pcall(require, "config/monitors")
if not monitorsOk then
    print("monitors.lua not loaded, falling back to auto monitor placement: " .. tostring(monitorsErr))
end

local workspacesOk, workspacesErr = pcall(require, "config/workspaces")
if not workspacesOk then
    print("workspaces.lua not loaded, no workspace-to-monitor pinning applied: " .. tostring(workspacesErr))
end

-- For Noctalia Color templates
local noctaliaOk, noctalia = pcall(require, "config/noctalia")
if noctaliaOk then
    noctalia.apply_theme()
else
    print("noctalia.lua not loaded, skipping Noctalia border-color theme: " .. tostring(noctalia))
end
