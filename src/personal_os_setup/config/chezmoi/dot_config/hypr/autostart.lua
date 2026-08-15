-- Auto-start config

hl.on("hyprland.start", function ()
    hl.exec_cmd("dbus-update-activation-environment --systemd --all")
    hl.exec_cmd("systemctl --user start hyprpolkitagent")
    hl.exec_cmd("kded6")
    hl.exec_cmd("gnome-keyring-daemon --start --components=pkcs11,secrets,ssh")
    hl.exec_cmd("udiskie --tray")
    hl.exec_cmd("vicinae server")
    hl.exec_cmd("noctalia")
    hl.exec_cmd("xhost +SI:localuser:root")
    hl.exec_cmd("hyprpm reload")
    hl.exec_cmd("XDG_MENU_PREFIX=arch- kbuildsycoca6")
end)
