# Source decman : sudo decman --source /chemin/vers/decman/source.py
# Les modules communs d'abord, puis ce qui dépend de l'hôte (choisi par hostname).
import os
import socket

import decman
from decman.extras.gpg import GPGReceiver
from decman.extras.users import User, UserManager

from base import USER, Base
from amd import Amd
from apps import Apps
from boot import Boot
from desktop import Desktop
from framework_gab_amd import FrameworkGabAmd

# Un fichier /etc appartenant à un paquet pas encore installé ferait échouer pacman
# (« existe déjà dans le système de fichiers ») : on installe d'abord, on écrit ensuite.
decman.execution_order = ["pacman", "aur", "flatpak", "files", "systemd"]

# Par hôte : paramètres noyau en plus de ceux de boot.py, et modules propres.
HOSTS = {
    "framework-gab-amd": (
        (
            "amdgpu.dcdebugmask=0x10",  # PSR (nixos-hardware)
            # pstore EFI, désactivé par défaut dans le noyau Arch : trace d'un blocage d'hibernation.
            "efi_pstore.pstore_disable=0",
            # Fin du journal gardée à la panique : 10 Kio par défaut (compressés), trop court pour la
            # pile des 12 cœurs. Chaque Kio prend une variable EFI : la NVRAM est petite, rester sobre.
            "pstore.kmsg_bytes=20480",
        ),
        [Amd(), FrameworkGabAmd()],
    ),
    "desktop-gab": (
        ('acpi_osi="!Windows 2015"',),  # veille sur la B650 (nixos-hardware)
        [Amd()],
    ),
}

host = socket.gethostname()
if host not in HOSTS:
    raise SystemExit(f"hôte inconnu : {host}")
kernel_params, host_modules = HOSTS[host]

# Groupes créés par des paquets : appliqués en after_update, une fois les paquets installés.
# docker ; uucp pour les ports série (dialout sous NixOS) ; input pour Rotatrix ; libvirt.
users = UserManager()
for group in ("docker", "uucp", "input", "libvirt"):
    users.add_user_to_group(USER, group)

# Builds AUR : un utilisateur dédié, dont le trousseau reçoit les clés des sources signées
# (configuration recommandée par la doc AUR de decman). nobody, l'utilisateur par défaut, n'a
# pas de trousseau : toute source signée échoue.
BUILD_USER = "builduser"
BUILD_HOME = f"/var/lib/{BUILD_USER}"
BUILD_GNUPG = f"{BUILD_HOME}/gnupg"
users.add_user(User(username=BUILD_USER, home=BUILD_HOME, system=True))
os.environ["GNUPGHOME"] = BUILD_GNUPG
decman.aur.makepkg_user = BUILD_USER
# /tmp est un tmpfs (moitié de la RAM) : trop petit pour certains builds AUR.
decman.aur.build_dir = "/var/tmp/decman/build"
keys = GPGReceiver()
keys.receive_key(  # libudev0-shim, dépendance de jlink-software-and-documentation (nRF Connect)
    user=BUILD_USER, gpg_home=BUILD_GNUPG,
    fingerprint="8703B6700E7EE06D7A39B8D6EDAE37B02CEB490D", keyserver="hkps://keyserver.ubuntu.com",
)

decman.modules += [Base(), Boot(kernel_params), Desktop(), Apps(), *host_modules, users, keys]
