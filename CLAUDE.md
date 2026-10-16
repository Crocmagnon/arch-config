# CLAUDE.md

Guidance for Claude Code in this repository. Keep it and `README.md` current: update both whenever a module, a decision or a procedure changes, not at the end.

## What this is

Declarative Arch Linux config for the user's desktops (`framework-gab`, a Framework 13 Pro Intel, and `desktop-gab`):
- archinstall for disk and boot;
- decman for system packages, `/etc` files, systemd units and snapshots;
- user files live in the separate chezmoi `dotfiles` repo.

The NixOS → Arch migration is done. Its inventory and decisions live in git history (`git log -- MIGRATION.md`); the rules that still apply are below.

## Commands

```sh
archinstall/render.sh <hostname> <disk> > config.json      # on the ISO
archinstall/creds.sh                                       # asks the password, writes archinstall/creds.json
archinstall --config config.json --creds archinstall/creds.json --silent
sudo decman --source decman/source.py --dry-run --debug     # always first
sudo decman --source decman/source.py                       # first real run: remembers the path
sudo decman                                                 # later runs (dry-run never stores it)
python3 -m py_compile decman/*.py                           # quick syntax check
```

Test in the VM bench (`vm/README.md`) before touching real hardware: `vm/state.sh save|reset|list`.

## Architecture

- `decman/source.py`: entry point. Sets `decman.execution_order`, maps hostname to kernel params and modules, and refuses unknown hosts.
- One module per concern (`base.py`, `boot.py`, …), then host modules. Files owned by a module live in `decman/files/<module>/`.
- `archinstall/user_configuration.json` has placeholders (`@HOSTNAME@`, `@DEVICE@`, `"@ESP_MIB@"`, `"@ROOT_START_MIB@"`, `"@ROOT_MIB@"`) filled by `render.sh`, which holds the ESP size. Laptop hostnames start with `framework-gab`: its hibernation swapfile command matches that prefix.

## Rules and gotchas (all verified)

- **decman removes every explicit package that is not declared, and every orphan.** An optional dependency counts as an orphan: that is why `wpa_supplicant` is declared, since without it the laptop loses Wi-Fi. Declare meta-packages, never groups. Before a first real run, compare `--dry-run` with `pacman -Qqe`.
- **ufw is the firewall, managed by decman.** `plasma-firewall` comes with `plasma-meta` but must not be used: decman would overwrite its changes.
- **Execution order is `pacman, aur, flatpak, files, systemd`.** Writing a file that a not-yet-installed package owns would make pacman fail.
- **decman enables units, never starts them.** It only touches units that are, or were, declared.
- **`on_change` also runs on the first run, together with `on_enable`.** Do not repeat work in both.
- **Never manage `/boot/limine.conf`.** limine-mkinitcpio-hook generates it from `/etc/kernel/cmdline`, and limine-snapper-sync adds the snapshot entries. `limine-update` rewrites it, keeping global options, so add a global option with an idempotent edit in a hook (see `term_font_scale` in `framework_gab.py`), never a `File`. Its checksum is not enrolled in the Limine binary: that only happens with `ENABLE_ENROLL_LIMINE_CONFIG=yes`, which is off by default (`enroll_config()` in `/usr/lib/limine/limine-common-functions`).
- **Initramfs hooks live in `/etc/mkinitcpio.conf.d/10-hooks.conf`.** archinstall writes it, and `boot.py` takes it over and adds `sd-btrfs-overlayfs`, which is required to boot a read-only snapshot and only exists once the AUR package is installed. Both also set `MODULES=(thunderbolt)`: the USB4 dock's DP tunnel needs it, and without it in the initramfs the docked screen stays black at the LUKS prompt (the module only loaded after switch-root). Limine and the firmware stay black behind the dock regardless; that part is up to the BIOS.
- **The LUKS root is in `/etc/crypttab` with `x-initrd.attach`.** `crypttab.initramfs` is deprecated in mkinitcpio 42. UUIDs are per install and never go in git.
- **archinstall 4.4 bugs and limits:**
  - `btrfs_options` from JSON is ignored (string vs `Path` compare), so snapper is set up in `boot.py`.
  - Sizes must be absolute, no `Percent`, hence `render.sh`.
  - The swap partition cannot be encrypted cleanly, hence a btrfs swapfile.
  - `custom_commands` run after the bootloader and before `genfstab`.
- **LUKS `iter_time` is 2000 ms in `user_configuration.json`.** archinstall's default is 10000 ms (`--iter-time` on `luksFormat`), which makes argon2id take ~10 s at every unlock. Lower an existing keyslot with `cryptsetup luksConvertKey --iter-time 2000 --key-slot 0 <part>`.
- **systemd-sleep hooks go in `/usr/lib/systemd/system-sleep/`.** `/etc/systemd/system-sleep/` only works on NixOS.
- **The framework-gab webcam wakes the laptop from s2idle.** It drops off and back on its USB port (`usb3-port6` on `0000:00:14.0`) as the system suspends, and the root hub wakes on that connect change; powerdevil then re-suspended every ~12 s all night with the lid closed, never reaching hibernation. The `webcam-port-off` sleep hook disables the port around sleep. Do not disable root hub wakeup instead: the KVM uses the same controller. To find a wake source, `echo 1 > /sys/power/pm_debug_messages`, test with `rtcwake -m freeze -s 15`, and enable dynamic debug on `drivers/usb/core/hub.c` and `drivers/usb/host/xhci-hub.c` to see which port changed.
- **framework-gab cannot drive 4K above 120 Hz through the USB4 dock.** At 180 and 240 Hz the screen is garbled behind the Cable Matters dock (Synaptics `SYNAR` branch), with or without the KVM. `xe` picks 4 DSC slices there, but 8 on the direct DP expansion card, which works. Both report 340 MP/s per slice. Reported upstream as [drm/xe#9600](https://gitlab.freedesktop.org/drm/xe/kernel/-/work_items/9600). Stay at 120 Hz behind the dock, or use the DP card directly for 240 Hz.
- **Arch groups:** serial ports are `uucp`, not `dialout`, and libvirt is `libvirt`, not `libvirtd`.
- **AUR builds run as `builduser`** (a system user). PGP keys for signed sources are received into its keyring by `GPGReceiver` in `source.py`, with one comment per key naming the package that needs it. The default `nobody` has no keyring, so any signed source fails.
- **Never declare a package that another declared AUR package already pulls in** (for example `nrf-udev`, a dependency of `nrfconnect-appimage`). The AUR step installs it as a dependency, and every later run tries to install it again.
- **Declare the provider whenever pacman would ask which package provides a virtual dependency.** Otherwise real installs prompt, and the default can be wrong: for `tessdata`, the default is Afrikaans. Declared so far: `pipewire-jack`, `qt6-multimedia-ffmpeg`, `tesseract-data-eng`, `tesseract-data-fra`, `vulkan-radeon`, `lib32-vulkan-radeon`, `vulkan-intel`, `lib32-vulkan-intel`; and, declared for themselves but providers too, so keep them: `mkinitcpio` (`initramfs`), `wireplumber` (`pipewire-session-manager`), `pipewire-pulse` (`pulse-native-provider`), `noto-fonts` (`ttf-font`). After a VM run, list the prompts with `grep -a -A3 "providers available"` on the log.
- **Discover is not used** (`plasma-meta` pulls it in). decman runs `flatpak update --system` on every run, packagekit is not installed, and firmware goes through `fwupdmgr`. dotfiles hides its update notifier (`autostart/org.kde.discover.notifier.desktop`), whose list goes stale after decman updates the runtimes.
- **Flatpak needs two runs.** The decman flatpak plugin is probed at startup, before pacman installs `flatpak`, so the first run skips it with a warning.
- **The autologin wallet is served by `ksecretd`** (KWallet 6), which owns `org.freedesktop.secrets` and is unlocked by PAM. Check it with the Secret Service `Locked` property of `/org/freedesktop/secrets/collection/kdewallet`. The legacy `org.kde.kwalletd6` name is a separate process that reports the wallet closed; whether apps using it re-prompt is still to be checked.
- **ufw overrides sysctl at start with `/etc/ufw/sysctl.conf`**, which sets `rp_filter=1` (strict) and breaks the Tailscale exit node. decman owns that file with `rp_filter=2`. After a ufw upgrade, merge the `.pacnew`.
- **Docker bypasses ufw.** It DNATs published ports in `nat PREROUTING` and accepts them in `DOCKER-FORWARD`, ahead of ufw's chains, so a plain `-p 8080:80` was reachable from the LAN. `/etc/docker/daemon.json` (`"ip": "127.0.0.1"`) binds published ports to localhost; `-p 0.0.0.0:…` opens one on purpose.
- **ufw rules go in `Desktop.after_update`, not `on_change`.** `on_change` only fires when a module's files, packages or units change, never when its code does, so a rule added there never reaches existing machines. ufw skips a rule already present.
- **ufw denies all incoming traffic, SSH included.** The real machines run no SSH server; they are reached by Tailscale SSH (`tailscale up --ssh`), which `tailscaled` serves itself and which bypasses ufw (verified). In the VM, chain `sudo ufw allow ssh` in the same command as the first real decman run: the running session survives (established connections pass), new ones do not (recovery: a TTY via `virsh send-key`).
- **nix comes from pacman (`apps.py`), for the repos that have a flake.** decman owns `/etc/nix/nix.conf`, which the package also owns (merge the `.pacnew` after an upgrade), to enable flakes. The daemon is socket-activated (`nix-daemon.socket`). No `nix-users` group: the Arch package only creates `nixbld`, and Nix's default `allowed-users = *` lets every user reach the daemon.
- **gpg-agent is the SSH agent, set up by dotfiles**, whose `CLAUDE.md` holds its gotchas. In VM tests, never run `gpg-connect-agent updatestartuptty` from a display-less ssh command: it wipes the display pinentry uses.

## Boundary with dotfiles

The user side lives in the `dotfiles` repo (chezmoi, `main`, cloned at `~/.local/share/chezmoi`), whose `CLAUDE.md` holds the chezmoi gotchas. dotfiles serves four machines, two of them work machines on Ubuntu and Debian; this repo serves only the Arch desktops. Where a thing goes:
- **Here (decman):** anything that needs root or is specific to Arch: packages, `/etc`, system units, udev, groups, plus the tools that must exist before chezmoi and mise run (`base.py`).
- **dotfiles:** anything under `$HOME`, including user units and Plasma settings. A CLI tool also wanted on the work machines comes from mise there; one that only matters on Arch, or that mise cannot build, comes from pacman here.

This repo owns the list of tools dotfiles relies on that come from pacman instead of mise:
- **needed before mise:** `fish`, `fisher`, `gnupg`, `git-crypt`, `chezmoi`, `mise` (`base.py`); dotfiles disables the mise copies of chezmoi and git-crypt on Arch;
- **absent from mise:** `luarocks`, `luacheck`, `busted` (`apps.py`);
- **called outside an interactive fish**, where mise is not activated: `git-lfs` (git filter marked `required`), `jq` (Claude Code statusline), `claude-code` (`run_onchange` MCP script).

On the work machines the same tools come from apt (laptop) or a local mise config (server).

## Working rules

- Never decrypt, print or modify secrets: git-crypt files in dotfiles, agenix files in nixos-config. The user runs re-encryption scripts themselves.
- No commit or push without the user's go. The user reviews at the end of each phase.
- Never touch `srv-1` in nixos-config.
- In the VM, drive interactive decman runs with `vm/answer.py`, type the LUKS passphrase with `virsh send-key`, and never pass `pkill -f` a pattern that matches your own ssh command line.
