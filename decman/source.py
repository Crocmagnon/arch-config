# Source decman : sudo decman --source /chemin/vers/decman/source.py
# Les modules communs d'abord, puis ce qui dépend de l'hôte (choisi par hostname).
import socket

import decman
from base import Base
from boot import Boot

# Un fichier /etc appartenant à un paquet pas encore installé ferait échouer pacman
# (« existe déjà dans le système de fichiers ») : on installe d'abord, on écrit ensuite.
decman.execution_order = ["pacman", "aur", "files", "systemd"]

KERNEL_PARAMS = {
    "framework-gab-amd": ("amdgpu.dcdebugmask=0x10",),  # PSR (nixos-hardware)
    "desktop-gab": ('acpi_osi="!Windows 2015"',),  # veille sur la B650 (nixos-hardware)
}

host = socket.gethostname()
if host not in KERNEL_PARAMS:
    raise SystemExit(f"hôte inconnu : {host}")

decman.modules += [Base(), Boot(KERNEL_PARAMS[host])]
