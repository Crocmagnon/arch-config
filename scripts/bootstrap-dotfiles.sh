#!/usr/bin/env bash
# Amorce les dotfiles (chezmoi) sur une machine perso fraîchement installée, juste après decman.
# À lancer depuis le TTY ou par Tailscale SSH, avant la première session Plasma : kglobalacceld
# ne relit pas ses raccourcis, ils doivent être écrits avant la connexion. Relançable : une étape
# déjà faite est sautée.
#
#   scripts/bootstrap-dotfiles.sh
set -euo pipefail

repo=https://github.com/Crocmagnon/dotfiles.git  # HTTPS : la machine n'a pas encore de clé SSH
src=$HOME/.local/share/chezmoi

[ "$(id -u)" -ne 0 ] || { echo "à lancer en gaugendre, pas en root" >&2; exit 1; }
for tool in chezmoi git-crypt mise fish; do
    command -v "$tool" >/dev/null || { echo "$tool introuvable : lancer decman d'abord" >&2; exit 1; }
done
if pgrep -u "$USER" -x plasmashell >/dev/null; then
    read -rp "Plasma tourne déjà : les raccourcis ne seront pris qu'à la prochaine connexion. Continuer ? [o/N] " ok
    [ "$ok" = o ] || exit 1
fi

[ -d "$src/.git" ] || git clone "$repo" "$src"

# La clé vient de Bitwarden (« git-crypt dotfiles chezmoi base64 »), en base64 : git-crypt
# export-key produit un binaire. Elle ne passe que par la RAM ($XDG_RUNTIME_DIR) et est effacée
# même en cas d'erreur.
if [ ! -e "$src/.git/git-crypt/keys/default" ]; then
    key=$(mktemp -p "${XDG_RUNTIME_DIR:?}")
    trap 'shred -u "$key"' EXIT
    read -rsp "Clé git-crypt (Bitwarden : git-crypt dotfiles chezmoi base64) : " b64
    echo
    base64 -d <<<"$b64" >"$key"
    unset b64
    (cd "$src" && git-crypt unlock "$key")
fi

# --promptBool répond par le texte des questions de .chezmoi.toml.tmpl, pas par les clés.
# headless n'est pas demandé : il se déduit de hostnamectl chassis.
chezmoi init --promptBool "Machine du travail=false"
chezmoi apply  # sans -v : les fichiers rendus contiennent des secrets
# Shell de connexion : conf.d exporte le token GitHub, qui évite les limites de l'API.
fish -lc 'mise install'
# Second passage, outils mise dans le PATH : un script run_onchange sauté faute d'outil repasse,
# car le chemin de l'outil entre dans son hash.
mise exec -- chezmoi apply

echo "Dotfiles appliqués. Redémarrer, puis suivre « Après la première connexion » dans le README."
