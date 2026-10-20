# Ce qu'il faut sur toutes les machines, avec ou sans bureau.
from decman import File, Module, prg
from decman.plugins import aur, pacman, systemd

USER = "gaugendre"


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
            # Outils de base, aussi pour root.
            "vim", "ripgrep",
            "pacman-contrib",  # paccache.timer, l'équivalent de nix gc ; checkupdates
            "reflector",  # miroirs (reflector.conf ci-dessous)
            "man-db", "man-pages",
            # Garde les modules du noyau en cours après sa mise à jour (bridge pour docker…),
            # linux-modules-cleanup.service les supprime au démarrage suivant.
            "kernel-modules-hook",
        }

    @aur.packages
    def aur_packages(self) -> set[str]:
        return {"decman"}

    @systemd.units
    def units(self) -> set[str]:
        return {"NetworkManager.service", "paccache.timer", "man-db.timer",
                "linux-modules-cleanup.service", "pacman-download.timer", "reflector.timer"}

    def files(self) -> dict[str, File]:
        return {
            # Miroirs à jour (synchronisés il y a moins d'une heure) et rapides, chaque semaine
            # (reflector.timer). Parmi les 25 synchronisés le plus récemment près d'ici, les 10 au
            # meilleur débit mesuré. Le mirrorlist.pacnew de pacman-mirrorlist est supprimé
            # (maintenance.py).
            "/etc/xdg/reflector/reflector.conf": File(content=(
                "--save /etc/pacman.d/mirrorlist\n"
                "--protocol https\n"
                "--country France,Germany,Netherlands,Belgium,Switzerland\n"
                "--delay 1\n"
                "--latest 25\n"
                "--sort rate\n"
                "--number 10\n"
                "--download-timeout 5\n"
            )),
            # Même chemin que celui d'archinstall, pour le remplacer plutôt que l'empiler.
            f"/etc/sudoers.d/00_{USER}": File(
                content=f"{USER} ALL=(ALL) NOPASSWD: SETENV: ALL\n", permissions=0o440
            ),
            "/etc/locale.gen": File(source_file="./files/base/locale.gen"),
            "/etc/locale.conf": File(source_file="./files/base/locale.conf"),
            # Télécharge seulement : la mise à jour reste un sudo decman à la main (news, .pacnew).
            "/etc/systemd/system/pacman-download.service": File(
                source_file="./files/base/pacman-download.service"
            ),
            "/etc/systemd/system/pacman-download.timer": File(
                source_file="./files/base/pacman-download.timer"
            ),
            # makepkg compile sur un seul cœur par défaut (MAKEFLAGS commenté). makechrootpkg, qui
            # sert aux builds AUR de decman, reprend ce MAKEFLAGS dans son chroot.
            "/etc/makepkg.conf.d/parallel.conf": File(content='MAKEFLAGS="-j$(nproc)"\n'),
        }

    # Aussi appelé au premier run, avec on_enable.
    def on_change(self, store) -> None:
        prg(["locale-gen"])
        # decman active les unités sans les démarrer : sans ça, timer et premier tri attendraient
        # le prochain démarrage.
        prg(["systemctl", "start", "reflector.timer", "reflector.service"])

    # usermod plutôt qu'un User() de UserManager : celui-ci alignerait aussi les groupes sur sa
    # liste, et retirerait gaugendre de wheel et des groupes ajoutés dans source.py.
    def on_enable(self, store) -> None:
        prg(["usermod", "--shell", "/usr/bin/fish", USER])

    # Nom affiché (GECOS) : à chaque run, pour atteindre aussi les machines déjà installées.
    def after_update(self, store) -> None:
        prg(["usermod", "--comment", "Gabriel", USER])
