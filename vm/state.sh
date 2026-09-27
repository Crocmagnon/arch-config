#!/usr/bin/env bash
# États de la VM de test : un disque qcow2 de base par état, un overlay de travail
# (current.qcow2) par-dessus, et une copie de la NVRAM (entrées Limine, HibernateLocation).
#   state.sh save NOM    fige l'état courant sous NOM et repart d'un overlay vierge au-dessus
#   state.sh reset NOM   jette l'overlay courant et repart de NOM
#   state.sh list
set -euo pipefail
export LIBVIRT_DEFAULT_URI=qemu:///system
vm=${VM:-arch-test}
dir=${DIR:-/var/lib/libvirt/images/$vm}
cmd=${1:-} name=${2:-}

if [ "$cmd" = list ]; then
  ls "$dir" | sed -n 's/\.qcow2$//p' | grep -vx current || true
  exit
fi
[ "$(virsh domstate "$vm")" = "shut off" ] || { echo "$vm doit être éteinte (virsh shutdown $vm)" >&2; exit 1; }
nvram=$(virsh dumpxml "$vm" | sed -n 's|.*<nvram[^>]*>\(.*\)</nvram>.*|\1|p')

case $cmd in
  save)
    [ -n "$name" ] && [ ! -e "$dir/$name.qcow2" ] || { echo "nom manquant ou déjà pris : '$name'" >&2; exit 1; }
    sudo mv "$dir/current.qcow2" "$dir/$name.qcow2"
    sudo cp "$nvram" "$dir/$name.VARS.fd"
    ;&
  reset)
    [ -e "$dir/$name.qcow2" ] || { echo "état inconnu : '$name'" >&2; exit 1; }
    sudo rm -f "$dir/current.qcow2"
    sudo qemu-img create -q -f qcow2 -b "$dir/$name.qcow2" -F qcow2 "$dir/current.qcow2"
    sudo cp "$dir/$name.VARS.fd" "$nvram"
    ;;
  *) sed -n '4,6p' "$0" >&2; exit 1 ;;
esac
