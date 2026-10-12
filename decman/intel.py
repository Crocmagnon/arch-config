# Processeur et GPU Intel (framework-gab).
from decman import Module
from decman.plugins import pacman


class Intel(Module):
    def __init__(self) -> None:
        super().__init__("intel")

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        # Déclarer le pilote Vulkan évite que pacman demande lequel installer pour Steam.
        return {"intel-ucode", "vulkan-intel", "lib32-vulkan-intel", "intel-media-driver"}
