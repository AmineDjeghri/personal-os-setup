# Home server (Ubuntu Server, KVM, Home Assistant OS)

<!-- TOC -->
* [Home server (Ubuntu Server, KVM, Home Assistant OS)](#home-server-ubuntu-server-kvm-home-assistant-os)
  * [Ubuntu Server 24.04](#ubuntu-server-2404)
    * [Setup](#setup)
    * [First checks / updates](#first-checks--updates)
    * [Lid closed (Laptop)](#lid-closed-laptop)
  * [Home Assistant](#home-assistant)
    * [Virtualization](#virtualization)
    * [Install KVM (Kernel-based Virtual Machine) and libvirt](#install-kvm-kernel-based-virtual-machine-and-libvirt)
      * [Create a bridge configuration](#create-a-bridge-configuration)
    * [Home Assistant OS in a VM](#home-assistant-os-in-a-vm)
      * [inside HA in your browser or mobile app:](#inside-ha-in-your-browser-or-mobile-app)
    * [2. Accessing HAOS from outside your local network  — Cloudflare Tunnel Setup](#2-accessing-haos-from-outside-your-local-network--cloudflare-tunnel-setup)
        * [1️⃣ Basic Information (Top Section)](#1-basic-information-top-section)
        * [2️⃣ Add Public Hostname (IMPORTANT)](#2-add-public-hostname-important)
        * [3️⃣ Browser Rendering Settings](#3-browser-rendering-settings)
        * [4️⃣ Policies (MOST IMPORTANT PART)](#4-policies-most-important-part)
        * [5️⃣ (Optional) Add a Second Policy – Emergency Lockdown](#5-optional-add-a-second-policy--emergency-lockdown)
        * [6️⃣ Login Methods](#6-login-methods)
        * [Go back to the previous page to see the policies](#go-back-to-the-previous-page-to-see-the-policies)
        * [7️⃣ Save the Application ✅](#7-save-the-application-)
      * [Activate MFA](#activate-mfa)
    * [Home Assistant devices, add-ons, and integrations](#home-assistant-devices-add-ons-and-integrations)
      * [Matter over Wi-Fi](#matter-over-wi-fi)
      * [Matter over Thread and Zigbee devices](#matter-over-thread-and-zigbee-devices)
    * [Apps / Add-ons](#apps--add-ons)
    * [Integrations](#integrations)
    * [Dashboard & Cards](#dashboard--cards)
    * [Automations, Scenes, Script, Helpers and Entities](#automations-scenes-script-helpers-and-entities)
  * [AdGuard Home address naming resolution using the router (Freebox)](#adguard-home-address-naming-resolution-using-the-router-freebox)
* [todo:](#todo)
<!-- TOC -->


## Ubuntu Server 24.04

### Setup

- Set up an Ubuntu Server on a laptop.
  - You  better have Ethernet connection. If you only have wifi, buy a usb  ethernet adapter. It's worth it and you will be able to use the bridge mode which is not available with wifi.
  - boot up ubuntu from an usb drive, select the language, keyboard layout, and timezone. In the network section, select the Ethernet connection, an IP 192.168.x.x will be assigned.
  - Wait for mirror to be configured.
  - Assign some partitions : `ext4` 100GB for `/` and some space for var/lib. `/var/lib` is where most application data lives. KVM/Libvirt stores virtual machine disks in /var/lib/libvirt/images. Docker (if you use it for AdGuard) stores everything in /var/lib/docker.
  - Install `openssh-server` and manage it remotely using SSH from another machine so you can copy-paste commands from the documentation.
  - enable ssh auto start : `sudo systemctl enable ssh` and  `sudo systemctl start ssh`
### First checks / updates

- Run updates:

```bash
sudo apt update && sudo apt upgrade
```

- Run `ip addr` to check the IP address. This is your HOST-IP. It looks like `192.168.x.x`
- Run `ping google.com` to check the connection.

- Connect remotely in the same network using SSH and the HOST-IP from another machine that has a GUI and a browser so you can copy-paste commands from the documentation.

```bash
ssh username@192.168.x.x
```

- SSH authentication: SSH always requires login, even on your own network. With a `password`, you are prompted to type it on every connection. With an SSH key (`ssh-keygen -t ed25519 -a 100`, then `ssh-copy-id username@192.168.x.x`), no prompt appears — the key proves your identity automatically (your client may ask for the key's passphrase once, or ssh-agent remembers it). If both are set, the key is tried first and the password acts as a fallback. Note: on iOS, the Files app connects to SFTP with a password only (SSH keys are not supported) — for key-based connections use Termius (or another SSH/SFTP client) instead.

- I customized the shell environment by installing Zsh and tools from the [Personal OS Setup](../../README.md) to improve usability and productivity.

### Lid closed (Laptop)

- File: `/etc/systemd/logind.conf`
- Change this line: `HandleLidSwitch=ignore`
- Restart with `sudo systemctl restart systemd-logind`

## Home Assistant

### Virtualization

- I verified that virtualization was supported on the system, checked Secure Boot status:
  - Run:

```bash
egrep -c '(vmx|svm)' /proc/cpuinfo
```

  Should return a number `> 0`.
- Sometimes it returns `0`. In that case you need to check if Virtualization is enabled in your BIOS to ensure compatibility.
- If you still have `0`, and you are sure that Virtualization is enabled in your BIOS, ignore the `0`.

### Install KVM (Kernel-based Virtual Machine) and libvirt

- Install:

```bash
sudo apt-get install qemu-system-x86 libvirt-daemon-system virtinst \
ovmf swtpm qemu-utils guestfs-tools libosinfo-bin -y
```

- Verify:

```bash
lsmod | grep kvm
sudo kvm-ok
lscpu | grep Virtualization
```

- Check libvirt:

```bash
sudo systemctl status libvirtd
sudo usermod -aG libvirt $USER
sudo usermod -aG kvm $USER
```

Restart the terminal and run:
```
id -nG  # user should be added to the group
```
If it is the case, you can run virsh without sudo.

#### Create a bridge configuration
A network bridge in KVM allows your virtual machines to appear directly on the same network as your host.

- Without a bridge: VMs often use NAT (Network Address Translation). They can access the internet, but other devices on your LAN cannot access the VMs directly.

- With a bridge: VMs act like physical machines on your network. They get an IP from your router (or DHCP server) just like your host, and other devices can communicate with them directly.

- This works only with Ethernet, not with wifi.

How to:
- Identify your network interface with `ip addr`, it should look like `enp0s31f6` or `enx001`  It is where you can see eth0.
- Create a bridge configuration file in `/etc/netplan/` with the following content:

- Create a bridge configuration file in  `/etc/netplan/01-bridge.yaml`, replace `enx001cc253c478` with your interface name:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enx001cc253c478:
      dhcp4: no
  bridges:
    br0:
      interfaces: [enx001cc253c478]
      dhcp4: yes
      parameters:
        stp: false
        forward-delay: 0
```


- Before applying the configuration, connect physically to the server because the next command will change the ip address of the SSH and your SSH connection will be lost.
- Your host’s IP will move from enx001cc253c478 to br0
- Apply the configuration:

```bash
sudo netplan apply
```
If you are connected via SSH, you will be disconnected.
Go physically to the server and get the new IP address:

```bash
ip addr
```
Your `interface name` will no longer have a direct IP. All traffic goes through `br0`.
To connect to the server via SSH, you will need to use the ``br0`` address.

### Home Assistant OS in a VM

- Doc: https://www.home-assistant.io/installation/alternative#virtual-machines

- Download the Home Assistant OS image:

```bash
wget https://github.com/home-assistant/operating-system/releases/download/16.3/haos_ova-16.3.qcow2.xz
```

- Move the image to the libvirt directory:

```bash
sudo mv haos_ova-16.3.qcow2.xz /var/lib/libvirt/images/
```

- Uncompress the image:

```bash
sudo xz -d /var/lib/libvirt/images/haos_ova-16.3.qcow2.xz
```

- important: we will use sudo so with all the commands later like `virsh list --all` should use sudo ``sudo virsh list --all`` otherwise it will show nothing.
- HAOS runs under system libvirt  and needs to be managed by root and uses /var/lib/libvirt
-

| Feature                      | system (`root`) | user        | Notes / Explanation                                                                                                   |
|------------------------------|-----------------|-------------|-----------------------------------------------------------------------------------------------------------------------|
| Autostart on boot            | ✅               | ⚠️ Possible | Root/systemd can autostart VMs easily. Users can use `systemd --user` or autostart scripts, but extra setup required. |
| USB passthrough              | ✅               | ⚠️ Possible | Root can attach any USB device. Users can do it if they’re in `libvirt`/`kvm` groups and udev rules allow access.     |
| Bluetooth / Zigbee           | ✅               | ⚠️ Possible | Needs hardware access; root can do it directly. Users need correct groups and permissions.                            |
| Headless server use          | ✅               | ✅           | Works for both. Headless VM does not require GUI.                                                                     |
| Network bridges              | ✅               | ⚠️ Possible | Root can create bridges freely. Users need pre-made bridges or `sudo` for creation.                                   |
| IP forwarding / port mapping | ✅               | ❌           | Modifying `sysctl` and `iptables` requires root. Users cannot forward ports without `sudo`.                           |
| Cloudflare tunnel stability  | ✅               | ✅           | Independent of root vs user. Tunnels are stable as long as service runs correctly.                                    |



- Create the VM: ( we are adding --network bridge=br0) to use the bridge.

```bash
sudo virt-install --name haos --description "Home Assistant OS" --os-variant=generic --ram=4096 --vcpus=2 --disk /var/lib/libvirt/images/haos_ova-16.3.qcow2,bus=scsi --controller type=scsi,model=virtio-scsi --import --graphics none --boot uefi --network bridge=br0,model=virtio --console pty,target_type=serial
```

- Once you see `Welcome to Home Assistant homeassistant login:`, you can quit leave the console using `Ctrl + Alt Gr +]` or Open a new terminal.

- Now we need to check if HAOS is running:
  - `sudo virsh list --all`, you should see the VM running named `haos`
  - Find the IP address of the HAOS VM: From your router’s DHCP table (recommended) on your router app/website. As you can understand, the VM is like a device that is connected to the router, that is why the router assigned it an IP address.
  - The default port is `8123`
  - Check if HAOS is running : open a browser and go to `http://<HAOS-IP>:8123` or use curl: ``curl -v http://<HAOS-IP>:8123``
  - You should see the Home Assistant login page.
  - Back on your terminal, activate the autostart: `sudo virsh autostart haos`
  - Check autostart in: `sudo virsh dominfo haos`


You need to differentiate between:

- HOST IP (the IP of the laptop): `ip addr` example: `192.168.1.86`
- VM-IP or HAOS-IP (the IP of the HAOS VM) example: `192.168.1.20`
- Both have IPs assigned from the router. The HAOS VM uses a bridge, so it gets an IP from the router just like a regular device.
- These IPs can change if we restart the router, we will assign static ip to the VM.

#### inside HA in your browser or mobile app:

- In your browser, go to `http://<HOST-IP>:8123`, for example `http://192.168.1.86:8123`.
- Create an account.
- User settings: Profile -> General-> language, date format, number format, etc.
- Check Advanced mode in General settings.
- in User settings, go to Security -> Enable MFA
- In Settings, check for an update for HAOS. After the update it will restart the server.
- In the addon store, click on the three dots on the top right and add this repository: https://github.com/homeassistant-apps/repository
- Set up a static IP for the VM: in HAOS website go to Settings -> System -> Network -> and change IPv4 from auto to static and IPv6 too. You can keep the default ip that is assigned to the VM.

### 2. Accessing HAOS from outside your local network  — Cloudflare Tunnel Setup
- Create a Domain or your domain is already managed by **Cloudflare**
- In HAOS, add the addon `file editor`.
- Follow this video: https://youtu.be/JGAKzzOmvxg
- Don't forget to update and save configuration.yaml
- Restart HAOS
- On you phone, when you add home assistant, add both local and external URL, so you can connect when you are outside
- Adding both local and external URL is important because the external URL is the one that will be used when you are outside your local network.

**Add Cloudflare Access (Zero Trust) ⭐⭐⭐**

This is the single biggest security upgrade. Before showing your Home Assistant app in your browser or mobile, it will force the user to first login via an email or something.
If the User can't log in, he won't be able to see the app.

- You are protecting for example `ha.yourdomain.com`
Go to  Cloudflare Zero Trust -> Access Controls -> Applications -> Self-hosted:

##### 1️⃣ Basic Information (Top Section)

Application name

Use something clear:

- Home Assistant
- (or Home Assistant – Production if you like)

Session Duration

Recommended:

- 24 hours or You can put more

##### 2️⃣ Add Public Hostname (IMPORTANT)

Click Add public hostname.

Fill in:

- Hostname: `ha.yourdomain.com`
- Path: `/*`
- Type: HTTP

👉 This is what actually puts the Access login page in front of Home Assistant.

Do NOT add private IP unless you know you need it.

##### 3️⃣ Browser Rendering Settings

Leave this OFF / untouched.

(Home Assistant does NOT need SSH/RDP/VNC rendering)

##### 4️⃣ Policies (MOST IMPORTANT PART)

Click Add a policy. It will open a new page, and need to go back to this page and refresh it to show the policies.

Policy 1 — Allow yourself (and family)

- Policy name: Allow Home Assistant Users
- Action: Allow

Rules (choose ONE of these methods):

✅ Best option: Email-based

- Include -> Emails -> `your@email.com`
- You can add multiple emails (family members).

✅ Alternative: Identity provider

If using Google / Microsoft / GitHub:

- You can for example add GitHub following [this](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/github/).
- Adding the integration automatically adds it as a login method to all the applications. Don't add the provider as a login method to the policy, otherwise, it will accept all the users using that provider.
- Keep the emails in the policy. https://developers.cloudflare.com/cloudflare-one/access-controls/policies/#require
- If you want to disable the login, create a policy with action allow and an include rule 'everyone'

❌ Do NOT use:

- “Allow everyone”
- IP-only rules (unless combined with email)
- Country-only rules alone

(Optional but recommended)

- Add Require MFA if available in your plan.

##### 5️⃣ (Optional) Add a Second Policy – Emergency Lockdown

Advanced but useful:

- Policy name: Block High Risk Countries
- Action: Block
- Rule:
  - Include -> Countries -> (countries you NEVER travel to)

Cloudflare evaluates Block after Allow, so this is safe.

##### 6️⃣ Login Methods

You’ll see:

- Accept all available identity providers -> ON

Recommended setting:

✅ Leave this ON if:

- You trust future IdPs
- You are the only admin

OR

🔒 Turn OFF and explicitly select:

- Google
- Email OTP

This is slightly more secure, less future surprise.

##### Go back to the previous page to see the policies
Where you put your domain, choose the policies you added.

##### 7️⃣ Save the Application ✅

Once saved:

- Visiting `ha.yourdomain.com` should show Cloudflare Access login. If it doesn't force refresh the page or clear cookies.
- Only after login -> Home Assistant loads

If you do a restoration, or change something in cloudflare, and you see that you can't view home assistant, delete the cookies and try again.

#### Activate MFA
- In profile -> security, activate MFA

You should now have:

- ✅ Cloudflare Tunnel (no ports open)
- ✅ Cloudflare Access login in front of HA
- ✅ Email (or Google login or GitHub)
- ✅ MFA
- ✅ 1 month session

---

### Home Assistant devices, add-ons, and integrations

- **Integrations**: built into Home Assistant (Settings -> Devices & services).
- **Add-ons (Apps)**: services that run alongside Home Assistant OS (AdguardHome,Cloudflared...etc).
- **Repositories**: additional catalogs for community add-ons and integrations (example: HACS).

Notes:

- Always search for an open-source integration before using a proprietary app. For example: TP-link, Dreame, LG ThinQ, Bosch Home Connect have open-source integrations and are far better than the proprietary apps.
- Some devices still need their vendor app for initial setup or extra features (example: LG, Bosch). It’s fine to keep the app installed even if you control the device later in Home Assistant.

#### Matter over Wi-Fi

-  TBD

#### Matter over Thread and Zigbee devices

- If the device does Matter over Thread, you will need a Thread Border Router (TBR) on your network. Personally, I recommend [Sonoff MG24](https://www.amazon.fr/SONOFF-Dongle-PMG24-Dongle-Plus-MG24/dp/B0FMJD288B) . It even supports both Thread and Zigbee and the same time.
- Do not use Aqara M100 because it is proprietary and not well-supported in Home Assistant.

How to setup Sonoff MG24:

 - Attach to usb port, run `usb-devices` on ubuntu and get Vendor and ProdID.
 - Run:

 ```sh
 sudo virsh attach-device haos /dev/stdin --persistent <<EOF
 <hostdev mode='subsystem' type='usb' managed='yes'>
   <source>
     <vendor id='0x10c4'/>
     <product id='0xea60'/>
   </source>
 </hostdev>
 EOF
 ```

 Or using the bus and device:

 ```sh
 sudo virsh attach-device haos /dev/stdin --persistent <<EOF
 <hostdev mode='subsystem' type='usb' managed='yes'>
   <source>
     <address bus='1' device='12'/>
   </source>
 </hostdev>
 EOF
 ```

 - Run `sudo virsh reboot haos`.
 - Go to Home Assistant -> Settings -> System -> Hardware -> All Hardware -> search for `Sonoff`.
 - Flash it using this [tutorial](https://blog.dautek.fr/comment-installer-le-dongle-zigbee-et-thread-sonoff-mg24-sur-home-assistant).

 If you want only thread: flash Sonoff for thread only.

 If you want both Thread controller and Zigbee, use Multipan with the MG24. Tutorials:

 - French: https://sonoff.tech/fr-fr/blogs/news/how-to-use-multipan-in-home-assistant-with-sonoff-dongle
 - English: https://www.sonoff.in/blog/product-guides-3/how-to-use-multipan-in-home-assistant-with-sonoff-zbdongle-e-36
 - Deactivate ZHA, and add devices: https://youtu.be/KA4XvVhyCtE?t=112
 - If you are facing an issue with onboarding not loading after submitting, check: https://community.home-assistant.io/t/smlight-slzb-06-new-installation-can-not-pass-the-zigbee2mqtt-onboarding-page/908462/2

 ### Apps / Add-ons

* **AdGuard Home**
  * DNS and DHCP (do not forget to add IPv4 and IPv6 DNS servers to your router). Disable safe search.
  * For IP address name resolving, check [this section](#adguard-home-address-naming-resolution-using-the-router-freebox).
  * Docs/repo: https://github.com/hassio-addons/addon-adguard-home
  * Add Google and Cloudflare DNS servers (both IPV4 and IPV6) as 2nd and 3rd options incase the self-hosted AdGuard Home breaks.
  * Make heavy tests (Restart the server, restart HA, restart the router, cut the power off...) after setting AdGuard Home because if something breaks, you will not be able to access your home assistant.


* [Cloudflared](https://github.com/homeassistant-apps/app-cloudflared) (Cloudflare Tunnel)

* [Donetick](https://github.com/donetick/hassio-addons)

* **File editor** :
  * Docs: https://github.com/home-assistant/addons/tree/master/configurator
  * How to install: https://github.com/home-assistant/addons/blob/master/configurator/DOCS.md

* [Home Assistant Community Store (HACS)](https://www.hacs.xyz/)

* [Home Assistant Google Drive Backup](https://github.com/sabeechen/hassio-google-drive-backup)
    * Backup everything except media.
    * Test the backup at least once: https://youtu.be/xXXW7sQ9rqs?t=274
    * Backup keeps everything, even addons configuration (delete cookies if the login page is not showing on your domain name).
    * Samba backup add-on: https://github.com/thomasmauerer/hassio-addons/tree/master/samba-backup
    * After a restoration, everything should work as expected:
        * Clean cookies in your browser because of Cloudflare.
        * The Sonoff MG24 can be unrecognized: wait a bit; if still not recognized, detach it and attach it again.

* [Linky](https://github.com/bokub/ha-linky)

* [motionEye](https://www.home-assistant.io/integrations/motioneye/)

* Music/Audio addons :
  * Navidrome:
  * Use it with Octo-Fiesta (and [Tidal](https://tidal.squid.wtf/) as a backend)
  * Music Assistant Addon
  * Clients : https://www.navidrome.org/apps/
    * For example Narjo for iOS
  * Auto tagger : Beets
  * You can check this [music server setup](music_server.md)


* **Vaultwarden** (self-hosted Bitwarden backend)
  * Lightweight, open-source reimplementation of the Bitwarden server API. All official Bitwarden clients (iOS, Android, Windows, macOS, browser extensions) work with it.
  * Addon repo: https://github.com/hassio-addons/app-vaultwarden
  * After installing, point your Bitwarden clients to your self-hosted server URL instead of `bitwarden.com`.

* [n8n](https://github.com/Rbillon59/hass-n8n)

* **Samba Backup**

* **Samba Share**
    * Docs: https://github.com/home-assistant/addons/tree/master/samba
    * How to install: https://github.com/home-assistant/addons/blob/master/samba/DOCS.md
    * Useful video example: https://www.youtube.com/watch?v=Vu_oxefjd0I
    * Common tasks: https://www.home-assistant.io/common-tasks/os/#installing-and-using-the-samba-add-on

* [Advanced SSH & Web Terminal](https://github.com/hassio-addons/addon-ssh) (replaces the official Terminal & SSH add-on)
  * Add-on repository to add in HA: https://github.com/hassio-addons/repository
  * Docs: https://github.com/hassio-addons/addon-ssh/blob/main/ssh/DOCS.md
  * Web terminal in the sidebar + SSH server, with Docker CLI and Docker socket access built in
  * Note: disable **Protection mode** to use Docker; set a `password` and/or `authorized_keys` in the configuration to log in
  * Authentication: SSH always requires login, even on your own network. With a `password`, you are prompted to type it on every connection (`ssh hassio@<ha-ip>`). With an `authorized_keys` entry, no prompt appears — the key proves your identity automatically (your client may ask for the key's passphrase once, or ssh-agent remembers it). If both are set, the key is tried first and the password acts as a fallback. Note: on iOS, the Files app connects to SFTP with a password only (SSH keys are not supported) — for key-based connections use Termius (or another SSH/SFTP client) instead.

This next section is about controllers / routers add-ons :

* **Home Assistant Matter Hub**
   - Repo: https://github.com/RiDDiX/home-assistant-matter-hub
   - Tutorial (old version but should work): https://www.youtube.com/watch?v=-TMzuHFo_-g
   - Notes:
     - Transform any device into a Matter device.
     - Use it with Alexa and Google Home. If Alexa doesn't discover the hub, use Google Home app, then add it to Alexa from Google Home.
     - You need to add labels to entities (not devices).

* **Matter Server**

* **Mosquitto broker**

* **Silicon Labs Multiprotocol**

* [Silicon Labs Flasher](https://github.com/home-assistant/addons/tree/master/silabs_flasher) (useful for multiprotocol / firmware)

* **SONOFF Dongle Flasher**

* **Zigbee2MQTT**

### Integrations
* **AdGuard Home**
   - Add-on repo (service): https://github.com/hassio-addons/addon-adguard-home

* **Alexa Media Player**
   - Repo: https://github.com/alandtse/alexa_media_player
   - Video guide you referenced: https://www.youtube.com/watch?v=TDdREzkigIE&t
   - Docs: https://www.home-assistant.io/integrations/alexa_media_player/

* **Android TV Remote** : Control your TV.

* **Backup** :

* **Brother Printer**

* **C.A.F.E**: https://github.com/FezVrasta/cafe-hass

* **Dreame vacuum**
  * Community integration repo: https://github.com/Tasshack/dreame-vacuum
  * Do not use the version 1. Use version > 2 (supports multiple accounts: dreamehome, xiaomi, etc.).
  * Maps for the vaccum:
    - https://github.com/noambergauz/dreame-vacuum-map-card
  * Script for voice assistant cleaning per room : https://github.com/Magnum9O/HA_BluePrints

* **Free Mobile** : https://www.home-assistant.io/integrations/freemobile/

* **Freebox** : https://www.home-assistant.io/integrations/freebox/

* **HACS**: The best is to use Home Assistant Community Store integrations when available; they often have more features.


* **Home Assistant Supervisor**

* **Home Connect Alt** : https://github.com/ekutner/home-connect-hass for Bosch devices

* **Matter**

* **Mobile App**

* **MotionEye**
  - https://www.home-assistant.io/integrations/motioneye/

* **MQTT**
  * Volets Profalux Zigbee: https://perso.aquilenet.fr/~sven337/francais/2023/06/02/Appairage-de-volets-Profalux-Zigbee.html
  * Windows (start, lock, restart, sleep...) :  [HASS Agent](https://github.com/hass-agent/HASS.Agent)


* **Open Thread Border Router**

* **SmartThinQ LGE Sensors** : https://github.com/ollo69/ha-smartthinq-sensors

* **Sun**

* **Tapo: Cameras Control**

* **Thread**

* **TP-Link Smart Home**



* HA Label State: https://github.com/andrew-codechimp/HA-Label-State

### Dashboard & Cards
* **Auto entities** : https://github.com/thomasloven/lovelace-auto-entities
* **Custom sidebar**: https://github.com/elchininet/custom-sidebar
* **Kiosk Mode**: https://github.com/NemesisRE/kiosk-mode
* **Mushroom cards** : https://github.com/piitaya/lovelace-mushroom#installation
* **Universal Remote Card** : https://github.com/Nerwyn/universal-remote-card


### Automations, Scenes, Script, Helpers and Entities
* **🤖 Automation** = When something happens → do something
    * Always use entities instead of devices. Entities have unique names.
* **🎬 Scene** = Rarely used. Set things to a predefined state. A scene is just a snapshot of states.
    * Script: is a sequence of actions that can be triggered by an automation or manually.
* **👉 Automations** trigger scenes
* An example : I want to arm the alarm when I leave my home
    * Automation 1 : if my phone is not available in home assistant (using freebox device tracker) -> Call a script to arm the alarm,
    * Script 1: turn on the alarm, turn on the lock of doors, activate the camera's high motion detections ..etc
    * Automation 2: if the alarm is triggered -> send notifications, run sound on the alarm ...
* **Scripts** are usually created so we can activate them manually or with an automation. They don't have conditions.

* **Helpers**
    * [HA Label State](https://github.com/andrew-codechimp/HA-Label-State)

* **Entities**
    * When you add an entity, you can select a default behavior (toggle , show info, etc..) . For example a camera move down button, the default behavior is to ``show more info``, but you can change it to ``toggle`` so when you press that button, it will move the camera.
    * Show offline devices and addons : Add a filter card that shows 'not_home' and 'unavailable' entities and addons. You need to go to an addon in devices, and enable the 'running' entity to be able to use it in the card.
    * When you rename a device, you can auto recreate the IDs. Changing the entity id doesn't propagate in scripts and automation so before changing the id of an entity, click on related, open in new tabs all the related stuff , change the id then change the id in the related stuff
    * Use labels to group entities. For example, an 'entity status' label and 'addon status' label to detect offline devices and addons without the need to add each device in the condition. You need the


## AdGuard Home address naming resolution using the router (Freebox)
- The following will show you how to get the names of the devices in AdGuard home using your router (this example is for Freebox API).
- You will notice that your AdGuard Home (AGH) logs contains anonymous entries like "FREE SAS" or raw IPv6 addresses (e.g., fe80::...).
- We create a Python script on Ubuntu that will get all the information from the Freebox API and send it to the AdGuard Home API.
- Steps:
  - In the addon configuration in HA: open the port 8082, you should access the dashboard without authentication on ``HA-IP:8082``. the username and password are your Home assistant username and password (you can create a user named 'adguard' for it).
  - Put the following scripts in the server:
    - [freebox_auth.py](freebox_auth.py)
    - [sync_adguard_home_ip_mac.py](sync_adguard_home_ip_mac.py)
  - I am using Freebox pop as a router, so I use the script [freebox_auth.py](freebox_auth.py) to get the token ``uv run freebox_auth.py``
  - then I use this script in the server to automatically update Adguard home: [sync_adguard_home_ip_mac.py](sync_adguard_home_ip_mac.py) to automatically resolve IPV6 addresses and clients names. ``uv run sync_adguard_home_ip_mac.py``
  - Make a cronjob for it by adding this line at the end of ``crontab -e`` (change the path of uv and the script)
````sh
# For example
* * * * * /home/amine/.local/bin/uv run sync_adguard_home_ip_mac.py
````

- Check Settings -> Client settings -> **Persistent clients settings** .
- This script will run every minute. If it discovers a new device, it will update the log file ``sync_agh.log`` with the latest sync information.

# todo:
- backup vm
- Lan architecture : Router Freebox = Honor Router 3  (bridge) - Ubuntu server (HAOS ( Adguard DNS + DHCP + Script for IPV6 update & naming resolution))

- add cards :
https://github.com/PiotrMachowski/lovelace-xiaomi-vacuum-map-card
mushroom card
auto entities
kioske mode
custom sidebar
room card
