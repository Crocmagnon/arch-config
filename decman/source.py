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

# Un fichier /etc appartenant à un paquet pas encore installé ferait échouer pacman
# (« existe déjà dans le système de fichiers ») : on installe d'abord, on écrit ensuite.
decman.execution_order = ["pacman", "aur", "flatpak", "files", "systemd"]

KERNEL_PARAMS = {
    "framework-gab-amd": ("amdgpu.dcdebugmask=0x10",),  # PSR (nixos-hardware)
    "desktop-gab": ('acpi_osi="!Windows 2015"',),  # veille sur la B650 (nixos-hardware)
}

host = socket.gethostname()
if host not in KERNEL_PARAMS:
    raise SystemExit(f"hôte inconnu : {host}")

# Groupes créés par des paquets : appliqués en after_update, une fois les paquets installés.
# docker ; uucp pour les ports série (dialout sous NixOS) ; input pour Rotatrix.
users = UserManager()
for group in ("docker", "uucp", "input"):
    users.add_user_to_group(USER, group)

# Builds AUR : un utilisateur dédié, dont le trousseau reçoit les clés des sources signées
# (configuration recommandée par la doc AUR de decman). nobody, l'utilisateur par défaut, n'a
# pas de trousseau : toute source signée échoue.
BUILD_HOME = "/var/lib/builduser"
users.add_user(User(username="builduser", home=BUILD_HOME, system=True))
os.environ["GNUPGHOME"] = f"{BUILD_HOME}/gnupg"
decman.aur.makepkg_user = "builduser"
keys = GPGReceiver()
keys.receive_key(  # libudev0-shim, dépendance de jlink-software-and-documentation (nRF Connect)
    user="builduser", gpg_home=f"{BUILD_HOME}/gnupg",
    fingerprint="8703B6700E7EE06D7A39B8D6EDAE37B02CEB490D", keyserver="hkps://keyserver.ubuntu.com",
)

decman.modules += [Base(), Boot(KERNEL_PARAMS[host]), Desktop(), Apps(), Amd(), users, keys]
