local mainMod = "ALT"
local noctCall = "noctalia msg "
local launchPrefix = "uwsm app -- "

-------------------------------
---- WORKSPACES & MONITORS ----
-------------------------------

-- Window switching
hl.bind(mainMod .. " + CONTROL + Right", hl.dsp.focus({ direction = "right" }), { description = "Focus window to the right" })
hl.bind(mainMod .. " + CONTROL + Left",  hl.dsp.focus({ direction = "left" }),  { description = "Focus window to the left" })
hl.bind(mainMod .. " + CONTROL + Up",    hl.dsp.focus({ direction = "up" }),    { description = "Focus window above" })
hl.bind(mainMod .. " + CONTROL + Down",  hl.dsp.focus({ direction = "down" }),  { description = "Focus window below" })

-- Scroll through existing workspaces & monitors
hl.bind(mainMod .. " + mouse_up",   hl.dsp.focus({ workspace = "m-1" }), { description = "Focus previous workspace" })
hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "m+1" }), { description = "Focus next workspace" })

-- Special workspace (scratchpad)
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }), { description = "Move window to scratchpad" })
hl.bind(mainMod .. " + S",         hl.dsp.workspace.toggle_special("magic"),            { description = "Toggle scratchpad" })


-- Switch workspaces with mainMod + [0-9] and move window with mainMod + SHIFT + [0-9]
-- AZERTY/QWERTY independent: code:10 = & in azerty or 1 in qwerty, code:19 = à or 0 key
-- Skel's own "focus on monitor" ALT+1/2/3 keysym binds were dropped: they only fire on the
-- "us" half of the fr,us layout toggle and collide with this code:-based loop on the same key.
for workspace = 1, 10 do
    local keycode = 9 + workspace

    hl.bind(mainMod .. " + code:" .. keycode, hl.dsp.focus({ workspace = workspace }), { description = "Switch to workspace " .. workspace })
    hl.bind(mainMod .. " + SHIFT + code:" .. keycode, hl.dsp.window.move({ workspace = workspace }), { description = "Move window to workspace " .. workspace })
end

---------------------------
---- WINDOW MANAGEMENT ----
 ---------------------------


-----------------------
---- Exec commands ----
-----------------------

hl.bind(mainMod .. " + Q",           hl.dsp.window.close(), { description = "Close window" }) -- graceful close; freed up once terminal moved to ALT+T
-- ALT+C left unbound on purpose (see note below)
-- hl.bind(mainMod .. " + D",           hl.dsp.window.fullscreen({ mode = 1 }), { description = "Toggle maximize" })
hl.bind(mainMod .. " + F",           hl.dsp.window.fullscreen(), { description = "Toggle fullscreen" })
-- hl.bind(mainMod .. " + J",           hl.dsp.layout("togglesplit"), { description = "Toggle split orientation" }) -- dwindle only

-- ALT+Tab: hymission is active
hl.bind(mainMod .. " + Tab", function() hl.plugin.hymission.toggle("forceall") end, { description = "Toggle window overview" })

hl.bind(mainMod .. " + T",      hl.dsp.exec_cmd(launchPrefix .. TERMINAL), { description = "Open terminal" })
hl.bind(mainMod .. " + E",          hl.dsp.exec_cmd(launchPrefix .. FILE_MANAGER), { description = "Open file manager" })
hl.bind(mainMod .. " + W",          hl.dsp.exec_cmd(launchPrefix .. BROWSER), { description = "Open browser" })
hl.bind("CONTROL + SHIFT + Escape", hl.dsp.exec_cmd(launchPrefix .. TERMINAL .. " -e btop"), { description = "Open system monitor" })
hl.bind(mainMod .. " + G",          hl.dsp.exec_cmd(noctCall .. "settings-toggle"), { description = "Toggle Noctalia settings" })
-- ALT+Z intentionally left free: gpu-screen-recorder-ui grabs it globally (ShadowPlay-style
hl.bind(mainMod .. " + X",          hl.dsp.exec_cmd(noctCall .. "panel-toggle control-center"), { description = "Toggle control center" })
hl.bind(mainMod .. " + Space",      hl.dsp.exec_cmd("vicinae toggle"), { description = "Toggle app launcher" })
hl.bind(mainMod .. " + period",     hl.dsp.exec_cmd(noctCall .. "panel-toggle launcher /emo"), { description = "Open emoji picker" })
hl.bind(mainMod .. " + L",          hl.dsp.exec_cmd(noctCall .. "session lock"), { description = "Lock session" })
hl.bind(mainMod .. " + SHIFT + L",  hl.dsp.exec_cmd(noctCall .. "panel-toggle session"), { description = "Toggle power/session menu" }) -- power/session menu; skel's own "mainMod + ALT + C" bind for this collapses to "ALT + ALT + C" once mainMod=ALT, so it's rebound here instead
hl.bind(mainMod .. " + SHIFT + R",  hl.dsp.exec_cmd("hyprctl reload"), { description = "Reload Hyprland config" })

---------------------------
---- HARDWARE CONTROLS ----
---------------------------

-- Audio
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd(noctCall .. "volume-up"),   { description = "Volume up",      locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd(noctCall .. "volume-down"), { description = "Volume down",    locked = true, repeating = true })
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd(noctCall .. "volume-mute"), { description = "Mute volume",    locked = true })
hl.bind("XF86AudioMicMute",     hl.dsp.exec_cmd(noctCall .. "mic-mute"),    { description = "Mute microphone", locked = true })

-- Media
hl.bind("XF86AudioPlay",  hl.dsp.exec_cmd(noctCall .. "media toggle"),   { description = "Play/pause media",  locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd(noctCall .. "media toggle"),   { description = "Play/pause media",  locked = true })
hl.bind("XF86AudioNext",  hl.dsp.exec_cmd(noctCall .. "media next"),     { description = "Next track",        locked = true })
hl.bind("XF86AudioPrev",  hl.dsp.exec_cmd(noctCall .. "media previous"), { description = "Previous track",    locked = true })

-- Brightness
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd(noctCall .. "brightness-up"),   { description = "Brightness up",   locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd(noctCall .. "brightness-down"), { description = "Brightness down", locked = true, repeating = true })

-------------------
---- UTILITIES ----
-------------------

hl.bind("Print", hl.dsp.exec_cmd(noctCall .. "screenshot-fullscreen"), { description = "Screenshot (fullscreen)" })
hl.bind(mainMod .. " + Print", hl.dsp.exec_cmd(noctCall .. "screenshot-region"), { description = "Screenshot (region)" })

-- Theming and Wallpaper
hl.bind(mainMod .. " + SHIFT + W", hl.dsp.exec_cmd(noctCall .. "panel-toggle wallpaper"), { description = "Toggle wallpaper picker" })

-- Clipboard (Vicinae's clipboard history if installed, else Noctalia's clipboard panel)
hl.bind(mainMod .. " + V", hl.dsp.exec_cmd(CLIPBOARD), { description = "Open clipboard history" })

-- Notifications
hl.bind(mainMod .. " + A", hl.dsp.exec_cmd(noctCall .. "panel-toggle control-center notifications"), { description = "Toggle notifications" })
