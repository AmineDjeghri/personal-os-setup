# Windows 11 & WSL setup

![Windows WSL Terminal with taskbar](../images/windows_wsl_terminal_taskbar.png)

The image you are looking at is a screenshot of a WSL Ubuntu terminal in Windows 11. The top bar is an app called
GlazeWM.
You can follow this repository to get a similar setup.

**Table of Contents**
<!-- TOC -->
* [Windows 11 & WSL setup](#windows-11--wsl-setup)
  * [1. Windows account & configuration](#1-windows-account--configuration)
    * [1.1. Windows account](#11-windows-account)
    * [1.2. Windows configuration](#12-windows-configuration)
      * [🎧Audio settings](#audio-settings)
      * [🖥️ Monitor and Display Settings](#-monitor-and-display-settings)
  * [2. Software](#2-software)
  * [3. Coding using Linux (WSL) inside Windows](#3-coding-using-linux-wsl-inside-windows)
    * [3.1. Install WSL:](#31-install-wsl)
    * [3.2. Linux/WSL Setup - terminal, shell, Miniconda, CUDA & More:](#32-linuxwsl-setup---terminal-shell-miniconda-cuda--more)
      * [CUDA on WSL2](#cuda-on-wsl2)
    * [3.3. WSL2 Utilities, Tips & Tricks :](#33-wsl2-utilities-tips--tricks-)
    * [3.4. backup and restore WSL](#34-backup-and-restore-wsl)
    * [3.5. Uninstall WSL:](#35-uninstall-wsl)
  * [4. More (deprecated)](#4-more-deprecated)
<!-- TOC -->

Install the Personal-OS-Setup TUI [app](../../README.md#windows-11)

## 1. Windows account & configuration

### 1.1. Windows account

1. If you already have a key: activate windows with your key
2. If you don't have a key, you can buy one for a small price.
3. If you have a key in your old computer, you can use it in your new computer: If you didn't save the key in your
   account, you need to do this before resetting your old computer
    - On your old PC, check if the key is not an OEM by running `Slmgr /dli`
    - Get your license key (if you forgot the serial number, use software like :
    - Deactivate it in Windows terminal by using administrator mode with `slmgr /cpky`
    - Activate it on the new computer using `slmgr /ipk xxxxx-xxxxx-xxxxx-xxxxx-xxxxx`

### 1.2. Windows configuration

- 🔑 Save your key: Connect windows with your Microsoft/Outlook account to save and link the key to your account
- 📍 Activate localization on Windows (if you want to localize your device)
- 🔐 Activate bitlocker to encrypt your data (Exists only on Windows pro, education and enterprise edition)
- 🖥️ When placing an external monitor that runs 144HZ, make sure to activate the `144Hz` in display settings
- ⚠️ If you're using OneDrive, careful when you sync your Desktop and Windows specific folders, you can face some
  problems. My advice is to avoid syncing Windows default folders (like Desktop, Documents). Unsyc everything (Desktop,
  Documents...) Just use OneDrive as a cloud store like Google Drive. If you don't use it, you can uninstall it.
- 💤 Sleep mode with or without screen
  lock [here](https://consumer.huawei.com/en/support/content/en-us15592807/##:~:text=Click%20the%20Windows%20icon%20and,Screen%20and%20Sleep%20to%20Never)
- If you have a 3200mhz RAM, and it runs bellow this frequency, activate XMP profile in the BIOS
- Turn off usb ports and pc lights when in sleep mode in the BIOS

#### 🎧Audio settings
  - If you have Bluetooth and audio devices, you can sort them in audio settings → use as default for both audio and
    communications.
  - You can also deactivate some audio devices if the are unused in the audio settings. Check this [link](https://www.reddit.com/r/Windows10/comments/hcxksq/how_do_you_remove_an_unused_device_from_the_sound/)
  - Deactivate lowering communication sounds in advanced audio settings.

#### 🖥️ Monitor and Display Settings
  - **Change display settings** (refresh rate, resolution, scaling, etc.):
    - `Windows + I` → **System** → **Display** .  Or **Right-click Desktop** → **Display settings**
  - **🚀 Critical Step – Refresh Rate** :  Go to **Advanced display**. Select the **highest available refresh rate** from the dropdown
   - Optimize Overdrive: Avoid using the "Extreme" or "Ultra-fast" response time settings. These usually degrade performance.
   - Use the following to check the performance of your monitor, and read the instructions on the top of each test. Make sure to use the full screen mode.
   - Do not move your mouse between the area of the test and the rest of the screen because it will cause stuttering. You can move your mouse outside the area of the test. The best is to use the full screen mode of the test.
      - Ghosting: Visit https://testufo.com/ghosting and adjust your monitor's Overdrive (OD) settings until the UFO images look as clean and sharp as possible.
      - FPS: https://testufo.com/
      - Black Level Test: https://testufo.com/blacklevels
      - Local Dimming: https://testufo.com/localdimming
   - Color Calibration: When adjusting your monitor's RGB values, only adjust them down from the default (e.g., if you want more green, decrease red and blue). Increasing values beyond default reduces maximum brightness and can lower contrast on LCD screens.
   - Manage Brightness: High brightness causes eye strain and fatigue over long sessions, making it harder to spot enemies. Instead of maxing out brightness, use the Shadow Boost feature to brighten only dark areas.
     - Use Twinkle Tray to control brightness via the taskbar or keyboard shortcuts during gameplay.
   - HDR settings:
     - If your monitor supports HDR, make sure to activate it.
     - Keep the HDR brightness to the maximum value (or to 80% minimum). If you want to reduce the brightness, do it in the games or applications.
     - You can change the brightness of SDR content when HDR is enabled in the Windows HDR settings of your monitor, if it's too bright for you.
     - Use the Windows [HDR Calibration app](https://apps.microsoft.com/detail/9n7f2sm5d1lr?hl=fr-FR&gl=FR) to calibrate your monitor.
   - Bias Lighting: Place lights behind your monitor to improve perceived contrast and further reduce eye strain.
   - Monitor Latency: Use the Nvidia statistics overlay (Alt + Z) to track your PC latency.
   - GPU Utilization: System latency spikes when your GPU hits 100% utilization. To keep latency low, use an FPS limiter, lower graphics settings, or enable Nvidia Reflex to ensure you are not "GPU bound".
  - Full-screen games optimization: uncheck “disable fullscreen optimization” for the .exe. You will get a fast alt tab (only on the latest windows versions). Example: Make your way to the following file location on your desktop: C:
    \Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game. The goal here is to locate the
    CS2.exe file.
- 🧠 Multiple Monitor Logic:
    - Each monitor configuration has **its own saved settings**
    - **Single Monitor Setup**
      - Customize refresh rate and resolution
    - **Dual Monitor Setup**
      - You must re-adjust refresh rates for this configuration
      - Windows remembers these settings separately
    - **Triple Monitor Setup**
      - Each monitor must be configured individually again
    - 🔄 When switching back to a previous setup, **Windows automatically restores**
      - Use `Windows + P` to disconnect/extend/duplicate a monitor if you have multiple ones: (Windows + P) → Select the monitor → Next to identify, select the right option.
      - Select **Identify** to confirm monitor positions
      - For advanced setups, consider **DisplayFusion (paid)****** :
        - You can use DisplayFusion if you want to easily configure displays and monitors. For example, you can create a configuration to use two monitors, and a configuration to use only one and turn off the second, a configuration to use the tv only ...etc.
       - Display Fusion configurations are meant to be used when you don't need to turn off manually the monitors ...etc. So if you have a TV, no need to change the configuration from monitors to TV. You just need to turn off the monitors, and turn on the TV; Windows will recognize that there is a change in the displays and will use the TV.
       -  You can use DisplayFusion to easily create profiles for different configurations (e.g., a "Gaming" profile for one monitor, a "Work" profile for two, or a "Movie" profile for the TV).

- Windows UI/UX Tips:
    - Hide the Windows taskbar (right-click on the taskbar → taskbar settings→ taskbar behavior (at the bottom) →
      automatically hide the taskbar).
    - Pin some folders and drivers, Recycle Bin in the file explorer. Fast browsing: right-click on the file explorer in
      the taskbar to show the shortcut to the pinned folders.
    - Auto lock screen after x minutes of inactivity: search for `screen saver` in windows and select the number of
      minutes before your computer auto locks itself.
    - Show Files extensions: In File Explorer under View, in the Show/hide group, select the File name extensions check
      box.
    - You can change your power management options (when windows will be put to sleep, what happens when you close your
      laptop. Ect), performance vs normal usage.
    - You can convert a website to an application, for example, Google Agenda/ Netflix in Edge/Brave/Chrome, go to At
      the top right: More -> More Tools -> Create shortcut and check window mode, it will run like an app in your
      Windows desktop
    - Remove unnecessary programs, unnecessary icons from the start menu and add others like Maps, meteo & calendar
    - Deactivate startup programs that you don't need.
    - Always use the Windows search bar to search for functionalities, settings, apps, files, folders, and more. Even
      the deep settings are accessible from the search bar.
    - You can use PowerToys to search for files, folders, and more. It's faster than the Windows search bar but does not
      contain deep settings.
    - (Need to update) Disable mouse from waking up computer from sleep and allowing only the keyboard to do that:
    ```
    PS C:\Users\amine> ``powercfg /devicequery wake_armed``
    Périphérique clavier PIH
    Périphérique clavier PIH (001)
    Souris HID (001)
    Realtek PCIe 2.5GbE Family Controller
    Souris HID (002)
    Périphérique clavier PIH (004)
    Périphérique clavier PIH (005)

    PS C:\Users\amine> ``powercfg /devicedisablewake "Souris HID (001)"``
    PS C:\Users\amine> ``powercfg /devicedisablewake "Souris HID (002)"``
    ```
    If your mouse has some buttons, they will be registered as a keyboard, so you need also to disable them.

Other apps, websites and tips: (DEPRECATED)

- Take a look
  at [Windows 11 subreddit](https://www.reddit.com/r/Windows11/) & [Awesome Windows 11](https://github.com/awesome-windows11/windows11)
-

## 2. Software

Automatic installation of these apps is available with the Personal-OS-Setup TUI [app](../../README.md#windows-11)

For App configuration, check [apps_configuration_and_shorcuts.md](../apps/apps_configuration_and_shorcuts.md) —
see the [app availability & alternatives table](../apps/apps_configuration_and_shorcuts.md#app-availability--alternatives-across-oses)
for what's available on Windows vs. macOS/CachyOS and their alternatives.

For browser extensions, check [browser_extensions.md](../apps/awesome_websites_browser_extensions.md)

- Remember to sync your settings bookmarks...ect.
- Use two browsers / or two profiles: one for work and the other for personal use.
- **Agenda & Mail**: Google Calendar, Gmail
    - create an app shortcut with brave & add them to the taskbar it will act like an app in windows, and activate the
      notifications.
    - You can change the theme and prioritize stuff like notifications (all new emails), signature...etc.
    - Download their desktop notifications
      extensions: [Desktop notifications for Gmail ](https://chrome.google.com/webstore/detail/checker-plus-for-gmail/oeopbcgkkoapgobdbedcemjljbihmemj) & [Desktop notifications for Google calendar](https://chrome.google.com/webstore/detail/checker-plus-for-google-c/hkhggnncdpfibdhinjiegagmopldibha)
    - Make Brave the default apps in windows for mailto and agenda (Windows search bar -> type in `Default apps` then
      add brave to 'mail' & 'agenda.' Go to brave://settings/handlers and add gmail and agenda. Open now the gmail
      website and accept brave as the default app.
- WSL (Windows Subsystem for Linux) with Ubuntu 22.04 LTS. Check the WSL section below.

For dev-related websites (Gitmoji, Explainpaper, Detexify, Mathpix, Overleaf), check
[awesome_websites_browser_extensions.md](../apps/awesome_websites_browser_extensions.md#22-development-websites)


## 3. Coding using Linux (WSL) inside Windows

The most amazing thing about WSL (WSL2.0 exactly) is: You can run Linux in Windows without the need of a virtual
machine.

- It's a full Linux kernel running on Windows.
- You can install packages directly on Linux
- Virtualization overhead is not noticeable, full integration between guest and host os's, you can run binaries compiled
  for MS Windows from linux.
- You can navigate and communicate between ubuntu and windows as Ubuntu acts like a disk drive.
- You can install conda environment in ubuntu, use GPU, use pycharm on windows to connect to WSL conda env and more.
- Do not code in both OS, use, for example, pycharm or vscode on windows with a conda environment installed on WSL. The
  best thing is to combine the power of Windows with WSL.

### 3.1. Install WSL:
- Automatic installation of WSL available with the Personal-OS-Setup TUI [app](../../README.md#linux--wsl2--macos)
- Run the script in Windows Terminal
- Or manual installation: Run this command in PowerShell ``` wsl --install ```. You can also select the drive where you want to install it instead of the default 'C' drive and this is what I recommand doing.

- Restart your computer
- When installing WSL, it comes with Ubuntu (you can always install other distibutions from the microsoft store)
- You have different options to run Ubuntu :
    - From windows search bar (and select ubuntu or WSL for the default distro)
    - Running `ubuntu` inside Windows terminal
    - Running `wsl` inside Windows terminal to run the default distro
    - Running Windows terminal and choosing ubuntu in the terminal tab section.
    - If it's not there, make sure you have correctly installed WSL by searching wsl in your Windows search bar &
      running it.
- If you have Nvidia GPU & the nvidia driver is installed on Windows, you can run `nvidia-smi` on Linux. No need to
  install the nvidia Driver again on Linux.
- You can choose a default terminal when you open Windows Terminal (for example, wsl): go to settings -> default
  profile -> select the terminal you want to open by default.
- If you have ubuntu terminal: you can add `C:\Windows\system32\wsl.exe -d Ubuntu` in the ubuntu profile to open ubuntu
  by default in the directory.
- Add systemd to wsl.conf if it's not there: run `sudo vim /etc/wsl.conf` inside linux then paste the following code:

 ```
[boot]
systemd=true
 ```

- Restart the terminal and run `systemctl list-unit-files --type=service` in WSL to see some processes running.
- If you have an ssh key in windows in `C:\Users\%UserProfile%\.ssh`, copy it (both keys) to linux `~/.ssh` folder or
  using Windows file explorer or power toys `\\wsl$\Ubuntu\home\%USERNAME%\.ssh` and change its rights
  using: `chmod 600 ~/.ssh/id_rsa` and `chmod 600 ~/.ssh/id_rsa.pub`.
- If you don't have an SSH key, generate a new SSH key using: `ssh-keygen -t rsa` inside linux (when prompted, you can
  enter an empty password).
- Jump to the next section to configure your WSL /Ubuntu.

### 3.2. Linux/WSL Setup - terminal, shell, Miniconda, CUDA & More:

After installing WSL, you have now ubuntu running inside windows.
Follow these guides containing an automated script to customize your terminal,
shell, install Miniconda, CUDA, and more:

- [1. Linux Setup Guide](../linux/README.md): A set of configurations, dotfiles and a script to
  automatically set up a powerful terminal & shell utilities(zsh, fzf...), themes like Powerlvl10k, Conda, GPU drivers,
  and more on Linux/WSL2.
- [2. Windows, WSL & apps settings/tips](../apps/apps_configuration_and_shorcuts)
- [3. Cuda & Pytorch installation inside conda](https://github.com/AmineDjeghri/ai-on-premise-project-template/blob/main/cuda_pytorch_install.md)

#### CUDA on WSL2

> **Important:** You must have the NVIDIA GPU driver already installed on Windows. Verify with `nvidia-smi` in PowerShell.
> **Do NOT install any NVIDIA GPU Linux driver inside WSL 2** — the Windows host driver is used directly.

Follow the official CUDA WSL guide:
[CUDA Support for WSL 2](https://docs.nvidia.com/cuda/wsl-user-guide/index.html#cuda-support-for-wsl-2)


### 3.3. WSL2 Utilities, Tips & Tricks :

- Take a look at [awesome-wsl](https://github.com/sirredbeard/awesome-wsl)
- A surprising number of Linux GUI apps can run on WSL. GUI applications are officially supported on WSL2 and referred
  to as [WSLg](https://github.com/microsoft/wslg)(No installation required).
- [Windows Hello on WSL]( https://github.com/nullpo-head/WSL-Hello-sudo)
-

- Find WSL path: `\\wsl$\Ubuntu\home` or `\\wsl$\Ubuntu` then ping it in Windows Explorer's sidebar.
- You can use `wslpath` command to convert a Windows path to wsl path: `wslpath 'C:\Users\AmineDjeghri\Desktop\'`
- Folder size for current directory: `du -h`, `du -h | sort -h`. For specific directory: `du -h /folder`
- wsl disk usage: `df -h` look on the right column 'Mounted on,' or `df -h /mnt/wslg/distro`
- Reclaim disk space :
    - it requires docker Dashboard for WSL2, and 2 hyper V params in the Control Panel.
    - Install this https://superuser.com/a/1307442/769637 install the Hyper-V Platform | Hyper-V Services part, too +
      restart)
    - in Administrator Mode: `wsl --shutdown`
      then `cd 'C:\Users\%UserProfile%\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu_79rhkp1fndgsc\LocalState'`
      then `optimize-vhd -Path .\ext4.vhdx -Mode full`
    - for more information, check this:
      these https://askubuntu.com/a/1380274 + https://github.com/microsoft/WSL/issues/4699 +
- To change the default distro or fix the `wsl` command to start your distro from powershell not working, you can do:

```sh
wsl --list
wsl --setdefault <name_of_your_distro>
```

- You can enter ubuntu with different ways: clicking on Shortcut (Orange), or running 'wsl' in Windows terminal, or
  running 'ubuntu' in Windows terminal, or selecting the right profile in the tab in Windows terminal.
- To open Ubuntu terminal from current location: go to Windows terminal -> parameters -> profiles -> ubuntu -> command
  line (under name) and change it to `ubuntu run`.
- Now, go to desktop and right-click to open a Windows terminal, run 'wsl'; you should see that ubuntu started from the
  current location.
- (pycharm) Use WSL/ubuntu as the default terminal in pycharm: `settings -> tools -> terminal` and put in a shell
  path: `ubuntu run`
- (pycharm) Add WSL conda interpreter in Pycharm (add interpreter -> WSL -> conda) and select the global
  conda: `/home/amine/miniconda3/bin/conda`. Then click on load environments, and it will automatically detect all the
  conda envs.

### 3.4. backup and restore WSL

You can export wsl image after finishing all the steps to save it in case you move to a new computer :

- wsl --terminate ubuntu
- wsl --shutdown
- wsl --export Ubuntu E:\ubuntu.tar
- [source 1](https://www.xda-developers.com/how-back-up-restore-wsl/)

### 3.5. Uninstall WSL:

Uninstall all distributions & WSL from the control panel & open Windows Features, then turn on (check) Windows Subsystem
for Linux. Restart your computer.

## 4. More (deprecated)

- Add more Desktop icons (PC, Downloads...): Personalization->themes->desktop icon settings
- Use Quiet Hours and add only the applications that you want them to send you a notification, (Brave will still send
  you notifications to get BAT, but it will never appear)
- **Windows partition**: use the window partition integrated software to create, delete or format partitions
- If you consider buying a computer with a GPU for Deep Learning, choose a computer with an NVIDIA GPU that supports
  CUDA (preferably > RTX 2000 series).

- Wifi & Router 5ghz:
    - Deactivate WPS
    - Make your Wi-Fi invisible,
    - Choose 5ghz over 2.4ghz: if your device is connected to a Wi-Fi, and it keeps switching between 5ghz and 2.4ghz do
      the following:
    - If it's your Wi-Fi: split your Wi-Fi into 2 access points, one for 5Ghz and the other for 2.4Ghz. After that make
      your PC connect to the 5Ghz one only
    - If it's not your Wi-Fi (hotel/work Wi-Fi) and you have an ethernet port, you can always plug a router (example,
      HONOR ROUTER 3 WI-FI 6) and have your own private network. You can split the Wi-Fi into 2 access points like I
      mentioned it in the section above.
