# Session Plasma et services système du bureau : tout ce qui ne dépend pas de la machine.
from decman import File, Module, prg
from decman.plugins import flatpak, pacman, systemd, aur

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
            "ttf-jetbrains-mono-nerd", "ttf-fira-sans", "ttf-montserrat", "ttf-opensans",
            "bluez", "bluez-utils", "cups", "fwupd",
            "docker", "docker-buildx", "tailscale", "ufw", "flatpak",
            "usbmuxd", "libimobiledevice", "ifuse",  # iPhone
            # VM (virt-manager) : dnsmasq pour le réseau NAT « default », swtpm pour un TPM virtuel
            "libvirt", "qemu-desktop", "virt-manager", "virtiofsd", "swtpm", "edk2-ovmf", "dnsmasq",
            "pam-u2f", "yubikey-manager",  # YubiKey Bio au verrouillage ; ykman pour enrôler les empreintes
        }

    @aur.packages
    def aur_packages(self) -> set[str]:
        return {
            "ttf-ms-fonts",
        }

    @flatpak.packages
    def flatpak_packages(self) -> set[str]:
        # La branche beta se pose à la main (README, « Après la première connexion ») : decman ne gère ni remotes ni branches.
        return {"com.prusa3d.PrusaSlicer", "org.fkoehler.KTailctl"}

    @systemd.units
    def units(self) -> set[str]:
        return {
            "plasmalogin.service", "bluetooth.service", "cups.socket",
            "docker.socket", "tailscaled.service", "ufw.service", "libvirtd.socket",
            # Métadonnées seulement : les firmwares s'installent à la main (fwupdmgr update).
            "fwupd-refresh.timer", "flatpak-update.timer",
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
            # Empreinte au verrouillage par la YubiKey Bio, derrière le KVM. Le mapping (pamu2fcfg,
            # origine commune pam://gab) ne contient qu'un handle et une clé publique.
            "/etc/u2f_mappings": File(source_file="./files/desktop/u2f_mappings"),
            "/etc/pam.d/kde-fingerprint": File(source_file="./files/desktop/kde-fingerprint"),
            "/usr/local/bin/u2f-wait-key": File(
                source_file="./files/desktop/u2f-wait-key", permissions=0o755
            ),
            # rp_filter lâche pour l'exit node Tailscale : voir le fichier.
            "/etc/ufw/sysctl.conf": File(source_file="./files/desktop/ufw-sysctl.conf"),
            # Docker accepte un port publié avant les chaînes ufw : un -p 8080:80 serait ouvert au
            # LAN. Les ports publiés n'écoutent que sur localhost, sauf -p 0.0.0.0:8080:80 explicite.
            "/etc/docker/daemon.json": File(content='{"ip": "127.0.0.1"}\n'),
            "/etc/systemd/system/flatpak-update.service": File(
                source_file="./files/desktop/flatpak-update.service"
            ),
            "/etc/systemd/system/flatpak-update.timer": File(
                source_file="./files/desktop/flatpak-update.timer"
            ),
        }

    # Aussi appelé au premier run.
    def on_change(self, store) -> None:
        # Docker ne relit daemon.json qu'au démarrage ; try-restart ne démarre pas un daemon arrêté.
        prg(["systemctl", "try-restart", "docker.service"])
        prg(["ufw", "default", "deny", "incoming"])
        prg(["ufw", "default", "allow", "outgoing"])
        prg(["ufw", "--force", "enable"])

    # À chaque run, après on_change : on_change ne voit pas un changement de ce code, seulement des
    # fichiers, paquets et unités. ufw ignore une règle déjà présente ; une règle retirée d'ici
    # reste active, à supprimer à la main (ufw delete).
    def after_update(self, store) -> None:
        for proto in ("tcp", "udp"):
            prg(["ufw", "allow", f"1714:1764/{proto}", "comment", "KDE Connect"])
        # Réseau NAT « default » de libvirt : DHCP et DNS de dnsmasq vers l'hôte, trafic des VM
        # vers l'extérieur. Sans ça, ufw les bloque et une VM n'obtient pas d'IP.
        prg(["ufw", "allow", "in", "on", "virbr0", "comment", "libvirt"])
        prg(["ufw", "route", "allow", "in", "on", "virbr0", "comment", "libvirt"])
