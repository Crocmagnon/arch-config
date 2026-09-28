# Ce qu'il faut sur toutes les machines, avec ou sans bureau.
import decman
from decman import File, Module, prg
from decman.plugins import aur, pacman, systemd

USER = "gaugendre"

# /tmp est un tmpfs (moitié de la RAM) : trop petit pour certains builds AUR.
decman.aur.build_dir = "/var/tmp/decman/build"


class Base(Module):
    def __init__(self) -> None:
        super().__init__("base")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {
            # Installés par archinstall : à déclarer, sinon decman les retire.
            "base", "base-devel", "linux", "linux-firmware", "mkinitcpio",
            "btrfs-progs", "efibootmgr", "limine", "plymouth", "zram-generator",
            "sudo", "git", "networkmanager",
            # Wi-Fi : dépendance optionnelle de NetworkManager, donc orpheline pour decman.
            "wpa_supplicant",
            # openssh : le client ssh (le serveur n'est activé que dans la VM de test).
            "openssh",
            # Ce qui doit exister avant mise et chezmoi.
            "fish", "fisher", "gnupg", "git-crypt", "chezmoi", "mise",
            "vim", "ripgrep",
            "pacman-contrib",  # paccache.timer, l'équivalent de nix gc
            "man-db", "man-pages",
        }

    @aur.packages
    def aur_packages(self) -> set[str]:
        return {"decman"}

    @systemd.units
    def units(self) -> set[str]:
        return {"NetworkManager.service", "paccache.timer", "man-db.timer"}

    def files(self) -> dict[str, File]:
        return {
            # Même chemin que celui d'archinstall, pour le remplacer plutôt que l'empiler.
            "/etc/sudoers.d/00_gaugendre": File(
                content=f"{USER} ALL=(ALL) NOPASSWD: SETENV: ALL\n", permissions=0o440
            ),
            "/etc/locale.gen": File(source_file="./files/base/locale.gen"),
            "/etc/locale.conf": File(source_file="./files/base/locale.conf"),
            # makepkg compile sur un seul cœur par défaut (MAKEFLAGS commenté). makechrootpkg, qui
            # sert aux builds AUR de decman, reprend ce MAKEFLAGS dans son chroot.
            "/etc/makepkg.conf.d/parallel.conf": File(content='MAKEFLAGS="-j$(nproc)"\n'),
        }

    # Aussi appelé au premier run, avec on_enable.
    def on_change(self, store) -> None:
        prg(["locale-gen"])

    def on_enable(self, store) -> None:
        prg(["usermod", "--shell", "/usr/bin/fish", USER])
