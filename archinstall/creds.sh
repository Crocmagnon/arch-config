#!/bin/bash
# Écrit archinstall/creds.json (ignoré par git) : demande un mot de passe, qui sert à LUKS, à
# gaugendre et à root. Le même pour LUKS et gaugendre : c'est ce qui ouvre le wallet KDE à
# l'autologin. Le mot de passe passe par l'environnement, jamais par les arguments (visibles
# dans ps).
set -eu
read -rsp "Mot de passe : " pw; echo
read -rsp "Confirmer : " pw2; echo
[ "$pw" = "$pw2" ] || { echo "les mots de passe diffèrent" >&2; exit 1; }
h=$(printf '%s' "$pw" | openssl passwd -6 -stdin)
out="$(dirname "$0")/creds.json"
umask 077
pw=$pw h=$h python3 -c '
import json, os, sys
h = os.environ["h"]
json.dump({"encryption_password": os.environ["pw"], "root_enc_password": h,
           "users": [{"username": "gaugendre", "enc_password": h, "sudo": True}]}, sys.stdout)
' > "$out"
echo "écrit : $out"
