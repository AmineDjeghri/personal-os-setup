hl.monitor({
    output = "DP-1",
    mode = "3840x2160@144.0",
    position = "1920x0",
    scale = 1.6666666,
    bitdepth = 10,
    cm = "auto", -- select "hdr" for HDR mode, or "auto"
    sdrbrightness = 1.5,      -- default is 1.0; try 1.2–2.0 until desktop looks normal
    sdrsaturation = 1.0,
    sdr_min_luminance = 0,
    sdr_max_luminance = 225   -- try values in the 200–400 range, matches your panel's SDR-mode brightness
})
hl.monitor({
    output = "DP-2",
    mode = "1920x1080@144.0",
    position = "0x173",
    scale = 1.0,
})
