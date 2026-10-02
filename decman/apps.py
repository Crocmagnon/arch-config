# Applications et outils en ligne de commande communs aux machines de bureau. Les outils de dev
# qui existent dans mise (go, node, uv, lua, rust, terraform…) passent par mise, pas par ici.
from decman import Module
from decman.plugins import aur, pacman


class Apps(Module):
    def __init__(self) -> None:
        super().__init__("apps")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {
            "firefox", "chromium", "signal-desktop", "thunderbird",
            "freecad", "graphviz",  # graphviz : graphe des dépendances dans FreeCAD
            "libreoffice-still", "calibre", "tldr",
            "steam",  # dépôt multilib, activé par archinstall ; pilote Vulkan dans le module du GPU
            "fuse2",  # AppImages (Rotatrix, nRF Connect)
            "git-lfs", "unzip", "bind", "jq", "watchexec", "htop", "btop", "clang",
            "vscode-json-languageserver", "yaml-language-server",
            "luarocks", "luacheck", "busted",  # outils Lua absents de mise (luajit, stylua, lua-language-server y sont)
            "opencode",
        }

    @aur.packages
    def aur_packages(self) -> set[str]:
        return {
            "rustdesk-bin", "pcloud-drive", "koreader-bin", "claude-code",
            "openscad-git",  # version de développement (manifold) ; recompilée seulement avec
                             # sudo decman --params aur-upgrade-devel
            # Suite Nordic nRF. nrf-udev et jlink-software-and-documentation en sont des dépendances :
            # les déclarer aussi les ferait réinstaller à chaque run (déjà là, mais pas explicites).
            "nrfconnect-appimage", "nrfutil",
            "git-toolbelt", "amber-search-bin", "fresh-editor-bin",
        }
