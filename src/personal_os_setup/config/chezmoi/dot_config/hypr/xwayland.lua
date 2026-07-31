-- XWayland scaling tradeoff for a mixed-DPI setup (DP-1 4K @ 1.5x, DP-2 1080p @ 1x):
-- force_zero_scaling renders XWayland apps at 1x and lets Hyprland upscale them, which
-- fixes blurry XWayland windows on the 4K/1.5x monitor but makes them render slightly
-- undersized on the 1080p/1x one. This is a global, single-scale switch — Hyprland has
-- no per-monitor XWayland scaling option, so there is no setting that fixes both monitors
-- at once. If XWayland blur or wrong-size windows come up again, this is the first place
-- to check and the tradeoff to re-weigh, not a bug to chase.

hl.config({
    xwayland = {
        force_zero_scaling = true,
    },
})
