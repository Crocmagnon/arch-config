# Banc de test VM

Il a tourné sur desktop-gab, alors sous NixOS (libvirt et virt-manager via `nixos-config/modules/nixos/desktop/virt.nix`), jusqu'à la migration de celui-ci. Le disque et ses états ont disparu avec. Pour le recréer, n'importe quelle machine Arch de ce dépôt convient : `desktop.py` y installe libvirt, virt-manager et OVMF. Les passages propres à NixOS (pare-feu, réseau `default`) sont à adapter. Toutes les commandes se lancent **sur l'hôte**, sauf indication contraire.

La VM s'appelle `arch-test`. Ses fichiers sont dans `/var/lib/libvirt/images/arch-test/`.

## 1. Une fois : ISO et réseau

```fish
sudo mkdir -p /var/lib/libvirt/images/arch-test
cd /var/lib/libvirt/images/arch-test
for f in archlinux-x86_64.iso archlinux-x86_64.iso.sig sha256sums.txt
    sudo curl -fLO https://geo.mirror.pkgbuild.com/iso/latest/$f
end
sha256sum -c --ignore-missing sha256sums.txt
gpg --auto-key-locate clear,wkd --keyserver-options auto-key-retrieve --verify archlinux-x86_64.iso.sig archlinux-x86_64.iso
```

La signature doit être « bonne » et provenir du signataire publié sur <https://archlinux.org/download/>.

Le réseau NAT `default` de libvirt est inactif sur desktop-gab :

```fish
virsh -c qemu:///system net-start default
```

## 2. Créer la VM (ou la recréer de zéro)

```fish
set -x LIBVIRT_DEFAULT_URI qemu:///system
set d /var/lib/libvirt/images/arch-test
virt-install --name arch-test --osinfo archlinux \
    --memory 20480 --vcpus 14 --cpu host-passthrough --machine q35 \
    --boot uefi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=no \
    --disk path=$d/current.qcow2,size=80,format=qcow2,bus=virtio,discard=unmap \
    --cdrom $d/archlinux-x86_64.iso \
    --network network=default --graphics spice --video virtio \
    --noautoconsole
virt-manager --connect qemu:///system --show-domain-console arch-test
```

Le choix des options :
- **UEFI sans Secure Boot**, car l'ISO Arch n'est pas signée.
- **NVRAM persistante**, créée par libvirt : Limine y inscrit son entrée de démarrage, et systemd y écrit `HibernateLocation`.
- **`discard=unmap`**, pour pouvoir tester les discards à travers LUKS.
- **14 vCPU et 20 Gio**, sur un hôte de 16 threads et 30 Gio qui ne fait rien d'autre pendant les tests : les compilations AUR vont vite. Sur le profil laptop, le swapfile prend la taille de la RAM, soit 20 Go ici.

Pour repartir d'un disque vierge (itérations sur archinstall), en ne jetant que le disque de travail et la définition de la VM, pas les états sauvegardés :

```fish
virsh destroy arch-test; virsh undefine arch-test --nvram
sudo rm -f /var/lib/libvirt/images/arch-test/current.qcow2
```

puis recommencer ce §2.

## 3. SSH vers l'ISO live

Dans la console de la VM, le clavier est en qwerty. Tape d'abord `loqdkeys fr` (c'est `loadkeys fr` en qwerty), puis :

```sh
passwd   # mot de passe jetable, valable seulement pour le système live
```

Sur l'hôte : l'ISO génère de nouvelles clés d'hôte à chaque démarrage et l'IP est réutilisée, d'où les options SSH. `ssh-copy-id` demande le mot de passe une fois ; ensuite, tout passe par la clé.

```fish
set ip (virsh -c qemu:///system domifaddr arch-test | string match -rg 'ipv4\s+([\d.]+)')
set o -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
ssh-copy-id $o root@$ip
scp $o -r ~/Projects/codeberg.org/Crocmagnon/arch-config root@$ip:
ssh $o root@$ip
```

Sans console, on peut aussi taper `passwd` dans le live avec `virsh send-key`, dont les noms de touches `KEY_*` suivent la disposition qwerty du live, puis passer le mot de passe à `ssh-copy-id` par un script `SSH_ASKPASS` (`SSH_ASKPASS_REQUIRE=force`).

`virt-install --cloud-init root-ssh-key=…` a été essayé : l'ISO signale cloud-init `done`, mais la clé n'est pas installée. On reste donc sur `passwd` + `ssh-copy-id`.

Les fichiers passent par `scp` plutôt que par `--config-url` : pas de serveur HTTP sur l'hôte, et rien à ouvrir dans le pare-feu NixOS. `--config-url` (depuis codeberg) ne sert qu'aux vraies installations.

## 4. États sauvegardés

Il y a un disque de base qcow2 en lecture seule par état, avec un overlay de travail `current.qcow2` par-dessus. La NVRAM est copiée avec chaque état, parce qu'elle contient l'entrée Limine. La VM doit être éteinte.

```fish
vm/state.sh save post-archinstall   # fige l'état courant
vm/state.sh reset post-archinstall  # jette les changements depuis
vm/state.sh list
```

## 5. Boucle de test

1. ISO, puis §3. Dans la VM :
   ```sh
   arch-config/archinstall/render.sh framework-gab-amd /dev/vda > c.json   # ou desktop-gab
   archinstall --config c.json --creds creds.json --silent
   ```
   `creds.json` est local et n'est pas versionné. Pour la VM, on met `test` partout (LUKS, gaugendre, root) : ce mot s'écrit pareil en qwerty et en azerty.
2. **VM seulement**, avant de redémarrer, sinon le système installé n'a pas de serveur SSH :
   ```sh
   arch-chroot /mnt pacman -S --noconfirm openssh
   arch-chroot /mnt systemctl enable sshd
   install -Dm600 /root/.ssh/authorized_keys /mnt/root/.ssh/authorized_keys
   umount -R /mnt; cryptsetup close root; poweroff
   ```
   Puis `state.sh save post-archinstall`. Premier démarrage : une seule passphrase, puis un TTY.

   La passphrase peut être tapée depuis l'hôte, ce qui évite la console. `send-key` envoie des codes de touches physiques, et les lettres de `test` sont au même endroit en qwerty et en azerty. Il faut attendre que l'invite soit affichée (45 s suffisent), sinon les touches se perdent :
   ```fish
   virsh -c qemu:///system start arch-test; sleep 45
   virsh -c qemu:///system send-key arch-test KEY_T KEY_E KEY_S KEY_T; virsh -c qemu:///system send-key arch-test KEY_ENTER
   ```
3. decman :
   - **Première fois**, l'installer depuis l'AUR à la main. Root installe les dépendances de compilation, `gaugendre` compile (makepkg refuse de tourner en root), puis root installe le paquet :
     ```sh
     cd /tmp && sudo -u gaugendre git clone https://aur.archlinux.org/decman.git && cd decman
     pacman -S --needed --asdeps $(sudo -u gaugendre makepkg --printsrcinfo | awk -F' = ' '/^\t(make)?depends = /{print $2}' | sed 's/[<>=].*//')
     sudo -u gaugendre makepkg --nocheck && pacman -U ./*.pkg.tar.zst
     ```
   - `scp` du dépôt, puis `decman --source …/source.py --dry-run --debug`, à comparer avec `pacman -Qqe`.
   - Le vrai run se lance dans un terminal, parce que pacman pose ses questions. Depuis un SSH non interactif, on passe par `vm/answer.py decman`, qui répond `y` aux confirmations et Entrée aux choix numérotés.
   - decman active ufw, qui refuse toute connexion entrante, SSH compris. La session en cours survit (ufw laisse passer les connexions établies), mais pas les suivantes : enchaîner `sudo ufw allow ssh` dans la même commande que le premier vrai run. Les vraies machines n'ouvrent pas SSH.
   - Redémarrer, contrôler, puis `state.sh save post-decman`.
4. `chezmoi init`, puis `git-crypt unlock`, puis `chezmoi apply` depuis un TTY, puis la première connexion graphique.

En cas d'échec à une étape : `state.sh reset <état précédent>`.

## Naviguer dans le menu Limine

Le menu s'affiche environ 3,5 s après le redémarrage, pendant 3 s. Une flèche envoyée à ce moment arrête le compte à rebours ; ensuite, on navigue sans se presser en vérifiant sur une capture d'écran :

```fish
virsh -c qemu:///system send-key arch-test KEY_DOWN
virsh -c qemu:///system screenshot arch-test /tmp/menu.ppm   # magick /tmp/menu.ppm /tmp/menu.png pour l'ouvrir
```

Entrée ouvre un dossier (Snapshots, puis un snapshot) ou démarre une entrée.

## Pièges de `send-key`

- **Une touche par appel.** Deux touches identiques dans un même appel n'en donnent qu'une : `KEY_R KEY_O KEY_O KEY_T` tape `rot`.
- **Les `KEY_*` sont des touches physiques**, nommées d'après la disposition qwerty. Le live est en qwerty, mais le système installé est en azerty. On y tape `a` avec `KEY_Q`, `z` avec `KEY_W`, `w` avec `KEY_Z`, `q` avec `KEY_A`, `m` avec `KEY_SEMICOLON`, et les chiffres demandent Maj.
- **Si on s'est coupé du SSH** (par exemple avec ufw), on se connecte en root sur tty1 avec `send-key` et on corrige depuis la console.

## Limites de la VM

- **L'hibernation ne se teste pas dans la VM.** Le processus va bien jusqu'à `PM: hibernation: resume from hibernation` : l'image est retrouvée via `HibernateLocation`, et la passphrase n'est demandée qu'une fois. Puis la VM redémarre pendant la restauration de la mémoire, sans message (essayé le 27/09/2026, avec `--cpu host-passthrough`). On la teste sur le vrai laptop.
- Le matériel non plus : empreinte, KVM, carte Ethernet, écran DisplayPort.

## Diagnostic : journal du port série

Pour voir ce que plymouth masque (effet au prochain démarrage à froid) :

```fish
virt-xml -c qemu:///system arch-test --edit --serial log.file=/var/log/libvirt/qemu/arch-test-serial.log,log.append=off
```

Ensuite, dans la VM, remplacer `quiet splash` par `console=ttyS0,115200 console=tty1 loglevel=7` dans `/boot/EFI/arch-limine/limine.conf`. Un `state.sh reset` annule cette modification.
