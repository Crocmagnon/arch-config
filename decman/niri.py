# Essai de niri + Dux Shell, à côté de Plasma : une session de plus sur l'écran de connexion,
# l'autologin reste sur Plasma. Pour tout retirer : enlever Niri() de source.py, puis sudo decman.
from decman import File, Module
from decman.plugins import pacman


class Niri(Module):
    # autologin : ouvrir niri au démarrage au lieu de Plasma. Quitter niri (Ctrl+Alt+Suppr) mène à
    # l'écran de connexion, où Plasma reste au choix : Relogin est désactivé par défaut.
    def __init__(self, autologin: bool = False) -> None:
        super().__init__("niri")
        self.autologin = autologin

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {
            "niri", "dux-shell",  # Dux Shell : barre, lanceur, notifications, polkit, verrou
            "xwayland-satellite",  # niri le lance à la demande pour les applis X11
            # Pas de xdg-desktop-portal-gnome, donc pas de partage d'écran sous niri : il tire
            # Nautilus, son indexeur et gvfs, qui se verraient aussi sous Plasma.
        }

    def files(self) -> dict[str, File]:
        # Verrou de Dux Shell : mot de passe, et YubiKey Bio (pam-u2f, u2f-wait-key et
        # /etc/u2f_mappings viennent de desktop.py).
        files = {
            "/etc/pam.d/dankshell": File(source_file="./files/niri/dankshell"),
            "/etc/pam.d/dankshell-u2f": File(source_file="./files/niri/dankshell-u2f"),
        }
        if self.autologin:
            # Lu après autologin.conf (desktop.py), dont il remplace la session.
            files["/etc/plasmalogin.conf.d/niri.conf"] = File(content="[Autologin]\nSession=niri\n")
        return files
