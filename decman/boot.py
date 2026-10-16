# Limine, ligne de commande du noyau et snapshots démarrables (l'équivalent des générations NixOS).
#
# snap-pac prend un snapshot avant et après chaque transaction pacman ; limine-snapper-sync en fait
# des entrées du menu Limine, chacune avec son propre noyau. limine-mkinitcpio-hook génère les
# entrées dans /boot/limine.conf à partir de /etc/kernel/cmdline.
import os
import re

from decman import File, Module, prg
from decman.plugins import aur, pacman, systemd

# Sans cryptdevice= : c'est l'initramfs systemd qui ouvre LUKS, via /etc/crypttab (x-initrd.attach).
CMDLINE = "root=/dev/mapper/root rootflags=subvol=@ rw rootfstype=btrfs zswap.enabled=0 quiet splash"
ARCHINSTALL_EFI_LABEL = "Arch Linux Limine Bootloader"


class Boot(Module):
    def __init__(self, kernel_params: tuple[str, ...] = ()) -> None:
        super().__init__("boot")
        self.cmdline = " ".join((CMDLINE, *kernel_params))

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {"snapper", "snap-pac", "terminus-font"}  # terminus-font : voir vconsole.conf

    @aur.packages
    def aur_packages(self) -> set[str]:
        return {"limine-mkinitcpio-hook", "limine-snapper-sync"}

    # Pas de limine-snapper-sync.service : sans inotify-tools il s'arrête aussitôt et laisse la main
    # au plugin snapper, appelé à chaque création ou suppression de snapshot, ce qui suffit.
    @systemd.units
    def units(self) -> set[str]:
        return {"snapper-cleanup.timer"}

    def files(self) -> dict[str, File]:
        return {
            "/etc/kernel/cmdline": File(content=self.cmdline + "\n"),
            "/etc/default/limine": File(content="ESP_PATH=/boot\n"),
            # Les HOOKS d'archinstall (custom_commands de user_configuration.json, à garder identiques),
            # plus sd-btrfs-overlayfs : un snapshot est en lecture seule, ce hook monte une couche
            # temporaire en écriture par-dessus pour démarrer. Il vient de l'AUR, d'où son absence là-bas.
            # thunderbolt ouvre le tunnel DP d'un dock USB4 : sans lui dans l'initramfs, l'écran du
            # dock reste noir à l'invite LUKS (framework-gab). Sans effet sur une machine sans USB4.
            "/etc/mkinitcpio.conf.d/10-hooks.conf": File(content=(
                "MODULES=(thunderbolt)\n"
                "HOOKS=(base systemd autodetect microcode modconf kms keyboard sd-vconsole block plymouth"
                " sd-encrypt filesystems sd-btrfs-overlayfs fsck)\n"
            )),
            # Police de console de 22 px, lisible sur les écrans du laptop et du desktop, pour les TTY
            # et les logs de démarrage. Le hook sd-vconsole la copie dans l'initramfs, que
            # on_change régénère.
            "/etc/vconsole.conf": File(content="KEYMAP=fr\nFONT=ter-122n\n"),
        }

    # Aussi appelé au premier run : régénère initramfs et entrées (cmdline, HOOKS, police de console).
    def on_change(self, store) -> None:
        prg(["limine-update"])

    # Une seule fois : snapper, puis bascule de l'installation Limine d'archinstall vers celle de
    # limine-mkinitcpio-hook (binaire déjà déployé par son hook pacman à l'installation).
    # L'ancienne n'est retirée qu'une fois la nouvelle vérifiée : sinon, plus de démarrage.
    def on_enable(self, store) -> None:
        # Relancé tant que la vérification ci-dessous échoue : create-config refuse une config existante.
        if not os.path.exists("/etc/snapper/configs/root"):
            prg(["snapper", "--no-dbus", "-c", "root", "create-config", "/"])
        prg(["snapper", "--no-dbus", "-c", "root", "set-config", "TIMELINE_CREATE=no", "NUMBER_LIMIT=10"])

        prg(["limine-update"])
        entries = prg(["efibootmgr"], pty=False)
        with open("/boot/limine.conf") as f:
            conf = f.read()
        if not (
            os.path.exists("/boot/EFI/limine/limine_x64.efi")
            and re.search(r"\\EFI\\limine\\limine_x64\.efi", entries, re.I)
            and "vmlinuz" in conf
        ):
            raise RuntimeError("nouvelle installation Limine incomplète : l'ancienne est conservée")

        prg(["rm", "-rf", "/boot/EFI/arch-limine", "/etc/pacman.d/hooks/99-limine.hook",
             "/boot/vmlinuz-linux", "/boot/initramfs-linux.img"])
        for num in re.findall(rf"^Boot([0-9A-F]{{4}})\* {re.escape(ARCHINSTALL_EFI_LABEL)}\b", entries, re.M):
            prg(["efibootmgr", "--quiet", "--bootnum", num, "--delete-bootnum"])
