# Framework 13 AMD (Ryzen AI 300) : hibernation, empreinte, KVM, cartes d'extension.
from decman import File, Module
from decman.plugins import aur, pacman, systemd

FILES = "./files/framework-gab-amd"


class FrameworkGabAmd(Module):
    def __init__(self) -> None:
        super().__init__("framework-gab-amd")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {
            "fprintd",  # le verrouillage Plasma l'utilise via /etc/pam.d/kde-fingerprint ; pas le login
            "power-profiles-daemon", "iio-sensor-proxy",  # profils d'énergie, luminosité auto
            "framework-system",  # framework_tool
            "powertop", "acpi",  # mesure de la batterie
        }

    @aur.packages
    def aur_packages(self) -> set[str]:
        return {"powerstat"}

    @systemd.units
    def units(self) -> set[str]:
        return {"power-profiles-daemon.service"}

    def files(self) -> dict[str, File]:
        return {
            # Veille, puis hibernation au bout d'une heure (déclenchée par powerdevil, SleepMode=3).
            # Reprise sans resume= : l'initramfs systemd lit la variable EFI HibernateLocation.
            "/etc/systemd/sleep.conf.d/hibernate.conf": File(
                content="[Sleep]\nHibernateDelaySec=60min\n"
            ),
            # Après une hibernation de plus de 5 min, la passphrase LUKS vient d'être saisie : lever
            # le verrouillage de Plasma. Les hooks de veille ne sont lus que dans /usr/lib.
            "/usr/lib/systemd/system-sleep/unlock-after-hibernate": File(
                source_file=f"{FILES}/unlock-after-hibernate", permissions=0o755
            ),
            # Clavier et souris derrière le KVM : réveil par USB (le KVM rattache le hub à chaque
            # bascule, un réglage ponctuel ne survivrait pas).
            "/etc/udev/rules.d/90-usb-wakeup.rules": File(
                content='ACTION=="add", SUBSYSTEM=="usb", DRIVER=="usb", ATTR{power/wakeup}="enabled"\n'
            ),
            # Carte d'extension Ethernet Framework (Realtek) : autosuspend (nixos-hardware).
            "/etc/udev/rules.d/90-framework-ethernet.rules": File(
                content='ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="8156", ATTR{power/autosuspend}="20"\n'
            ),
            # Le BIOS déclare à tort le périphérique ACP, d'où une interface audio fantôme (nixos-hardware).
            "/etc/modprobe.d/framework-acp.conf": File(
                content="blacklist snd_acp70\nblacklist snd_acp_pci\n"
            ),
        }
