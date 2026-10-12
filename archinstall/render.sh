#!/bin/sh
# Rend user_configuration.json pour un hôte et un disque, sur stdout.
#   render.sh framework-gab /dev/nvme0n1 > /root/config.json
# L'ESP commence à 1 MiB ; la racine prend tout le disque après elle, moins 1 MiB pour la GPT de
# secours : archinstall n'accepte que des tailles absolues.
set -eu
host=$1 dev=$2
esp_mib=4096
root_start_mib=$(( 1 + esp_mib ))
root_mib=$(( $(blockdev --getsize64 "$dev") / 1048576 - root_start_mib - 1 ))
sed -e "s|@HOSTNAME@|$host|" -e "s|@DEVICE@|$dev|" -e "s|\"@ESP_MIB@\"|$esp_mib|" \
  -e "s|\"@ROOT_START_MIB@\"|$root_start_mib|" -e "s|\"@ROOT_MIB@\"|$root_mib|" \
  "$(dirname "$0")/user_configuration.json"
