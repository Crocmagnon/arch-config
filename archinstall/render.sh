#!/bin/sh
# Rend user_configuration.json pour un hôte et un disque, sur stdout.
#   render.sh framework-gab-amd /dev/nvme0n1 > /root/config.json
# La racine prend tout le disque après l'ESP (1 MiB + 4 GiB), moins 1 MiB pour la GPT de secours :
# archinstall n'accepte que des tailles absolues.
set -eu
host=$1 dev=$2
root_mib=$(( $(blockdev --getsize64 "$dev") / 1048576 - 4097 - 1 ))
sed -e "s|@HOSTNAME@|$host|" -e "s|@DEVICE@|$dev|" -e "s|\"@ROOT_MIB@\"|$root_mib|" \
  "$(dirname "$0")/user_configuration.json"
