#!/usr/bin/env bash
# Migration à usage unique : re-chiffre les secrets agenix du desktop (nixos-config) en fichiers
# git-crypt du dépôt dotfiles, là où chezmoi les attend. Voir MIGRATION.md §5.
#
# À lancer soi-même, sur une machine NixOS qui a l'identité age, avec dotfiles DÉVERROUILLÉ
# (git-crypt unlock). N'affiche aucun secret et ne commite rien : relire `git status` ensuite.
#
#   nix shell nixpkgs#age --command scripts/agenix-to-dotfiles.sh [~/Projects/codeberg.org/Crocmagnon]
set -euo pipefail
umask 077

base=${1:-$HOME/Projects/codeberg.org/Crocmagnon}
age_dir=$base/nixos-config/modules/home/gaugendre/desktop/age
dotfiles=$base/dotfiles
identity=$HOME/.config/agenix/identity.txt

[ -r "$identity" ] || { echo "identité age introuvable : $identity" >&2; exit 1; }
# Un fichier git-crypt verrouillé commence par l'en-tête \0GITCRYPT : seuls ces octets sont lus.
probe=$dotfiles/.secrets/encrypted_smtp_password
if head -c 10 "$probe" | tail -c 9 | grep -q GITCRYPT; then
    echo "dotfiles est verrouillé : lancer d'abord git-crypt unlock <clé> dans $dotfiles" >&2
    exit 1
fi

decrypt() { # source.age destination
    mkdir -p "$(dirname "$2")"
    age -d -i "$identity" -o "$2" "$1"
    echo "écrit : ${2#"$dotfiles"/}"
}

decrypt "$age_dir/ro-github-token.age" "$dotfiles/.secrets/encrypted_ro_github_token"
decrypt "$age_dir/ha-mcp-token.age" "$dotfiles/.secrets/encrypted_ha_mcp_token"
for f in "$age_dir"/fonts/*.otf.age; do
    name=$(basename "$f" .age)
    decrypt "$f" "$dotfiles/dot_local/share/fonts/encrypted_$name"
done

# Chaque nouveau fichier doit être couvert par le filtre git-crypt (encrypted_* dans .gitattributes).
# git check-attr lit .gitattributes pour tout chemin, même non suivi (git-crypt status, lui, ne voit
# que les fichiers déjà dans l'index).
cd "$dotfiles"
bad=$( { echo .secrets/encrypted_ro_github_token; echo .secrets/encrypted_ha_mcp_token; ls dot_local/share/fonts/encrypted_*; } \
    | git check-attr --stdin filter | grep -v ': filter: git-crypt$' || true)
if [ -n "$bad" ]; then
    echo "ATTENTION, fichiers NON couverts par git-crypt, ne pas commiter :" >&2
    echo "$bad" >&2
    exit 1
fi
echo "OK : tous les fichiers seront chiffrés par git-crypt au commit. Vérifier avec git status, puis commiter."
