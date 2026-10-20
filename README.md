# arch-config

Configuration déclarative d'Arch Linux pour mes machines de bureau :
- **framework-gab** : Framework 13 Pro Intel ;
- **desktop-gab** : desktop AMD, carte mère Gigabyte B650.

Ce dépôt couvre la partie système. La partie utilisateur (fichiers de config, Plasma, thèmes) vit dans le dépôt [dotfiles](https://github.com/Crocmagnon/dotfiles) et s'applique avec chezmoi.

| Couche | Outil | Dans ce dépôt |
|---|---|---|
| Disque, LUKS, btrfs, bootloader | archinstall | `archinstall/` |
| Paquets, fichiers `/etc`, unités systemd, snapshots | [decman](https://github.com/kiviktnm/decman) | `decman/` |
| Fichiers utilisateur | chezmoi | dépôt dotfiles |

Pour savoir où va une chose : ce qui demande root ou ne concerne qu'Arch va ici (paquets, `/etc`, unités système, udev, groupes), ainsi que les outils nécessaires avant chezmoi et mise. Tout ce qui vit sous `$HOME` va dans dotfiles, y compris les unités utilisateur et les réglages Plasma. dotfiles sert aussi les machines du travail (Ubuntu, Debian). Un outil en ligne de commande utile partout vient donc de mise, dans dotfiles. Un outil propre à Arch, ou que mise ne sait pas installer, vient de pacman, ici.

> **État (28/09/2026).** Migration depuis NixOS terminée : le laptop `framework-gab-amd` et le desktop `desktop-gab` tournent sous Arch avec cette config. Vérifié sur le matériel : sur le laptop, l'hibernation, l'empreinte et le réveil par le KVM ; sur le desktop, l'écran DisplayPort à l'invite LUKS (y compris allumé après coup) et la veille ; sur les deux, l'exit node Tailscale. Chaque machine perso a ses propres clés SSH et GPG. srv-1 reste sous NixOS et se déploie depuis lui-même (`mise run srv-1` dans nixos-config). Le Framework 13 AMD a laissé place au Framework 13 Pro Intel (`framework-gab`, 12/10/2026). Son module reprend l'hibernation, le KVM et l'empreinte de l'ancien laptop. Y sont vérifiés (14/10/2026) : l'hibernation (une fois coupé le port de la webcam qui réveillait la machine), l'empreinte et les pilotes Intel (Vulkan, VA-API) ; puis (16/10/2026) l'écran du dock USB4 à l'invite LUKS, capot fermé, grâce à `thunderbolt` dans l'initramfs (le menu Limine reste noir derrière le dock) ; le réveil par le KVM reste à vérifier. Une YubiKey Bio derrière le KVM donne l'empreinte au verrouillage au bureau, où le laptop sert capot fermé : vérifié sur les deux machines (19/10/2026), y compris verrouillé pendant que le KVM était sur l'autre. Elle déverrouille aussi LUKS, avec un wallet sans mot de passe : vérifié (20/10/2026) sur desktop-gab, par la clé comme par la passphrase après les 30 s d'attente, et sur framework-gab par la clé, au démarrage et à la reprise d'hibernation. L'inventaire et les décisions de la migration sont dans l'historique git (`git log -- MIGRATION.md`).

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
   Sur framework-gab, activer aussi « Power on AC attach » : posé capot fermé dans son socle, le laptop démarre quand l'alimentation du dock revient. Le BIOS 3.02 n'a pas d'option USB4 avant le boot, donc le menu Limine reste noir derrière le dock ; l'invite LUKS s'affiche.
2. Sur l'ISO, se connecter au réseau, récupérer ce dépôt, puis générer la configuration pour l'hôte et son disque :
   ```sh
   loadkeys fr
   iwctl station wlan0 connect <SSID>
   pacman -Sy git && git clone https://github.com/Crocmagnon/arch-config && cd arch-config
   archinstall/render.sh framework-gab /dev/nvme0n1 > config.json
   ```
3. Écrire `archinstall/creds.json`, ignoré par git : `archinstall/creds.sh` demande un mot de passe et le met pour LUKS, `gaugendre` et root.
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
   Sauvegarder la clé GPG secrète (`gpg --armor --export-secret-keys`) et son certificat de révocation (`~/.gnupg/openpgp-revocs.d/`) dans Bitwarden. Publier les deux clés publiques sur GitHub, la clé SSH dans `modules/nixos/common/users.nix` (nixos-config, déployé sur srv-1) et sur `hass`. Passer ensuite les remotes de dotfiles et arch-config en SSH.
2. Comptes et services :
   - `sudo tailscale up --operator=$USER --ssh --accept-routes --accept-dns` si ce n'est pas fait à l'étape 6, appairage KDE Connect ;
   - connexions : Signal, pCloud, Steam, `claude` ; restauration du profil Thunderbird ;
   - `fprintd-enroll` (laptop) ;
   - YubiKey Bio, seulement pour une nouvelle clé (le mapping est dans le dépôt, commun aux deux machines) : `ykman fido access change-pin`, `ykman fido fingerprints add <nom>`, puis `pamu2fcfg -u gaugendre -o pam://gab -i pam://gab -V > decman/files/desktop/u2f_mappings` (aucun message : toucher la clé quand la commande semble bloquée) et `sudo decman` ;
   - YubiKey Bio pour LUKS, sur chaque machine : `sudo systemd-cryptenroll /dev/disk/by-uuid/<uuid LUKS> --fido2-device=auto --fido2-with-client-pin=no --fido2-with-user-verification=yes` (`lsblk -o NAME,FSTYPE,UUID` pour l'UUID). La ligne crypttab a déjà `fido2-device=auto` ; sur une installation plus ancienne, l'ajouter puis lancer `sudo limine-mkinitcpio` ;
   - wallet sans mot de passe, sur les deux machines (sinon il reste fermé à l'autologin) : kwalletmanager, « Changer le mot de passe… », champs vides ;
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
- **initramfs systemd.** archinstall pose le hook busybox `encrypt`. Les commandes le remplacent par `sd-encrypt` via `/etc/mkinitcpio.conf.d/10-hooks.conf`, et déclarent la racine dans `/etc/crypttab` avec `x-initrd.attach`. C'est nécessaire à la reprise d'hibernation et au déverrouillage par la YubiKey Bio (`fido2-device=auto`). Le même fichier met `thunderbolt` dans `MODULES` : sans lui, le tunnel DP du dock USB4 n'existe pas avant le démarrage du vrai système, et l'écran du dock reste noir à l'invite LUKS.
- **swapfile** de la taille de la RAM dans `@swap`, sur le laptop seulement, pour l'hibernation. La reprise passe par la variable EFI `HibernateLocation`, sans `resume=`. `resumeflags=x-systemd.device-timeout=infinity` la fait attendre la passphrase LUKS sans limite : par défaut, au bout de 2 min, systemd démarre à froid et perd l'image. En contrepartie, une variable obsolète (hiberner, puis réinstaller, reformater ou changer de SSD) bloque le démarrage indéfiniment : démarrer une fois avec `noresume` ajouté dans l'éditeur de Limine (`e`), et systemd efface la variable. C'est aussi le seul moyen de renoncer à une reprise depuis l'invite LUKS.

**decman** (`decman/source.py` choisit les modules selon le hostname) :
- `base.py` :
  - les paquets posés par archinstall, qu'il faut déclarer pour que decman ne les supprime pas ;
  - le socle : fish, fisher, gnupg, git-crypt, chezmoi, mise, le client openssh, vim, ripgrep, man (avec `man-db.timer`) ;
  - sudo sans mot de passe, les locales, `paccache.timer`, `pacman-download.timer` (télécharge chaque jour les mises à jour dans le cache, sans les installer), et `kernel-modules-hook`, qui garde les modules du noyau en cours jusqu'au redémarrage qui suit sa mise à jour.
- `boot.py` : Limine avec `limine-mkinitcpio-hook`, la ligne de commande du noyau (`/etc/kernel/cmdline`), snapper, snap-pac et `limine-snapper-sync`, la police de console (Terminus 22 px), et `luks-attach` : à l'invite LUKS, trois essais d'empreinte sur la YubiKey Bio puis la passphrase, au lieu de l'emergency mode au premier doigt refusé.
  - Chaque transaction pacman crée un snapshot avant et un après, et chacun devient démarrable depuis le menu Limine avec son propre noyau.
  - Au premier run, le module migre l'installation Limine d'archinstall vers celle de l'outil.

- `desktop.py` : la session Plasma et les services du bureau.
  - Plasma et ses applications, plasma-login-manager en autologin.
  - L'empreinte au verrouillage par la YubiKey Bio : `pam_u2f` dans une copie de `kde-fingerprint`, avant `pam_fprintd`. sudo est sans mot de passe, donc pas concerné.
  - Audio, Bluetooth, impression, Docker, Tailscale, iPhone, VM (libvirt et virt-manager).
  - ufw (entrée refusée, sauf KDE Connect et le réseau NAT de libvirt ; ports Docker publiés sur localhost seulement, `-p 0.0.0.0:…` pour les ouvrir au LAN ; `rp_filter` lâche pour l'exit node Tailscale), Flatpak (PrusaSlicer, mis à jour chaque jour par `flatpak-update.timer`), `fwupd-refresh.timer` (métadonnées des firmwares seulement).
- `apps.py` : les applications (Firefox, Chromium, Signal, Thunderbird, FreeCAD, LibreOffice, calibre, Steam, openscad-git…), les outils en ligne de commande qui ne viennent pas de mise, et nRF Connect (AUR), dont la dépendance J-Link est figée (`source.py`). L'AUR reste minimal : Claude Code et fresh viennent des dotfiles, RustDesk de Flatpak.
- `maintenance.py` : à chaque `sudo decman`, les news Arch non lues (avec les paquets installés qu'elles citent) et une confirmation avant la mise à jour ; après, les `.pacnew` avec leur diff, le rappel de redémarrage après un nouveau noyau et les firmwares en attente. Une notification hebdomadaire signale les mises à jour et les news en attente. Les miroirs viennent de reflector, chaque semaine (`base.py`).
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

- Mettre à jour : `sudo decman`, à la main, après un coup d'œil aux news Arch. Les paquets sont déjà en cache. Les mises à jour automatiques sont écartées : interventions manuelles annoncées par les news, `.pacnew`, questions de pacman, transaction coupée par une veille.
- `openscad-git` n'est recompilé qu'avec `sudo decman --params aur-upgrade-devel`.
- Après une mise à jour de ufw, fusionner le `.pacnew` de `/etc/ufw/sysctl.conf` (decman le gère avec `rp_filter=2`).
- Après une mise à jour de nix, fusionner le `.pacnew` de `/etc/nix/nix.conf` (decman le gère pour activer les flakes).
- Plus tard, en option : Secure Boot (`sbctl create-keys`, `enroll-keys -m`, signer l'EFI de Limine, puis `limine enroll-config`).

## Tester

Le banc de test est une VM libvirt sur un hôte existant, avec des états sauvegardés : voir [vm/README.md](vm/README.md). Ce qui n'est pas testable en VM (hibernation, empreinte, matériel) se vérifie sur la vraie machine.
