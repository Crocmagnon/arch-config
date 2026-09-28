# arch-config

Configuration déclarative d'Arch Linux pour mes machines de bureau :
- **framework-gab-amd** : Framework 13 AMD ;
- **desktop-gab** : desktop AMD, carte mère Gigabyte B650 ;
- plus tard, **framework-gab** : Framework 13 Pro Intel.

Ce dépôt couvre la partie système. La partie utilisateur (fichiers de config, Plasma, thèmes) vit dans le dépôt [dotfiles](https://codeberg.org/Crocmagnon/dotfiles) et s'applique avec chezmoi.

| Couche | Outil | Dans ce dépôt |
|---|---|---|
| Disque, LUKS, btrfs, bootloader | archinstall | `archinstall/` |
| Paquets, fichiers `/etc`, unités systemd, snapshots | [decman](https://github.com/kiviktnm/decman) | `decman/` |
| Fichiers utilisateur | chezmoi | dépôt dotfiles |

> **État (28/09/2026).** Migration depuis NixOS terminée : le laptop `framework-gab-amd` et le desktop `desktop-gab` tournent sous Arch avec cette config. Vérifié sur le matériel : sur le laptop, l'hibernation, l'empreinte et le réveil par le KVM ; sur le desktop, l'écran DisplayPort à l'invite LUKS (y compris allumé après coup) et la veille ; sur les deux, l'exit node Tailscale. Chaque machine perso a ses propres clés SSH et GPG. srv-1 reste sous NixOS et se déploie depuis lui-même (`mise run srv-1` dans nixos-config). Le futur Framework 13 Pro (`framework-gab`) aura son module d'hôte. Les décisions sont dans [MIGRATION.md](MIGRATION.md).

## Installer une machine

1. Démarrer sur l'ISO Arch.
2. Récupérer ce dépôt, puis générer la configuration pour l'hôte et son disque :
   ```sh
   archinstall/render.sh framework-gab-amd /dev/nvme0n1 > config.json
   ```
3. Écrire un `creds.json` local, **jamais versionné** :
   ```json
   {"encryption_password": "…", "root_enc_password": "<hash>", "users": [{"username": "gaugendre", "enc_password": "<hash>", "sudo": true}]}
   ```
   Les hash s'obtiennent avec `openssl passwd -6`. Mettre le même mot de passe pour LUKS et pour `gaugendre`, c'est ce qui permet au wallet KDE de s'ouvrir à l'autologin.
4. Lancer l'installation, puis redémarrer :
   ```sh
   archinstall --config config.json --creds creds.json --silent
   ```
5. Se connecter en `gaugendre` sur un TTY, se connecter au réseau (`nmcli device wifi connect <SSID> --ask`), cloner ce dépôt, puis installer decman depuis l'AUR, à la main pour cette seule fois :
   ```sh
   cd /tmp && git clone https://aur.archlinux.org/decman.git && cd decman && makepkg -si --nocheck
   sudo decman --source /chemin/vers/arch-config/decman/source.py --dry-run --debug
   sudo decman --source /chemin/vers/arch-config/decman/source.py
   ```
   Le premier run n'installe pas les Flatpak : le plugin Flatpak de decman est chargé au démarrage, avant que pacman n'installe `flatpak`. Un second `sudo decman` s'en charge. Le `--dry-run` doit n'enlever aucun paquet utile. Comparer sa sortie avec `pacman -Qqe`. Le chemin de la source n'est mémorisé qu'au premier vrai run : ce run-là prend donc aussi `--source`, et les suivants s'en passent.

6. Appliquer les dotfiles depuis un TTY, avant la première session graphique (les raccourcis Plasma ne sont relus qu'à la connexion) :
   ```sh
   chezmoi init <dépôt dotfiles>          # sans --apply : les templates lisent des fichiers git-crypt
   cd ~/.local/share/chezmoi && git-crypt unlock /tmp/gc.key && shred -u /tmp/gc.key
   chezmoi init                           # répondre : travail non, serveur non
   chezmoi apply && fish -lc 'mise install'
   ```

Les étapes manuelles (sauvegardes, secrets, comptes) sont listées dans [MIGRATION.md §7](MIGRATION.md#7-étapes).

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
  - le socle : fish, gnupg, git-crypt, chezmoi, mise ;
  - sudo sans mot de passe, les locales, `paccache.timer`.
- `boot.py` : Limine avec `limine-mkinitcpio-hook`, la ligne de commande du noyau (`/etc/kernel/cmdline`), snapper, snap-pac et `limine-snapper-sync`, et la police de console (Terminus 22 px).
  - Chaque transaction pacman crée un snapshot avant et un après, et chacun devient démarrable depuis le menu Limine avec son propre noyau.
  - Au premier run, le module migre l'installation Limine d'archinstall vers celle de l'outil.

- `desktop.py` : la session Plasma et les services du bureau.
  - Plasma et ses applications, plasma-login-manager en autologin.
  - Le wallet KDE ouvert à l'autologin avec la passphrase LUKS : `pam_systemd_loadkey` dans une copie de `plasmalogin-autologin`, et `KeyringMode=inherit` sur `plasmalogin.service`.
  - Audio, Bluetooth, impression, Docker, Tailscale, iPhone, VM (libvirt et virt-manager).
  - ufw (entrée refusée, sauf KDE Connect ; `rp_filter` lâche pour l'exit node Tailscale), Flatpak (PrusaSlicer).
- `apps.py` : les applications (Firefox, Chromium, Signal, Thunderbird, FreeCAD, LibreOffice, calibre, Steam, openscad-git, suite Nordic nRF…) et les outils en ligne de commande qui ne viennent pas de mise.
- `amd.py` : le microcode et les pilotes Vulkan pour les machines AMD.
- Les paquets AUR se compilent sous l'utilisateur système `builduser`. Les clés PGP des sources signées lui sont fournies par `source.py`.
- `/etc/makepkg.conf.d/parallel.conf` fait compiler sur tous les cœurs (makepkg n'en utilise qu'un par défaut).
- `framework_gab_amd.py` (laptop) :
  - l'hibernation (veille, puis hibernation au bout d'une heure) et la levée du verrouillage de Plasma après une hibernation de plus de 5 min ;
  - l'empreinte digitale au verrouillage de l'écran, les profils d'énergie ;
  - le réveil par le clavier derrière le KVM, la blacklist audio du BIOS ;
  - les outils de mesure de la batterie ;
  - pour l'écran dense : la police du menu Limine doublée.
- `source.py` associe chaque hôte à ses paramètres noyau et à ses modules. desktop-gab n'a pas de module propre : juste `acpi_osi` pour la veille. Il ajoute aussi l'utilisateur aux groupes `docker`, `uucp` (ports série), `input` et `libvirt`.

## Revenir en arrière

Dans le menu Limine, ouvrir **Snapshots**, puis un snapshot, puis son entrée `linux`. Le système démarre sur ce snapshot, avec un overlay en écriture qui disparaît au redémarrage. Pour rendre le retour définitif, lancer `limine-snapper-restore` depuis ce démarrage.

## Tester

Le banc de test est une VM libvirt sur un hôte existant, avec des états sauvegardés : voir [vm/README.md](vm/README.md). Ce qui n'est pas testable en VM (hibernation, empreinte, matériel) se vérifie sur la vraie machine.
