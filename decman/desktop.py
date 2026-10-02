# Session Plasma et services système du bureau : tout ce qui ne dépend pas de la machine.
from decman import File, Module, prg
from decman.plugins import flatpak, pacman, systemd

from base import USER


class Desktop(Module):
    def __init__(self) -> None:
        super().__init__("desktop")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {
            # plasma-meta tire plasma-login-manager, plasma-firewall et kwallet-pam, mais pas les
            # applications que NixOS installait avec Plasma.
            "plasma-meta", "ark", "dolphin", "dolphin-plugins", "elisa", "gwenview", "okular",
            "kate", "konsole", "khelpcenter", "kwalletmanager", "kdegraphics-thumbnailers",
            "ffmpegthumbs", "kio-admin", "kio-extras", "partitionmanager", "kdeconnect",
            "kitty", "wl-clipboard",
            # Fournisseurs à choisir, sinon pacman pose la question : backend multimédia de Qt, et
            # langues de l'OCR de Spectacle (le choix par défaut serait l'afrikaans).
            "qt6-multimedia-ffmpeg", "tesseract-data-eng", "tesseract-data-fra",
            "pipewire-alsa", "pipewire-pulse", "pipewire-jack", "wireplumber", "rtkit",  # jack : sinon pacman propose jack2
            "ttf-dejavu", "ttf-liberation", "noto-fonts", "noto-fonts-emoji",
            "ttf-jetbrains-mono-nerd", "ttf-fira-sans", "ttf-montserrat",
            "bluez", "bluez-utils", "cups", "fwupd",
            "docker", "tailscale", "ufw", "flatpak",
            "usbmuxd", "libimobiledevice", "ifuse",  # iPhone
            # VM (virt-manager) : dnsmasq pour le réseau NAT « default », swtpm pour un TPM virtuel
            "libvirt", "qemu-desktop", "virt-manager", "virtiofsd", "swtpm", "edk2-ovmf", "dnsmasq",
        }

    @flatpak.packages
    def flatpak_packages(self) -> set[str]:
        # La branche beta se pose à la main (README, « Après la première connexion ») : decman ne gère ni remotes ni branches.
        return {"com.prusa3d.PrusaSlicer"}

    @systemd.units
    def units(self) -> set[str]:
        return {
            "plasmalogin.service", "bluetooth.service", "cups.socket",
            "docker.socket", "tailscaled.service", "ufw.service", "libvirtd.socket",
        }

    def files(self) -> dict[str, File]:
        return {
            "/etc/plasmalogin.conf.d/autologin.conf": File(
                content=f"[Autologin]\nUser={USER}\nSession=plasma\n"
            ),
            # Wallet ouvert à l'autologin avec la passphrase LUKS (Arch Wiki, KDE Wallet) :
            # systemd-cryptsetup la laisse dans le trousseau du noyau, le service de connexion en
            # hérite, pam_systemd_loadkey la passe à pam_kwallet5.
            "/etc/systemd/system/plasmalogin.service.d/keyring.conf": File(
                content="[Service]\nKeyringMode=inherit\n"
            ),
            "/etc/pam.d/plasmalogin-autologin": File(
                source_file="./files/desktop/plasmalogin-autologin"
            ),
            # rp_filter lâche pour l'exit node Tailscale : voir le fichier.
            "/etc/ufw/sysctl.conf": File(source_file="./files/desktop/ufw-sysctl.conf"),
        }

    # Aussi appelé au premier run. ponytail: additif, ufw ignore une règle déjà présente ; une
    # règle retirée d'ici reste active, à supprimer à la main (ufw delete).
    def on_change(self, store) -> None:
        prg(["ufw", "default", "deny", "incoming"])
        prg(["ufw", "default", "allow", "outgoing"])
        for proto in ("tcp", "udp"):
            prg(["ufw", "allow", f"1714:1764/{proto}", "comment", "KDE Connect"])
        prg(["ufw", "--force", "enable"])
