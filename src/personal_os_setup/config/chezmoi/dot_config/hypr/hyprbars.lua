-- Hyprbars (glassy Catppuccin titlebar), loaded via hyprpm

if hl.plugin.hyprbars then

  hl.config({
    plugin = {
      hyprbars = {
        bar_height = 28,

        -- Glassy Catppuccin Mocha look
        bar_color = "rgba(313244dd)",
        bar_blur = true,

        bar_title_enabled = true,
        bar_text_size = 11,

        bar_part_of_window = true,
        bar_precedence_over_border = true,

        -- Double click title bar = float
        on_double_click = "hyprctl dispatch 'hl.dsp.window.float({ action = \"toggle\" })'",
      },
    },
  })

  -- Close button
  hl.plugin.hyprbars.add_button({
    bg_color = "rgba(f38ba8ff)",
    fg_color = "rgba(1e1e2eff)",
    size = 14,
    icon = "󰅖",
    action = "hyprctl dispatch 'hl.dsp.window.close()'",
  })

  -- Maximize button
  hl.plugin.hyprbars.add_button({
    bg_color = "rgba(f9e2afff)",
    fg_color = "rgba(1e1e2eff)",
    size = 14,
    icon = "󰐘",
    action = [[hyprctl dispatch 'hl.dsp.window.fullscreen({ mode = "maximized", action = "toggle" })']],
  })

  -- Minimize
  hl.plugin.hyprbars.add_button({
    bg_color = "rgba(a6e3a1ff)",
    fg_color = "rgba(1e1e2eff)",
    size = 14,
    icon = "󰖰",
    action = [[hyprctl dispatch 'hl.dsp.window.move({workspace = "special:minimized" })']],
  })

end
