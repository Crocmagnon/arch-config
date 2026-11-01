# Framework 13 Pro Intel : hibernation, empreinte, KVM, cartes d'extension.
from decman import File, Module, prg
from decman.plugins import aur, pacman, systemd

FILES = "./files/framework-gab"


class FrameworkGab(Module):
    def __init__(self) -> None:
        super().__init__("framework-gab")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {
            "fprintd",  # le verrouillage Plasma l'utilise via kde-fingerprint (fourni par kscreenlocker) ; pas le login
            "power-profiles-daemon", "iio-sensor-proxy",  # profils d'énergie, luminosité auto
            "framework-system",  # framework_tool
            "powertop", "acpi",  # mesure de la batterie
        }

    @systemd.units
    def units(self) -> set[str]:
        return {
            "power-profiles-daemon.service",
        }

    def files(self) -> dict[str, File]:
        return {
            # Veille, puis hibernation au bout d'une heure (déclenchée par powerdevil, SleepMode=3).
            # Reprise sans resume= : l'initramfs systemd lit la variable EFI HibernateLocation.
            # HibernateMode=shutdown : écrire l'image puis s'éteindre, sans entrer en ACPI S4. En S4,
            # le Framework 13 AMD se rallumait tout seul au bout de quelques secondes (constaté sous
            # NixOS, puis sous Arch le 28/09/2026) ; gardé sur ce modèle, où il marche (vérifié le 14/10/2026).
            "/etc/systemd/sleep.conf.d/hibernate.conf": File(
                content="[Sleep]\nHibernateDelaySec=60min\nHibernateMode=shutdown\n"
            ),
            # Après une hibernation de plus de 5 min, la passphrase LUKS vient d'être saisie : lever
            # le verrouillage de Plasma. Les hooks de veille ne sont lus que dans /usr/lib.
            "/usr/lib/systemd/system-sleep/unlock-after-hibernate": File(
                source_file=f"{FILES}/unlock-after-hibernate", permissions=0o755
            ),
            # La webcam réveille la machine à chaque mise en veille : couper son port pendant la veille.
            "/usr/lib/systemd/system-sleep/webcam-port-off": File(
                source_file=f"{FILES}/webcam-port-off", permissions=0o755
            ),
            # Clavier et souris derrière le KVM : réveil par USB (le KVM rattache le hub à chaque
            # bascule, un réglage ponctuel ne survivrait pas).
            "/etc/udev/rules.d/90-usb-wakeup.rules": File(
                content='ACTION=="add", SUBSYSTEM=="usb", DRIVER=="usb", TEST=="power/wakeup", ATTR{power/wakeup}="enabled"\n'
            ),
        }

    # Aussi appelé au premier run.
    def on_change(self, store) -> None:
        # Menu Limine lisible : police doublée. limine-update relit limine.conf et garde ses options
        # globales (vérifié le 28/09/2026), il suffit donc de l'ajouter une fois. Sans ligne timeout:,
        # sed n'insère rien sans erreur : le second grep fait alors échouer le hook.
        prg(["sh", "-c", "grep -q '^term_font_scale:' /boot/limine.conf"
             " || { sed -i '/^timeout:/i term_font_scale: 2x2' /boot/limine.conf"
             " && grep -q '^term_font_scale:' /boot/limine.conf; }"])
