# Source decman : sudo decman --source /chemin/vers/decman/source.py
# Les modules communs d'abord, puis ce qui dépend de l'hôte (choisi par hostname).
import os
import socket
import subprocess

import decman
from decman.extras.gpg import GPGReceiver
from decman.extras.users import User, UserManager

from base import BUILD_USER, USER, Base
from amd import Amd
from apps import Apps
from boot import Boot
from desktop import Desktop
from framework_gab import FrameworkGab
from intel import Intel
from maintenance import Maintenance

# Un fichier /etc appartenant à un paquet pas encore installé ferait échouer pacman
# (« existe déjà dans le système de fichiers ») : on installe d'abord, on écrit ensuite.
decman.execution_order = ["pacman", "aur", "flatpak", "files", "systemd"]

# Par hôte : paramètres noyau en plus de ceux de boot.py, et modules propres.
HOSTS = {
    "framework-gab": ((), [Intel(), FrameworkGab()]),
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

# J-Link (dépendance de nrfconnect-appimage, pour le PPK2) est figé : installé à sa dernière
# version sur une machine neuve, puis jamais mis à jour. Il sort une version par semaine, et une
# ancienne suffit. Pour le mettre à jour : sudo pacman -Rns nrfconnect-appimage, puis sudo decman.
JLINK = "jlink-software-and-documentation"
if subprocess.run(["pacman", "-Q", JLINK], capture_output=True).returncode == 0:
    decman.aur.ignored_packages.add(JLINK)

decman.modules += [Base(), Boot(kernel_params), Desktop(), Apps(), *host_modules, Maintenance(USER), users, keys]
