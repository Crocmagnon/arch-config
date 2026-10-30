# Processeur et GPU AMD (desktop-gab).
import re

from decman import File, Module, prg
from decman.plugins import pacman, systemd


class Amd(Module):
    def __init__(self) -> None:
        super().__init__("amd")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        # Déclarer le pilote Vulkan évite que pacman demande lequel installer pour Steam.
        return {"amd-ucode", "vulkan-radeon", "lib32-vulkan-radeon"}

    def files(self) -> dict[str, File]:
        return {
            # Écran noir au réveil derrière le KVM : journaliser les connecteurs et forcer une redétection.
            "/usr/lib/systemd/system-sleep/drm-redetect": File(
                source_file="./files/amd/drm-redetect", permissions=0o755
            ),
            # Réveils lents (19 à 54 s) ou figés jusqu'au reboot forcé (23 et 30/10/2026) : la durée de
            # chaque périphérique au réveil dans le journal, et une panique, gardée dans les variables
            # EFI (efi_pstore, source.py), si le réveil reste bloqué. Un blocage de plus de 120 s hors
            # veille redémarre aussi la machine : à retirer une fois la cause trouvée.
            "/etc/tmpfiles.d/resume-debug.conf": File(content="w /sys/power/pm_print_times - - - - 1\n"),
            "/etc/sysctl.d/90-resume-debug.conf": File(
                content="kernel.hung_task_panic = 1\nkernel.softlockup_panic = 1\n"
                "kernel.hardlockup_panic = 1\nkernel.panic = 10\n"
            ),
        }

    @systemd.units
    def units(self) -> set[str]:
        # Archive au démarrage le dmesg d'une panique dans /var/lib/systemd/pstore.
        return {"systemd-pstore.service"}

    # Aussi appelé au premier run.
    def on_change(self, store) -> None:
        prg(["systemd-tmpfiles", "--create", "/etc/tmpfiles.d/resume-debug.conf"])
        prg(["sysctl", "--system"])

    # Avant le pacman -Syu de decman. Réveils figés sous linux 7.2.11 (4 sur ~20 depuis le 18/10/2026),
    # aucun sous 7.2.7 à 7.2.9 (~40) : rester en 7.2.9 le temps de le confirmer. pacman.conf
    # appartient au paquet pacman, d'où une modification en place plutôt qu'un File. À retirer avec
    # la ligne IgnorePkg une fois la question tranchée.
    def before_update(self, store) -> None:
        conf = "/etc/pacman.conf"
        with open(conf) as f:
            text = f.read()
        pinned = re.sub(r"^#?IgnorePkg\s*=.*$", "IgnorePkg   = linux", text, count=1, flags=re.M)
        if pinned != text:
            with open(conf, "w") as f:
                f.write(pinned)
