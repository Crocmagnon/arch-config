# CLAUDE.md

Guidance for Claude Code in this repository. Keep it and `README.md` current: update both whenever a module, a decision or a procedure changes, not at the end.

## What this is

Declarative Arch Linux config for the user's desktops (`framework-gab-amd`, `desktop-gab`, later `framework-gab`):
- archinstall for disk and boot;
- decman for system packages, `/etc` files, systemd units and snapshots;
- user files live in the separate chezmoi `dotfiles` repo.

`MIGRATION.md` holds the NixOS → Arch inventory, every settled decision (§0) and the phased plan (§9). Read §0 before changing anything.

## Commands

```sh
archinstall/render.sh <hostname> <disk> > config.json      # on the ISO
archinstall --config config.json --creds creds.json --silent
sudo decman --source decman/source.py --dry-run --debug     # always first
sudo decman --source decman/source.py                       # first real run: remembers the path
sudo decman                                                 # later runs (dry-run never stores it)
python3 -m py_compile decman/*.py                           # quick syntax check
```

Test in the VM bench (`vm/README.md`) before touching real hardware: `vm/state.sh save|reset|list`.

## Architecture

- `decman/source.py`: entry point. Sets `decman.execution_order`, maps hostname to kernel params and modules, and refuses unknown hosts.
- One module per concern (`base.py`, `boot.py`, …), then host modules. Files owned by a module live in `decman/files/<module>/`.
- `archinstall/user_configuration.json` has placeholders (`@HOSTNAME@`, `@DEVICE@`, `"@ROOT_MIB@"`) filled by `render.sh`.

## Rules and gotchas (all verified; see MIGRATION.md for sources)

- **decman removes every explicit package that is not declared, and every orphan.** An optional dependency counts as an orphan: that is why `wpa_supplicant` is declared, since without it the laptop loses Wi-Fi. Declare meta-packages, never groups. Before a first real run, compare `--dry-run` with `pacman -Qqe`.
- **Execution order is `pacman, aur, files, systemd`.** Writing a file that a not-yet-installed package owns would make pacman fail.
- **decman enables units, never starts them.** It only touches units that are, or were, declared.
- **`on_change` also runs on the first run, together with `on_enable`.** Do not repeat work in both.
- **Never manage `/boot/limine.conf`.** limine-mkinitcpio-hook generates it from `/etc/kernel/cmdline`, and limine-snapper-sync adds the snapshot entries. Its checksum is enrolled in the Limine binary, so hand edits break boot.
- **Initramfs hooks live in `/etc/mkinitcpio.conf.d/10-hooks.conf`.** archinstall writes it, and `boot.py` takes it over and adds `sd-btrfs-overlayfs`, which is required to boot a read-only snapshot and only exists once the AUR package is installed.
- **The LUKS root is in `/etc/crypttab` with `x-initrd.attach`.** `crypttab.initramfs` is deprecated in mkinitcpio 42. UUIDs are per install and never go in git.
- **archinstall 4.4 bugs and limits:**
  - `btrfs_options` from JSON is ignored (string vs `Path` compare), so snapper is set up in `boot.py`.
  - Sizes must be absolute, no `Percent`, hence `render.sh`.
  - The swap partition cannot be encrypted cleanly, hence a btrfs swapfile.
  - `custom_commands` run after the bootloader and before `genfstab`.
- **systemd-sleep hooks go in `/usr/lib/systemd/system-sleep/`.** `/etc/systemd/system-sleep/` only works on NixOS.
- **Arch groups:** serial ports are `uucp`, not `dialout`, and libvirt is `libvirt`, not `libvirtd`.
- **AUR builds run as `builduser`** (a system user). PGP keys for signed sources are received into its keyring by `GPGReceiver` in `source.py`, with one comment per key naming the package that needs it. The default `nobody` has no keyring, so any signed source fails.
- **Never declare a package that another declared AUR package already pulls in** (for example `nrf-udev`, a dependency of `nrfconnect-appimage`). The AUR step installs it as a dependency, and every later run tries to install it again.
- **Declare the provider whenever pacman would ask which package provides a virtual dependency.** Otherwise real installs prompt, and the default can be wrong: for `tessdata`, the default is Afrikaans. Declared so far: `pipewire-jack`, `qt6-multimedia-ffmpeg`, `tesseract-data-eng`, `tesseract-data-fra`, `vulkan-radeon`, `lib32-vulkan-radeon`. After a VM run, list the prompts with `grep -a -A3 "providers available"` on the log.
- **Flatpak needs two runs.** The decman flatpak plugin is probed at startup, before pacman installs `flatpak`, so the first run skips it with a warning.
- **The autologin wallet is served by `ksecretd`** (KWallet 6), which owns `org.freedesktop.secrets` and is unlocked by PAM. Check it with the Secret Service `Locked` property of `/org/freedesktop/secrets/collection/kdewallet`. The legacy `org.kde.kwalletd6` name is a separate process that reports the wallet closed; whether apps using it re-prompt is still to be checked.
- **ufw denies all incoming traffic.** In the VM, keep port 22 open, or you lock yourself out of the SSH that drives it.
- **GnuPG stays in `~/.gnupg`.** gpg-agent is the SSH agent, and Arch does not export `SSH_AUTH_SOCK` for it. chezmoi handles that.

## dotfiles (chezmoi) gotchas

The chezmoi side lives in the `dotfiles` repo (branch `arch-migration`).
- **Templates run with `missingkey=error`:** use `get . "work"`, never `.work`. Machines that have not re-run `chezmoi init` lack the key.
- **`{{-` also eats the newline before the tag, gluing headings together.** Put tags on their own line with `-}}` only.
- **chezmoi skips only truly empty renders:** a lone `\n` still creates the file.
- **Never template a file that already contains `{{`** (kitty.conf has 23 in its comments). Include a small templated file instead (`shell.conf`).
- **Test renders without touching `$HOME`:** `nix shell nixpkgs#chezmoi --command chezmoi --config <tmp.toml> --source . --destination <tmp> execute-template` or `managed`. `--promptBool` matches the prompt *text*, not the key.
- **Once dotfiles is unlocked, never print a rendered template that includes a secret.** Use `chezmoi apply` without `-v`, and `chezmoi status` for names only.

## Before real hardware

- Remove the temporary `ufw allow ssh` from `decman/desktop.py` (VM iterations only), and delete the rule on any machine that got it (`ufw delete allow ssh`).

## Working rules

- Never decrypt, print or modify secrets: git-crypt files in dotfiles, agenix files in nixos-config. The user runs re-encryption scripts themselves.
- No commit or push without the user's go. The user reviews at the end of each phase.
- Never touch `srv-1` in nixos-config.
- In the VM, drive interactive decman runs with `vm/answer.py`, type the LUKS passphrase with `virsh send-key`, and never pass `pkill -f` a pattern that matches your own ssh command line.
