# Processeur et GPU AMD (desktop-gab).
from decman import Module
from decman.plugins import pacman


class Amd(Module):
    def __init__(self) -> None:
        super().__init__("amd")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        # Déclarer le pilote Vulkan évite que pacman demande lequel installer pour Steam.
        return {"amd-ucode", "vulkan-radeon", "lib32-vulkan-radeon"}
