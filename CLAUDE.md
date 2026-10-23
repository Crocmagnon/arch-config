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
python3 decman/test_maintenance.py                          # offline self-check of the news/pacnew hooks
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
- **Initramfs hooks live in `/etc/mkinitcpio.conf.d/10-hooks.conf`.** archinstall writes it, and `boot.py` takes it over and adds `sd-btrfs-overlayfs`, which is required to boot a read-only snapshot and only exists once the AUR package is installed. Both also set `MODULES=(thunderbolt)`: the USB4 dock's DP tunnel needs it, and without it in the initramfs the docked screen stays black at the LUKS prompt (the module only loaded after switch-root). Limine and the firmware stay black behind the dock regardless: BIOS 3.02 has no USB4 pre-boot option. To start it docked with the lid closed, the BIOS has "Power on AC attach" enabled: cut and restore the dock's power.
- **The LUKS root is in `/etc/crypttab` with `x-initrd.attach`.** `crypttab.initramfs` is deprecated in mkinitcpio 42. UUIDs are per install and never go in git.
- **archinstall 4.4 bugs and limits:**
  - `btrfs_options` from JSON is ignored (string vs `Path` compare), so snapper is set up in `boot.py`.
  - Sizes must be absolute, no `Percent`, hence `render.sh`.
  - The swap partition cannot be encrypted cleanly, hence a btrfs swapfile.
  - `custom_commands` run after the bootloader and before `genfstab`.
- **LUKS `iter_time` is 2000 ms in `user_configuration.json`.** archinstall's default is 10000 ms (`--iter-time` on `luksFormat`), which makes argon2id take ~10 s at every unlock. Lower an existing keyslot with `cryptsetup luksConvertKey --iter-time 2000 --key-slot 0 <part>`.
- **Resume from hibernation waits forever for the LUKS passphrase** (`resumeflags=x-systemd.device-timeout=infinity` in `boot.py`). Without `resume=`, the resume device comes from the `HibernateLocation` EFI variable, and `systemd-hibernate-resume-generator` then gives it a 2 min job timeout. A passphrase typed later cold-boots: the image is discarded and the session lost. On 19/10/2026 that cold boot, docked with the lid closed, was also suspended by logind at once, freezing `user.slice` while autologin started: black screen. A normal boot does not wait, since the generator exits when the variable is absent. The catch: a stale variable naming a volume that never appears (hibernate, then reinstall, reformat or swap the SSD) hangs the boot forever. Boot once with `noresume` added in the Limine editor (`e`): systemd then clears the variable. The same is the only way to give up a resume at the LUKS prompt. A corrupt image or one from another kernel is not affected: the resume fails fast and the boot goes on.
- **systemd-sleep hooks go in `/usr/lib/systemd/system-sleep/`.** `/etc/systemd/system-sleep/` only works on NixOS.
- **The framework-gab webcam wakes the laptop from s2idle.** It drops off and back on its USB port (`usb3-port6` on `0000:00:14.0`) as the system suspends, and the root hub wakes on that connect change; powerdevil then re-suspended every ~12 s all night with the lid closed, never reaching hibernation. The `webcam-port-off` sleep hook disables the port around sleep. Do not disable root hub wakeup instead: the KVM uses the same controller. To find a wake source, `echo 1 > /sys/power/pm_debug_messages`, test with `rtcwake -m freeze -s 15`, and enable dynamic debug on `drivers/usb/core/hub.c` and `drivers/usb/host/xhci-hub.c` to see which port changed.
- **framework-gab cannot drive 4K above 120 Hz through the USB4 dock.** At 180 and 240 Hz the screen is garbled behind the Cable Matters dock (Synaptics `SYNAR` branch), with or without the KVM. `xe` picks 4 DSC slices there, but 8 on the direct DP expansion card, which works. Both report 340 MP/s per slice. Reported upstream as [drm/xe#9600](https://gitlab.freedesktop.org/drm/xe/kernel/-/work_items/9600). Stay at 120 Hz behind the dock, or use the DP card directly for 240 Hz.
- **`maintenance.py` shows what an update needs from a human, when it matters.** Before the update, unread Arch news (first run: the last 30 days), naming the installed packages a title mentions and whether they have an upgrade pending, then a confirmation; news is marked read only once confirmed, kept in the decman store (`news_seen`). After it: each `.pacnew`/`.pacsave` with its diff (one for a file decman writes goes into the repo, then `rm`, never `pacdiff`: decman would overwrite the merge), a reboot reminder when `linux` differs from the running kernel (`kernel-modules-hook` keeps the running modules, so their presence proves nothing), and pending firmware. Hooks never run with `--dry-run`. decman also installs the file itself to `/usr/local/lib/arch-maintenance/`, where `update-reminder.timer` runs it weekly (never more often, by the user's choice) as `maintenance.py remind <user>`: a Plasma notification with the pending upgrades (the kernel named) and unread news, nothing when there is none or no session is open.
- **Mirrors come from reflector** (`reflector.conf` in `base.py`, `reflector.timer` weekly, first run from `on_change`): synced within the hour, the 10 fastest among the 25 most recent nearby. reflector rewrites `/etc/pacman.d/mirrorlist`, so `maintenance.py` deletes the `mirrorlist.pacnew` that `pacman-mirrorlist` upgrades leave.
- **Only downloads and Flatpaks update unattended.** `pacman-download.timer` runs `checkupdates -d`, whose separate database avoids a partial upgrade; it exits 2 when there is nothing to do. `fwupd-refresh.timer` only fetches metadata. pacman and AUR upgrades stay a manual `sudo decman`: news interventions, `.pacnew` merges and provider prompts need a human.
- **Arch groups:** serial ports are `uucp`, not `dialout`, and libvirt is `libvirt`, not `libvirtd`.
- **AUR builds run as `builduser`** (a system user). PGP keys for signed sources are received into its keyring by `GPGReceiver` in `source.py`, with one comment per key naming the package that needs it. The default `nobody` has no keyring, so any signed source fails.
- **Never declare a package that another declared AUR package already pulls in** (for example `nrf-udev`, a dependency of `nrfconnect-appimage`). The AUR step installs it as a dependency, and every later run tries to install it again.
- **Declare the provider whenever pacman would ask which package provides a virtual dependency.** Otherwise real installs prompt, and the default can be wrong: for `tessdata`, the default is Afrikaans. Declared so far: `pipewire-jack`, `qt6-multimedia-ffmpeg`, `tesseract-data-eng`, `tesseract-data-fra`, `vulkan-radeon`, `lib32-vulkan-radeon`, `vulkan-intel`, `lib32-vulkan-intel`; and, declared for themselves but providers too, so keep them: `mkinitcpio` (`initramfs`), `wireplumber` (`pipewire-session-manager`), `pipewire-pulse` (`pulse-native-provider`), `noto-fonts` (`ttf-font`). After a VM run, list the prompts with `grep -a -A3 "providers available"` on the log.
- **Discover is not used** (`plasma-meta` pulls it in). decman runs `flatpak update --system` on every run, and `flatpak-update.timer` daily; packagekit is not installed, and firmware goes through `fwupdmgr`. dotfiles hides its update notifier (`autostart/org.kde.discover.notifier.desktop`), whose list goes stale after decman updates the runtimes.
- **Flatpak needs two runs.** The decman flatpak plugin is probed at startup, before pacman installs `flatpak`, so the first run skips it with a warning.
- **The YubiKey Bio unlocks LUKS** (`systemd-cryptenroll --fido2-device=auto --fido2-with-client-pin=no --fido2-with-user-verification=yes`, `fido2-device=auto` in crypttab); the passphrase keyslot stays as fallback. systemd-cryptsetup waits `token-timeout=` (default 30 s, kept) for the key, then asks the passphrase and stops watching USB: a key plugged in after that is ignored until the next boot. Nothing skips the wait from the keyboard: on framework-gab away from the key, every boot and resume waits 30 s; lower it with `token-timeout=` in crypttab if that gets in the way. Once, on desktop-gab, the key behind the KVM failed USB enumeration (`device descriptor read/64, error -110`) and needed a replug.
- **A refused finger at the LUKS prompt failed the boot into emergency mode.** libfido2 reports it as a generic error (`EIO`), and systemd-cryptsetup only retries or falls back to the passphrase when the key is absent (`EAGAIN`). `boot.py` replaces the `ExecStart` of `systemd-cryptsetup@root` with `luks-attach` (drop-in and script in the initramfs through `FILES`): three tries with the key, then the passphrase alone. The emergency shell recovers with `systemd-cryptsetup attach root /dev/disk/by-uuid/<uuid> none luks`, then `exit`. Verified on framework-gab (20/10/2026). After three failed fingers in a row, the Bio blinks red and refuses every finger, even replugged, until the FIDO PIN is entered once (`ykman fido fingerprints list`).
- **The KDE wallet has an empty password.** A FIDO2 unlock puts no passphrase in the kernel keyring, so the former `pam_systemd_loadkey` chain could not open it. With LUKS and autologin, its protection was already the disk's; the catch is that a backup of `~/.local/share/kwalletd/` would be readable, and none is made. Such a wallet stays `Locked` until the first app asks for it, then opens without a prompt (`kwallet-query -l kdewallet` opens it).
- **The autologin wallet is served by `ksecretd`** (KWallet 6), which owns `org.freedesktop.secrets`. Check it with the Secret Service `Locked` property of `/org/freedesktop/secrets/collection/kdewallet`. The legacy `org.kde.kwalletd6` name is a separate process that reports the wallet closed; whether apps using it re-prompt is still to be checked.
- **kscreenlocker ships its PAM services in `/usr/lib/pam.d/`** (`kde`, `kde-fingerprint`, `kde-smartcard`), not `/etc/pam.d/`. A file of the same name in `/etc/pam.d/` replaces the vendor one whole, so an override must copy all of it. `kde-smartcard` waits for a card (`pam_pkcs11 wait_for_card`) in parallel with the password prompt.
- **The YubiKey Bio unlocks Plasma through `pam_u2f` in `/etc/pam.d/kde-fingerprint`** (`desktop.py`), placed three times before `pam_fprintd` (`[success=5|3|1 default=ignore]`), one fingerprint read per call, so three tries: lid closed, fprintd would wait on an unreachable sensor. On framework-gab it works lid closed and with the key absent (the Goodix still answers). On desktop-gab, which has no `fprintd`, the missing `-auth required` module counts as a failure: the screen does not unlock by itself with the key absent. Without the key, `pam_u2f` fails at once and kscreenlocker never reruns the stack, so a lock taken while the KVM was switched away (the key behind it disconnected) left the key unused once back: `u2f-wait-key`, a `pam_exec` placed before each try, waits for the key to show up, unless a lid is open. Placed only before the first, a key that vanished for a second after the prompt (a KVM switch, a failed USB reset on resume) burned the three tries at once (verified 23/10/2026). The mapping in `files/desktop/u2f_mappings` holds only a key handle and a public key; its common origin `pam://gab` serves both hosts. `pamu2fcfg` prints nothing while it waits for a touch.
- **ufw overrides sysctl at start with `/etc/ufw/sysctl.conf`**, which sets `rp_filter=1` (strict) and breaks the Tailscale exit node. decman owns that file with `rp_filter=2`. After a ufw upgrade, merge the `.pacnew`.
- **Docker bypasses ufw.** It DNATs published ports in `nat PREROUTING` and accepts them in `DOCKER-FORWARD`, ahead of ufw's chains, so a plain `-p 8080:80` was reachable from the LAN. `/etc/docker/daemon.json` (`"ip": "127.0.0.1"`) binds published ports to localhost; `-p 0.0.0.0:…` opens one on purpose.
- **ufw rules go in `Desktop.after_update`, not `on_change`.** `on_change` only fires when a module's files, packages or units change, never when its code does, so a rule added there never reaches existing machines. ufw skips a rule already present.
- **ufw denies all incoming traffic, SSH included.** The real machines run no SSH server; they are reached by Tailscale SSH (`tailscale up --ssh`), which `tailscaled` serves itself and which bypasses ufw (verified). In the VM, chain `sudo ufw allow ssh` in the same command as the first real decman run: the running session survives (established connections pass), new ones do not (recovery: a TTY via `virsh send-key`).
- **nix comes from pacman (`apps.py`), for the repos that have a flake.** decman owns `/etc/nix/nix.conf`, which the package also owns (merge the `.pacnew` after an upgrade), to enable flakes. The daemon is socket-activated (`nix-daemon.socket`). No `nix-users` group: the Arch package only creates `nixbld`, and Nix's default `allowed-users = *` lets every user reach the daemon.
- **Keep the AUR minimal: it was most of the babysitting.** Over three weeks, `claude-code` was rebuilt 11 times, J-Link (pulled in by `nrfconnect-appimage`) 3 times. What updates often leaves for upstream channels: Claude Code from its native installer, `fresh` from mise (both in dotfiles), RustDesk as a Flatpak. To rank what is left: count `upgraded <pkg>` per `pacman -Qqm` package in `/var/log/pacman.log`, and the PKGBUILD commits over a year in its AUR git repo.
- **J-Link is frozen** (`source.py`): added to `decman.aur.ignored_packages` once installed, so a new machine gets the latest and later runs never rebuild it (about 50 releases a year; an old one is fine). nRF Connect needs it even only to measure power with the PPK2: its launcher blocks without J-Link, its "Install" runs `pkexec dpkg -i` and fails on Arch, and the PPK2 is not found. nRF Connect itself (3 releases a year) is not frozen. To update J-Link: `sudo pacman -Rns nrfconnect-appimage`, then `sudo decman`.
- **AUR sources are kept between builds** (`SRCDEST` in `base.py`, `makechrootpkg` bind-mounts it): the limine packages are Java built with GraalVM native-image, and no longer download the ~300 MiB JDK at every rebuild (about every two weeks each). systemd-tmpfiles drops what went unused for 90 days.
- **gpg-agent is the SSH agent, set up by dotfiles**, whose `CLAUDE.md` holds its gotchas. In VM tests, never run `gpg-connect-agent updatestartuptty` from a display-less ssh command: it wipes the display pinentry uses.

## Boundary with dotfiles

The user side lives in the `dotfiles` repo (chezmoi, `main`, cloned at `~/.local/share/chezmoi`), whose `CLAUDE.md` holds the chezmoi gotchas. dotfiles serves four machines, two of them work machines on Ubuntu and Debian; this repo serves only the Arch desktops. Where a thing goes:
- **Here (decman):** anything that needs root or is specific to Arch: packages, `/etc`, system units, udev, groups, plus the tools that must exist before chezmoi and mise run (`base.py`).
- **dotfiles:** anything under `$HOME`, including user units and Plasma settings. A CLI tool also wanted on the work machines comes from mise there; one that only matters on Arch, or that mise cannot build, comes from pacman here.

This repo owns the list of tools dotfiles relies on that come from pacman instead of mise:
- **needed before mise:** `fish`, `fisher`, `gnupg`, `git-crypt`, `chezmoi`, `mise` (`base.py`); dotfiles disables the mise copies of chezmoi and git-crypt on Arch;
- **absent from mise:** `luarocks`, `luacheck`, `busted` (`apps.py`);
- **called outside an interactive fish**, where mise is not activated: `git-lfs` (git filter marked `required`), `jq` (Claude Code statusline).

On the work machines the same tools come from apt (laptop) or a local mise config (server).

## Working rules

- Never decrypt, print or modify secrets: git-crypt files in dotfiles, agenix files in nixos-config. The user runs re-encryption scripts themselves.
- No commit or push without the user's go. The user reviews at the end of each phase.
- Never touch `srv-1` in nixos-config.
- In the VM, drive interactive decman runs with `vm/answer.py`, type the LUKS passphrase with `virsh send-key`, and never pass `pkill -f` a pattern that matches your own ssh command line.
