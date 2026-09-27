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
- **GnuPG stays in `~/.gnupg`.** gpg-agent is the SSH agent, and Arch does not export `SSH_AUTH_SOCK` for it. chezmoi handles that.

## Working rules

- Never decrypt, print or modify secrets: git-crypt files in dotfiles, agenix files in nixos-config. The user runs re-encryption scripts themselves.
- No commit or push without the user's go. The user reviews at the end of each phase.
- Never touch `srv-1` in nixos-config.
- In the VM, drive interactive decman runs with `vm/answer.py`, type the LUKS passphrase with `virsh send-key`, and never pass `pkill -f` a pattern that matches your own ssh command line.
