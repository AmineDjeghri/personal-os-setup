-- Look and feel configuration

-- Border/group colors are intentionally not set here: require("noctalia").apply_theme()
-- runs last in hyprland.lua and unconditionally overwrites general.col/group.col/
-- group.groupbar.col with Noctalia's wallpaper-derived palette, so anything set here
-- would never actually render.
hl.config({
    general = {
        gaps_in = 3,
        gaps_out = 8,
        border_size = 2,
        extend_border_grab_area = 10,
        resize_on_border = true,
    },
    decoration = {
        dim_special = 0.3,
        rounding = 10,
        active_opacity = 0.95,
        inactive_opacity = 0.85,
        fullscreen_opacity = 1,
        blur = {
            size = 5,
            passes = 4,
            special = true,
        },
    },
})
