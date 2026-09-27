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

> **État (27/09/2026).** Migration depuis NixOS en cours. Validés dans la VM de test, de bout en bout sur une installation neuve : archinstall, puis les modules decman `base` et `boot` en un seul run, jusqu'au démarrage sur un snapshot. Restent à faire : les modules `desktop` et d'hôte, puis chezmoi. Le plan et les décisions sont dans [MIGRATION.md](MIGRATION.md).

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
5. Installer decman depuis l'AUR, à la main pour cette seule fois (`makepkg`), puis :
   ```sh
   sudo decman --source /chemin/vers/arch-config/decman/source.py --dry-run --debug
   sudo decman --source /chemin/vers/arch-config/decman/source.py
   ```
   Le `--dry-run` doit n'enlever aucun paquet utile. Comparer sa sortie avec `pacman -Qqe`. Le chemin de la source n'est mémorisé qu'au premier vrai run : ce run-là prend donc aussi `--source`, et les suivants s'en passent.

Les étapes manuelles (sauvegardes, secrets, comptes) sont listées dans [MIGRATION.md §7](MIGRATION.md#7-étapes).

## Ce que fait l'installation

**archinstall** (`archinstall/user_configuration.json`, rendu par `render.sh`) :
- une ESP de 4 Gio montée sur `/boot` ;
- une partition LUKS2 avec btrfs, sous-volumes `@ @home @log @pkg @swap`, compression zstd ;
- Limine, plymouth, zram, NetworkManager, clavier `fr`, fuseau Europe/Paris.

Ses `custom_commands` font deux choses :
- **initramfs systemd.** archinstall pose le hook busybox `encrypt`. Les commandes le remplacent par `sd-encrypt` via `/etc/mkinitcpio.conf.d/10-hooks.conf`, et déclarent la racine dans `/etc/crypttab` avec `x-initrd.attach`. C'est nécessaire à la reprise d'hibernation et au déverrouillage du wallet.
- **swapfile** de la taille de la RAM dans `@swap`, sur le laptop seulement, pour l'hibernation. La reprise passe par la variable EFI `HibernateLocation`, sans `resume=`.

**decman** (`decman/source.py` choisit les modules selon le hostname) :
- `base.py` :
  - les paquets posés par archinstall, qu'il faut déclarer pour que decman ne les supprime pas ;
  - le socle : fish, gnupg, git-crypt, chezmoi, mise ;
  - sudo sans mot de passe, les locales, `paccache.timer`.
- `boot.py` : Limine avec `limine-mkinitcpio-hook`, la ligne de commande du noyau (`/etc/kernel/cmdline`), snapper, snap-pac et `limine-snapper-sync`.
  - Chaque transaction pacman crée un snapshot avant et un après, et chacun devient démarrable depuis le menu Limine avec son propre noyau.
  - Au premier run, le module migre l'installation Limine d'archinstall vers celle de l'outil.

## Revenir en arrière

Dans le menu Limine, ouvrir **Snapshots**, puis un snapshot, puis son entrée `linux`. Le système démarre sur ce snapshot, avec un overlay en écriture qui disparaît au redémarrage. Pour rendre le retour définitif, lancer `limine-snapper-restore` depuis ce démarrage.

## Tester

Le banc de test est une VM libvirt sur un hôte existant, avec des états sauvegardés : voir [vm/README.md](vm/README.md). Ce qui n'est pas testable en VM (hibernation, empreinte, matériel) se vérifie sur la vraie machine.
