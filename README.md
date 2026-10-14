# arch-config

Configuration déclarative d'Arch Linux pour mes machines de bureau :
- **framework-gab** : Framework 13 Pro Intel ;
- **desktop-gab** : desktop AMD, carte mère Gigabyte B650.

Ce dépôt couvre la partie système. La partie utilisateur (fichiers de config, Plasma, thèmes) vit dans le dépôt [dotfiles](https://codeberg.org/Crocmagnon/dotfiles) et s'applique avec chezmoi.

| Couche | Outil | Dans ce dépôt |
|---|---|---|
| Disque, LUKS, btrfs, bootloader | archinstall | `archinstall/` |
| Paquets, fichiers `/etc`, unités systemd, snapshots | [decman](https://github.com/kiviktnm/decman) | `decman/` |
| Fichiers utilisateur | chezmoi | dépôt dotfiles |

Pour savoir où va une chose : ce qui demande root ou ne concerne qu'Arch va ici (paquets, `/etc`, unités système, udev, groupes), ainsi que les outils nécessaires avant chezmoi et mise. Tout ce qui vit sous `$HOME` va dans dotfiles, y compris les unités utilisateur et les réglages Plasma. dotfiles sert aussi les machines du travail (Ubuntu, Debian). Un outil en ligne de commande utile partout vient donc de mise, dans dotfiles. Un outil propre à Arch, ou que mise ne sait pas installer, vient de pacman, ici.

> **État (28/09/2026).** Migration depuis NixOS terminée : le laptop `framework-gab-amd` et le desktop `desktop-gab` tournent sous Arch avec cette config. Vérifié sur le matériel : sur le laptop, l'hibernation, l'empreinte et le réveil par le KVM ; sur le desktop, l'écran DisplayPort à l'invite LUKS (y compris allumé après coup) et la veille ; sur les deux, l'exit node Tailscale. Chaque machine perso a ses propres clés SSH et GPG. srv-1 reste sous NixOS et se déploie depuis lui-même (`mise run srv-1` dans nixos-config). Le Framework 13 AMD a laissé place au Framework 13 Pro Intel (`framework-gab`, 12/10/2026). Son module reprend l'hibernation, le KVM et l'empreinte de l'ancien laptop. Y sont vérifiés (14/10/2026) : l'hibernation (une fois coupé le port de la webcam qui réveillait la machine), l'empreinte et les pilotes Intel (Vulkan, VA-API) ; le réveil par le KVM reste à vérifier. L'inventaire et les décisions de la migration sont dans l'historique git (`git log -- MIGRATION.md`).

## Installer une machine

1. Préparer la clé USB avec l'ISO officielle (sous fish comme sous bash) :
   ```sh
   curl -LO https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso
   curl -LO https://geo.mirror.pkgbuild.com/iso/latest/archlinux-x86_64.iso.sig
   curl -LO https://geo.mirror.pkgbuild.com/iso/latest/b2sums.txt
   pacman-key -v archlinux-x86_64.iso.sig && b2sum -c b2sums.txt --ignore-missing
   lsblk -o NAME,SIZE,MODEL,TRAN    # repérer la clé (TRAN=usb)
   sudo dd if=archlinux-x86_64.iso of=/dev/sdX bs=4M oflag=direct conv=fsync status=progress
   ```
   Sur un Framework, désactiver Secure Boot dans le BIOS (F2) : l'ISO n'est pas signée. Démarrer sur la clé (F12).
2. Sur l'ISO, se connecter au réseau, récupérer ce dépôt, puis générer la configuration pour l'hôte et son disque :
   ```sh
   loadkeys fr
   iwctl station wlan0 connect <SSID>
   pacman -Sy git && git clone https://codeberg.org/Crocmagnon/arch-config && cd arch-config
   archinstall/render.sh framework-gab /dev/nvme0n1 > config.json
   ```
3. Écrire `archinstall/creds.json`, ignoré par git : `archinstall/creds.sh` demande un mot de passe et le met pour LUKS, `gaugendre` et root. Le même pour LUKS et `gaugendre`, c'est ce qui permet au wallet KDE de s'ouvrir à l'autologin.
4. Lancer l'installation, puis redémarrer :
   ```sh
   archinstall --config config.json --creds archinstall/creds.json --silent
   ```
5. Se connecter en `gaugendre` sur un TTY, se connecter au réseau (`nmcli device wifi connect <SSID> --ask`), cloner ce dépôt, puis installer decman depuis l'AUR, à la main pour cette seule fois :
   ```sh
   cd /tmp && git clone https://aur.archlinux.org/decman.git && cd decman && makepkg -si --nocheck
   sudo decman --source /chemin/vers/arch-config/decman/source.py --dry-run --debug
   sudo decman --source /chemin/vers/arch-config/decman/source.py
   ```
   Le premier run n'installe pas les Flatpak : le plugin Flatpak de decman est chargé au démarrage, avant que pacman n'installe `flatpak`. Un second `sudo decman` s'en charge. Le `--dry-run` doit n'enlever aucun paquet utile. Comparer sa sortie avec `pacman -Qqe`. Le chemin de la source n'est mémorisé qu'au premier vrai run : ce run-là prend donc aussi `--source`, et les suivants s'en passent.

6. Avant la première session graphique (les raccourcis Plasma ne sont relus qu'à la connexion), appliquer les dotfiles. Pour coller la clé depuis une autre machine plutôt que dans le TTY, joindre d'abord le tailnet depuis le TTY (`--qr` : un QR code à scanner au téléphone, pas d'URL à recopier) :
   ```sh
   sudo systemctl start tailscaled     # decman active l'unité sans la démarrer
   sudo tailscale up --operator=$USER --ssh --accept-routes --accept-dns --qr
   ```
   Puis, depuis une machine du tailnet, `ssh gaugendre@<hôte>` et :
   ```sh
   scripts/bootstrap-dotfiles.sh
   ```
   Il clone dotfiles en HTTPS, le déverrouille avec la clé git-crypt collée en base64 depuis l'entrée Bitwarden « git-crypt dotfiles chezmoi base64 », répond « travail non », puis lance `chezmoi apply`, `mise install` et un second `chezmoi apply` pour les scripts qui attendaient un outil de mise. Relançable sans risque. Puis redémarrer.

## Après la première connexion

Dans un terminal Plasma (pinentry-qt et le wallet ne sont là qu'en session graphique) :

1. Créer les clés de la machine, en cochant « enregistrer dans le gestionnaire de mots de passe » à chaque pinentry :
   ```sh
   ssh-keygen -t ed25519 -C "gaugendre@$(hostname)"
   ssh-add ~/.ssh/id_ed25519
   gpg --quick-generate-key "Gabriel Augendre <gabriel@augendre.info>" default default 2y
   ```
   Sauvegarder la clé GPG secrète (`gpg --armor --export-secret-keys`) et son certificat de révocation (`~/.gnupg/openpgp-revocs.d/`) dans Bitwarden. Publier les deux clés publiques sur Codeberg et GitHub, la clé SSH dans `modules/nixos/common/users.nix` (nixos-config, déployé sur srv-1) et sur `hass`. Passer ensuite les remotes de dotfiles et arch-config en SSH.
2. Comptes et services :
   - `sudo tailscale up --operator=$USER --ssh --accept-routes --accept-dns` si ce n'est pas fait à l'étape 6, appairage KDE Connect ;
   - connexions : Signal, pCloud, Steam, `claude` ; restauration du profil Thunderbird ;
   - `fprintd-enroll` (laptop) ;
   - `fwupdmgr refresh && fwupdmgr update` ;
   - `flatpak remote-add flathub-beta …`, installer PrusaSlicer `//beta`, puis l'ajouter à `ignored_packages` (decman ne gère ni remotes ni branches).
3. Contrôles :
   - `sysctl net.ipv4.conf.all.rp_filter` vaut 2 (exit node Tailscale) ;
   - laptop : `test -e /sys/class/rtc/rtc0/wakealarm`, puis une hibernation et sa reprise ;
   - `ssh-add -l` depuis une application graphique.

## Ce que fait l'installation

**archinstall** (`archinstall/user_configuration.json`, rendu par `render.sh`) :
- une ESP de 4 Gio montée sur `/boot` ;
- une partition LUKS2 avec btrfs, sous-volumes `@ @home @log @pkg @swap`, compression zstd ;
- Limine, plymouth, zram, NetworkManager, le dépôt `multilib` (pour Steam), clavier `fr`, fuseau Europe/Paris.

Ses `custom_commands` font deux choses :
- **initramfs systemd.** archinstall pose le hook busybox `encrypt`. Les commandes le remplacent par `sd-encrypt` via `/etc/mkinitcpio.conf.d/10-hooks.conf`, et déclarent la racine dans `/etc/crypttab` avec `x-initrd.attach`. C'est nécessaire à la reprise d'hibernation et au déverrouillage du wallet.
- **swapfile** de la taille de la RAM dans `@swap`, sur le laptop seulement, pour l'hibernation. La reprise passe par la variable EFI `HibernateLocation`, sans `resume=`.

**decman** (`decman/source.py` choisit les modules selon le hostname) :
- `base.py` :
  - les paquets posés par archinstall, qu'il faut déclarer pour que decman ne les supprime pas ;
  - le socle : fish, fisher, gnupg, git-crypt, chezmoi, mise, le client openssh, vim, ripgrep, man (avec `man-db.timer`) ;
  - sudo sans mot de passe, les locales, `paccache.timer`, et `kernel-modules-hook`, qui garde les modules du noyau en cours jusqu'au redémarrage qui suit sa mise à jour.
- `boot.py` : Limine avec `limine-mkinitcpio-hook`, la ligne de commande du noyau (`/etc/kernel/cmdline`), snapper, snap-pac et `limine-snapper-sync`, et la police de console (Terminus 22 px).
  - Chaque transaction pacman crée un snapshot avant et un après, et chacun devient démarrable depuis le menu Limine avec son propre noyau.
  - Au premier run, le module migre l'installation Limine d'archinstall vers celle de l'outil.

- `desktop.py` : la session Plasma et les services du bureau.
  - Plasma et ses applications, plasma-login-manager en autologin.
  - Le wallet KDE ouvert à l'autologin avec la passphrase LUKS : `pam_systemd_loadkey` dans une copie de `plasmalogin-autologin`, et `KeyringMode=inherit` sur `plasmalogin.service`.
  - Audio, Bluetooth, impression, Docker, Tailscale, iPhone, VM (libvirt et virt-manager).
  - ufw (entrée refusée, sauf KDE Connect et le réseau NAT de libvirt ; ports Docker publiés sur localhost seulement, `-p 0.0.0.0:…` pour les ouvrir au LAN ; `rp_filter` lâche pour l'exit node Tailscale), Flatpak (PrusaSlicer).
- `apps.py` : les applications (Firefox, Chromium, Signal, Thunderbird, FreeCAD, LibreOffice, calibre, Steam, openscad-git, suite Nordic nRF…) et les outils en ligne de commande qui ne viennent pas de mise.
- `amd.py` (desktop) et `intel.py` (laptop) : le microcode et les pilotes Vulkan, plus le décodage vidéo VA-API côté Intel.
- Les paquets AUR se compilent sous l'utilisateur système `builduser`. Les clés PGP des sources signées lui sont fournies par `source.py`.
- `/etc/makepkg.conf.d/parallel.conf` fait compiler sur tous les cœurs (makepkg n'en utilise qu'un par défaut).
- `framework_gab.py` (laptop) :
  - l'hibernation (veille, puis hibernation au bout d'une heure) et la levée du verrouillage de Plasma après une hibernation de plus de 5 min ; le port de la webcam coupé pendant la veille, car elle réveillait la machine aussitôt ;
  - l'empreinte digitale au verrouillage de l'écran, les profils d'énergie ;
  - le réveil par le clavier derrière le KVM ;
  - les outils de mesure de la batterie ;
  - pour l'écran dense : la police du menu Limine doublée.
- `source.py` associe chaque hôte à ses paramètres noyau et à ses modules. desktop-gab n'a pas de module propre : juste `acpi_osi` pour la veille. Il ajoute aussi l'utilisateur aux groupes `docker`, `uucp` (ports série), `input` et `libvirt`.

## Revenir en arrière

Dans le menu Limine, ouvrir **Snapshots**, puis un snapshot, puis son entrée `linux`. Le système démarre sur ce snapshot, avec un overlay en écriture qui disparaît au redémarrage. `systemd-remount-fs.service` y échoue, et c'est attendu : il essaie de remonter l'overlay avec les options btrfs de fstab. Pour rendre le retour définitif, lancer `limine-snapper-restore` depuis ce démarrage.

## Entretien

- `openscad-git` n'est recompilé qu'avec `sudo decman --params aur-upgrade-devel`.
- Après une mise à jour de ufw, fusionner le `.pacnew` de `/etc/ufw/sysctl.conf` (decman le gère avec `rp_filter=2`).
- Après une mise à jour de nix, fusionner le `.pacnew` de `/etc/nix/nix.conf` (decman le gère pour activer les flakes).
- Plus tard, en option : Secure Boot (`sbctl create-keys`, `enroll-keys -m`, signer l'EFI de Limine, puis `limine enroll-config`).

## Tester

Le banc de test est une VM libvirt sur un hôte existant, avec des états sauvegardés : voir [vm/README.md](vm/README.md). Ce qui n'est pas testable en VM (hibernation, empreinte, matériel) se vérifie sur la vraie machine.
