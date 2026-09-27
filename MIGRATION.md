# Migration NixOS → Arch (laptop, desktop)

Inventaire, décisions et plan de réalisation (§9). Rien n'est encore implémenté.

**Principe directeur.** Retrouver les *fonctionnalités* actuelles avec un Arch/Plasma aussi proche que possible du standard. Une implémentation plus simple que celle de NixOS est préférée, même si elle diffère. Ce qui n'était qu'un contournement NixOS est abandonné.

Sources lues : `nixos-config@main` (les fichiers, plus l'évaluation réelle des deux hôtes via `nix eval`, y compris ce qu'apportent `nixos-hardware` et le module plasma6) et `dotfiles@main`. Les fichiers `*.age` et `encrypted_*` n'ont pas été ouverts. srv-1 est hors périmètre. Le plan a été relu par un relecteur chargé de la simplicité ; ses points vérifiés sont intégrés.

Hôtes :
- **L** = laptop Framework 13 AMD (aujourd'hui `framework-gab`, sous Arch **`framework-gab-amd`**).
- **D** = `desktop-gab`.
- **L+D** = les deux.
- Le futur Framework 13 Pro Intel prendra le nom `framework-gab` (§2.4).

Cibles :
- **ai** : archinstall
- **dm** : decman (paquet, fichier `/etc`, unité systemd)
- **cz** : chezmoi
- **pl** : données Plasma (`kwriteconfig6`)
- **fp** : Flatpak
- **mise**
- **man.** : étape manuelle
- **✗** : abandonné

---

## 0. Décisions

| Sujet | Décision |
|---|---|
| nix sur les Arch | **Non.** Conséquences sous le tableau. |
| Bootloader | **Limine** + `limine-snapper-sync` (AUR) + `snap-pac` : un snapshot avant et après chaque transaction pacman, démarrable depuis le menu. C'est l'équivalent des générations NixOS. |
| Swap | **L** : partition swap LUKS dédiée, déclarée dans le layout d'archinstall. **D** : zram. |
| Initramfs | **systemd** (`sd-encrypt`) sur L et D. Il sert au déverrouillage du wallet (cf. ligne suivante) et, sur L, à la reprise d'hibernation. La bascule depuis le `encrypt` qu'archinstall pose se fait une seule fois, dans les `custom_commands` d'archinstall (§7). |
| Wallet | **Déverrouillé automatiquement à l'autologin** avec la passphrase LUKS, via la recette du Arch Wiki « KDE Wallet » : `pam_systemd_loadkey` plus un override `KeyringMode=inherit` du service de connexion. |
| Clés GPG et SSH | **Déverrouillées par le wallet.** gpg-agent sert d'agent SSH partout (setup du travail). pinentry-qt enregistre la passphrase dans KWallet via le protocole Secret Service, qui la lui rend ensuite sans question. Détail et limites (laptop du travail) en §6. |
| Gestionnaire de connexion | **plasma-login-manager** (dépendance de `plasma-meta` 6.7), pas SDDM. |
| Pare-feu | **ufw géré par decman** (règles dans `/etc/ufw/`, `ENABLED=yes`, `ufw.service`). `plasma-firewall` est installé par `plasma-meta`, mais on ne s'en sert pas : decman écraserait ses modifications. |
| Outils de dev | **mise** est la source unique (config partagée avec le travail). Les outils propres au travail passent sous `work`. pacman fournit le système, le bureau, et ce qui doit exister avant mise. |
| Hostnames | `framework-gab-amd` (L sous Arch), `desktop-gab`. Le futur Intel prendra `framework-gab`, avec son propre module. |
| Réglages AMD du laptop | Conservés, puisque L passe sous Arch avant le Pro. |
| Emplacement GnuPG | Chemin par défaut `~/.gnupg` (§6). |
| Branche git par défaut | `main` en perso, `master` au travail. |
| Thème clair/sombre | La bascule automatique est **gardée** pour kitty, herdr, fish, starship, bat, eza, helix, fzf et claude. Catppuccin est **abandonné** pour plymouth, Konsole, btop, Zed et VS Code (leurs thèmes par défaut ou intégrés). |
| Config de `root` | Abandonnée. |
| Chiffrement chezmoi | `encryption = "transparent"` sur toutes les machines. Avec ce mode, chezmoi garde l'attribut `encrypted_` et laisse git-crypt chiffrer ([doc chezmoi « Transparent »](https://github.com/twpayne/chezmoi/blob/master/assets/chezmoi.io/docs/user-guide/encryption/transparent.md)). |
| Clé git-crypt | Saisie à la main depuis le gestionnaire de mots de passe (§7). |
| Secrets agenix du desktop | Re-chiffrés en git-crypt par un script que tu relis et que tu lances toi-même (phase 3, §5). |
| himalaya | Abandonné. Thunderbird : on restaure le profil. |

**Conséquences de l'absence de nix :**
- **srv-1 se déploie depuis srv-1** (`nixos-rebuild switch --flake .#srv-1` dans un clone). `agenix -e` aussi : il faut que ton identité y soit présente. La tâche `mise run srv-1` est à adapter, mais je ne touche pas à la config du serveur sans ton feu vert.
- **Hook pre-commit `nixfmt`** de nixos-config (`language: system`). Il exige `nixfmt` sur le PATH, et le paquet n'existe pas dans les dépôts officiels. Pistes : un binaire publié via mise (à vérifier), ou des commits faits depuis srv-1.
- **Abandonnés :** devenv, nil, nixd, direnv/nix-direnv, comma/nix-index, `~/.config/nixpkgs/config.nix`, le wrapper agenix, `NIX_CONFIG access-tokens`, le MCP `mcp-nixos` (possible via `uvx` si tu y tiens).

---

## 1. Corrections du brief (vérifiées)

| Affirmation du brief | Verdict | Source |
|---|---|---|
| decman supprime tout paquet explicite non déclaré | **Vrai, et même plus.** Il retire aussi les orphelins natifs et étrangers ; une dépendance non déclarée est rétrogradée en `--asdeps`. Un *groupe* déclaré est développé en membres explicites que decman tentera ensuite d'enlever : il faut des méta-paquets. Les exceptions passent par `decman.{pacman,aur,flatpak}.ignored_packages`. | [pacman.py L92-131](https://github.com/kiviktnm/decman/blob/main/plugins/decman-pacman/src/decman/plugins/pacman.py), [aur/\_\_init\_\_.py L168-214](https://github.com/kiviktnm/decman/blob/main/plugins/decman-pacman/src/decman/plugins/aur/__init__.py), [docs/pacman.md](https://github.com/kiviktnm/decman/blob/main/docs/pacman.md) |
| Déclarer base / linux / firmware / bootloader / decman avant le premier vrai run | **Vrai**, et aucune protection n'est intégrée. Il faut aussi `base-devel` et `git` (builds AUR), `btrfs-progs`, `snapper`, `efibootmgr` et `sudo` (§2.1). `decman` est dans l'AUR (1.2.2) et embarque les plugins pacman, systemd et flatpak. | [README « Installation »](https://github.com/kiviktnm/decman#installation), [AUR decman](https://aur.archlinux.org/packages/decman) |
| Flatpak : ajouter `"flatpak"` à `execution_order` | **Vrai**, car cette liste sélectionne aussi les plugins qui tournent. Défaut : `["files","pacman","aur","systemd"]`. API v1 : `decman.flatpak.packages` et `decman.flatpak.user_packages["user"]`. | [src/decman/\_\_init\_\_.py L69-74](https://github.com/kiviktnm/decman/blob/main/src/decman/__init__.py), [docs/flatpak.md](https://github.com/kiviktnm/decman/blob/main/docs/flatpak.md) |
| Active les unités sans les démarrer | **Vrai.** Il fait `systemctl enable` / `disable` plus un daemon-reload. Les unités utilisateur passent par `enabled_user_units`. | [docs/systemd.md](https://github.com/kiviktnm/decman/blob/main/docs/systemd.md), [systemd.py L159-183](https://github.com/kiviktnm/decman/blob/main/plugins/decman-systemd/src/decman/plugins/systemd.py) |
| `--dry-run --debug` : liste paquets et fichiers, sans diff ni versions, hooks sautés | **Vrai.** `--print` est un alias. | [app.py L30-37, L278-352](https://github.com/kiviktnm/decman/blob/main/src/decman/app.py), [core/fs.py L161-217](https://github.com/kiviktnm/decman/blob/main/src/decman/core/fs.py) |
| `--only` / `--skip` / `--no-hooks` | **Vrai.** Les valeurs sont des noms d'étapes. Un nom inconnu passé à `--skip` lève une `ValueError`. | [app.py L38-58, L239-256](https://github.com/kiviktnm/decman/blob/main/src/decman/app.py) |
| Choix du module par hostname | **Pas d'aide intégrée.** La source est du Python, donc on branche sur `socket.gethostname()`. `--source` est mémorisé. | [app.py L132-171](https://github.com/kiviktnm/decman/blob/main/src/decman/app.py) |
| `archinstall --config <url>` | **Faux.** Pour une URL, il faut `--config-url` (de même `--creds-url`). | [args.py L519-552](https://github.com/archlinux/archinstall/blob/master/archinstall/lib/args.py) |
| archinstall : LUKS + btrfs | **Vrai.** Défaut `@ @home @log @pkg`. `btrfs_options.snapshot_config: Snapper` configure snapper pour `/` et `/home`. | [default_layouts.py L130-139](https://github.com/archlinux/archinstall/blob/master/archinstall/lib/disk/default_layouts.py), [installer.py L982-1005](https://github.com/archlinux/archinstall/blob/master/archinstall/lib/installer.py) |
| (implicite) initramfs systemd | **Faux avec une passphrase simple.** archinstall pose le hook busybox `encrypt`, d'où la bascule en `custom_commands` (§7). | [installer.py L121-135, L838-884](https://github.com/archlinux/archinstall/blob/master/archinstall/lib/installer.py) |
| Panther Lake « veut ≥ 7.1 » | **Faux comme exigence.** Framework annonce : minimum 6.19, recommandé 7.0+. Le `linux` de core est en 7.2.7. | [frame.work/laptop13pro?tab=linux](https://frame.work/laptop13pro?tab=linux), [archlinux.org linux](https://archlinux.org/packages/core/x86_64/linux/) |
| `kwriteconfig6 --notify`, `--group` répété | **Vrai.** `--notify` ne recharge que les applications qui surveillent leur config (KConfigWatcher). | [kwriteconfig.cpp L24-96](https://invent.kde.org/frameworks/kconfig/-/blob/master/src/kreadconfig/kwriteconfig.cpp) |
| `plasma-apply-*`, scripts JS de panneaux | **Vrai.** Pour Qt6, c'est `qdbus6`. | [org.kde.PlasmaShell.xml L18](https://invent.kde.org/plasma/plasma-workspace/-/blob/master/shell/dbus/org.kde.PlasmaShell.xml) |
| Plasma + SDDM | **Obsolète.** `plasma-meta` 6.7 dépend de `plasma-login-manager` et de `plasma-firewall`, et ne tire pas `power-profiles-daemon`. | [plasma-meta (json)](https://archlinux.org/packages/extra/any/plasma-meta/json/) |
| Phase 4 : ajouter libvirt sur desktop | **Déjà fait** : `modules/nixos/desktop/virt.nix`, importé par desktop-gab seul. Il ne reste que la documentation de la boucle de test. | `hosts/desktop-gab/configuration.nix:8` |
| Disques en btrfs | **Faux aujourd'hui** : ext4 sur LUKS, avec un swap LUKS séparé. | `hosts/*/hardware-configuration.nix` |
| Secrets en git-crypt | **Partiel.** Seul dotfiles utilise git-crypt, avec une clé symétrique ; nixos-config utilise agenix. | `modules/home/gaugendre/desktop/age/` |

Le Arch Wiki bloque les lectures automatiques. Les pages KDE Wallet, Snapper et Framework Laptop 13 n'ont été vues qu'à travers des extraits de recherche ; à confirmer dans un navigateur.

---

## 2. Système

### 2.1 Installation, disque, boot

| Fonctionnalité (NixOS) | Hôte | Cible | Arch | Note |
|---|---|---|---|---|
| ext4 sur LUKS + swap LUKS | L+D | ai | — | btrfs `@ @home @log @pkg` sur LUKS, `compress=zstd`. L : plus une partition swap LUKS (plusieurs `obj_id` dans `disk_encryption.partitions`). D : zram. |
| Discards à travers LUKS | L+D | ai / man. | — | Option `discard` dans crypttab, ou `cryptsetup refresh --allow-discards --persistent` une fois. À vérifier dans la VM : archinstall le pose-t-il ? |
| systemd-boot | L+D | ai + dm | `limine limine-snapper-sync snap-pac` | decman gère **`/etc/default/limine`** (ligne de commande du noyau), **jamais `limine.conf`**, que `limine-snapper-sync` réécrit. |
| Paquets de base à protéger | L+D | dm | `base base-devel linux linux-firmware git sudo btrfs-progs snapper efibootmgr` + microcode + `decman` (AUR) | Sinon decman les retire. Comparer `pacman -Qqe` avec `--dry-run` avant le premier vrai run. |
| `kernelPackages` (L : `_latest` pour le correctif alarme RTC) | L+D | ai | `linux` | L'Arch stable (7.2.x) a le correctif. Contrôle : `test -e /sys/class/rtc/rtc0/wakealarm`. |
| initramfs systemd (`initrd.systemd.enable`) | L+D | ai (`custom_commands`) + dm | `mkinitcpio.conf` : `base systemd autodetect microcode modconf kms keyboard sd-vconsole block sd-encrypt filesystems fsck` | decman gère ensuite `mkinitcpio.conf`, qui ne dépend pas de l'hôte. `crypttab.initramfs` contient des UUID propres à chaque installation : il est **généré à l'installation** et n'est pas versionné. |
| `amdgpu` dans l'initrd | L+D | ✗ | — | Le hook `kms` charge déjà le pilote GPU. À remettre (`MODULES=(amdgpu)`) seulement si l'écran DisplayPort de D reste noir à l'invite LUKS. |
| Boot silencieux | L+D | dm | `quiet splash loglevel=3 rd.systemd.show_status=auto rd.udev.log_level=3` | `intremap=on` (déjà le défaut) et `boot.shell_on_fail` (propre à NixOS) : ✗. |
| plymouth (thème catppuccin mocha) | L+D | dm | `plymouth` + hook `plymouth` | Thème par défaut d'Arch, pas de catppuccin. `plymouth` va aussi dans la liste de paquets d'archinstall pour que le hook existe dès le premier build. |
| `amdgpu.dcdebugmask=0x10` (PSR, via nixos-hardware) | L | dm | cmdline | |
| blacklist `snd_acp70`, `snd_acp_pci` | L | dm | `/etc/modprobe.d/framework-acp.conf` | |
| `amd_pstate=active` | L | ✗ | — | Déjà le défaut du noyau. |
| `acpi_osi="!Windows 2015"` (veille sur la B650) | D | dm | cmdline | |
| microcode, firmware | L+D | ai | `amd-ucode`, `linux-firmware` | |
| catppuccin `tty` | L+D | ✗ | — | |

### 2.2 Base

| Fonctionnalité | Hôte | Cible | Arch | Note |
|---|---|---|---|---|
| `vim git ripgrep` | L+D | dm | idem | |
| fuseau Europe/Paris, locale `en_US` + `LC_*=fr_FR`, clavier `fr` | L+D | ai + dm | `/etc/locale.conf`, `/etc/vconsole.conf`, `/etc/X11/xorg.conf.d/00-keyboard.conf` | |
| fish comme shell de gaugendre | L+D | ai + dm | `fish` | root garde bash (config root abandonnée). |
| sudo NOPASSWD | L+D | dm | `/etc/sudoers.d/gaugendre` (0440) | |
| groupes | L+D | dm | `wheel docker uucp input libvirt` (libvirt sur D) | Sur Arch, les ports série sont en `uucp` (NixOS : `dialout`) et le groupe libvirt s'appelle `libvirt` (NixOS : `libvirtd`). |
| nix, nh, gc, `authorizedKeys`, `man.cache`, `allowUnfree` | L+D | ✗ | — | |
| Nettoyage du cache pacman (l'équivalent de `nix gc`) | L+D | dm | `pacman-contrib` + `paccache.timer` | |
| journald `SystemMaxUse=5G` | L+D | ✗ | — | Le défaut (10 % du FS, 4 Gio au plus) suffit. |

### 2.3 Bureau

| Fonctionnalité | Hôte | Cible | Arch | Note |
|---|---|---|---|---|
| Plasma 6 | L+D | dm | `plasma-meta` + applications (voir sous le tableau) | |
| Autologin | L+D | dm | config plasma-login-manager | Chemin exact du fichier à vérifier dans la VM. |
| Wallet ouvert à l'autologin | L+D | dm | une ligne `pam_systemd_loadkey` ajoutée à `/etc/pam.d/plasmalogin-autologin` (copie du fichier fourni dans `/usr/lib/pam.d/`) + drop-in `plasmalogin.service.d/keyring.conf` (`KeyringMode=inherit`) | Recette du Arch Wiki « KDE Wallet », sans réécriture de PAM. Le wallet a le même mot de passe que LUKS. |
| NetworkManager | L+D | dm | `networkmanager` + unité | |
| Impression | L+D | dm | `cups` + `cups.socket` | |
| fwupd | L+D | dm | `fwupd` | |
| Audio | L+D | dm | `pipewire pipewire-alsa pipewire-pulse wireplumber rtkit` | |
| Bluetooth | L+D | dm | `bluez bluez-utils` + `bluetooth.service` | |
| Polices | L+D | dm | `ttf-dejavu ttf-liberation noto-fonts noto-fonts-emoji ttf-jetbrains-mono-nerd ttf-fira-sans ttf-montserrat` | Polices sous licence : §5. |
| Docker | L+D | dm | `docker` + `docker.socket` | |
| Tailscale (client) | L+D | dm + man. | `tailscale` + `tailscaled.service` | Pas de sysctl : `rp_filter=2` est déjà le défaut systemd. **Contrôle après démarrage** : ufw peut le remettre à 1 via `/etc/ufw/sysctl.conf` (non vérifié), et c'est là qu'il faudrait corriger. |
| Pare-feu | L+D | dm | `ufw` + règles (KDE Connect 1714-1764/tcp+udp) | |
| iPhone | L+D | dm | `usbmuxd libimobiledevice ifuse` | |
| nRF Connect | L+D | dm (AUR) | `nrfconnect-appimage nrfutil nrf-udev jlink-software-and-documentation` | |
| Rotatrix | L+D | man. + dm | AppImage dans `~/Applications`, `fuse2`, `.desktop` d'autostart (cz) | D'abord laisser l'appli installer sa propre règle udev, ce qu'elle ne pouvait pas faire sur NixOS. À défaut, un seul fichier `/etc/udev/rules.d/70-rotatrix.rules` (hidraw + uinput en `TAG+="uaccess"`, `OPTIONS+="static_node=uinput"`). |
| Flatpak PrusaSlicer stable + beta | L+D | fp + man. | `flatpak` ; `com.prusa3d.PrusaSlicer` déclaré | flathub est livré par le paquet. `flathub-beta` et `//beta` sont ajoutés **une fois à la main**, puis `//beta` va dans `ignored_packages`. Les mises à jour passent par Discover ou `flatpak update`. |
| `uv-python` (nix-ld, cert.pem) | L+D | ✗ | — | Arch est FHS. |
| Applications | L+D | dm | repo : `partitionmanager bind wl-clipboard kate dolphin-plugins signal-desktop freecad graphviz chromium jq gcc calibre esphome firefox kdeconnect libreoffice-still kio thunderbird`. AUR : `rustdesk-bin pcloud-drive openscad-git solvespace koreader-bin` | `openscad-git` : compilation lourde (le `openscad` d'extra date de 2021). |
| Steam | L+D | ai + dm | `steam` (multilib) `vulkan-radeon lib32-vulkan-radeon lib32-mesa` | Clé multilib d'archinstall à confirmer. |
| gokrazy | L+D | mise | `go:github.com/gokrazy/tools/cmd/gok` | |

**Applications que NixOS installait avec Plasma et que `plasma-meta` ne tire pas** (relevé par `nix eval`) : `ark dolphin elisa gwenview okular konsole khelpcenter kwalletmanager kdegraphics-thumbnailers ffmpegthumbs kio-admin kio-extras qt6-tools`. Retire ce que tu n'utilises pas.

### 2.4 Laptop `framework-gab-amd` (L)

| Fonctionnalité | Cible | Arch | Note |
|---|---|---|---|
| **Hibernation** (veille, puis hibernation après 60 min) | dm + pl | swap LUKS dans `crypttab.initramfs` ; `/etc/systemd/sleep.conf.d/hibernate.conf` (`HibernateDelaySec=60min`) ; powerdevil `SleepMode=3` (§4) | Pas de `resume=` : l'initramfs systemd retrouve l'image via la variable EFI `HibernateLocation` (`man systemd-hibernate-resume-generator`). Une seule saisie de passphrase, grâce au cache de systemd-cryptsetup. Vérifier que swap ≥ RAM. `HibernateMode=shutdown` (qui évitait le réveil tout seul en S4) : à remettre seulement si le problème revient. |
| Pas de second mot de passe après une hibernation longue | dm | `/usr/lib/systemd/system-sleep/unlock-after-hibernate` | Gardé : Plasma n'a rien d'équivalent. Sur Arch, les hooks vont dans `/usr/lib/systemd/system-sleep/` (`man systemd-sleep`). |
| Empreinte digitale (verrouillage d'écran, pas le login) | dm + man. | `fprintd` | Plasma fournit `/etc/pam.d/kde-fingerprint`, sans toucher au login. `fprintd-enroll`. |
| Empreinte après une reprise de veille | dm (si besoin) | une unité `fprintd-sleep.service` | Bug réel côté fprintd. D'abord tester sans ; sinon une seule unité (`Before=sleep.target`, `ExecStart=` arrête fprintd, `ExecStop=` le redémarre et relance `kscreenlocker_greet`), sans script system-sleep. |
| Capot fermé sur secteur : rien (KVM) | pl | powerdevil `AC/SuspendAndShutdown LidAction=0` | |
| Réveil par le clavier/souris derrière le KVM | dm | `/etc/udev/rules.d/90-usb-wakeup.rules` | |
| Carte Ethernet Framework (autosuspend 0bda:8156) | dm | `/etc/udev/rules.d/90-framework-ethernet.rules` | Carte possédée, gardée. |
| Mesure batterie | dm | `powertop acpi` ; `powerstat` (AUR) | |
| Profils d'énergie, capteurs, TRIM | dm | `power-profiles-daemon iio-sensor-proxy` + `fstrim.timer` | power-profiles-daemon n'est pas tiré par plasma-meta. |
| Outil Framework | dm | `framework-system` (extra) | |
| `framework-laptop-kmod` | ✗ | — | Intégré au noyau depuis 6.10 (`cros_ec_lpcs`, `cros_charge-control`, `cros_ec_hwmon`). Le seuil de charge peut aussi se régler dans le BIOS. |

**Futur Framework 13 Pro (`framework-gab`)** : un module à part, avec `intel-ucode vulkan-intel lib32-vulkan-intel intel-media-driver`, sans les réglages AMD. Il reprend l'hibernation, le KVM, la carte Ethernet et l'empreinte.

### 2.5 Desktop `desktop-gab` (D)

| Fonctionnalité | Cible | Arch | Note |
|---|---|---|---|
| OpenRGB | dm | `openrgb` + `/etc/modules-load.d/i2c.conf` (`i2c-dev`, `i2c-piix4`) | Le serveur `openrgb --server` n'est à garder que si tu t'en sers. |
| VM (libvirt / virt-manager) | dm | `libvirt qemu-desktop virt-manager virtiofsd swtpm edk2-ovmf dnsmasq` + `libvirtd.socket` | |
| Veille sur la B650 | dm | `acpi_osi` (§2.1) | Optionnel : tester la veille sans. |

---

## 3. Home Manager → chezmoi / mise / pacman

« État » : **✓** déjà couvert dans dotfiles, **≈** couvert mais divergent, **✗** manquant.

| Module HM | Cible | État | À faire |
|---|---|---|---|
| git (`git.nix`) | cz | ≈ | Fusionner les alias HM (`statmain diffs restores prev next first pushf`) et ceux de dotfiles. `init.defaultBranch` main/master selon `work`. Sous `work` : git-town et `diff.tool = nvimdiff`. Paquets textconv : `git-lfs python-pygments pandoc-cli poppler perl-image-exiftool unzip`. |
| Paquets de `home.nix` | dm / mise | ✗ | pacman : `git-crypt watchexec vscode-json-languageserver yaml-language-server htop btop` ; AUR ou mise : `tlrc-bin git-toolbelt amber-search-bin terraform-ls-bin`. prek est déjà dans mise. |
| tmux, tldr-update, direnv, bash | ✗ | — | tlrc met son cache à jour tout seul. |
| gpg, gpg-agent | cz | ≈ | Voir §6. |
| ssh (hôtes `srv-1` avec ControlMaster, `hass`) | cz | ≈ | Blocs perso sous `not work`, `XAuthLocation` (chemin macOS) sous `darwin`. `AddKeysToAgent yes` importe la clé dans gpg-agent au premier usage. |
| fish (plugins, fonctions, greeting) | cz | ✓ | Supprimer `conf.d/fish_frozen_theme.fish` et l'ajouter à `.chezmoiremove` ; retirer `catppuccin/fish` de `fish_plugins`. Ajouter `~/.cargo/bin` au PATH. |
| bat, eza | cz | ≈ | Alias eza HM (`ls ll la lt lla`) si tu les utilises. |
| **theme-auto** (fish, bat, starship, eza, helix, fzf) | cz | ✗ | Cœur de la phase 3, en **un** fichier `conf.d` fish (`__theme_auto`) plus des thèmes épinglés (`.chezmoiexternal`). starship : un template, deux fichiers (latte/mocha). bat : `theme=auto`. helix : `catppuccin.toml` réécrit par le hook ; `theme = "adaptive"` disparaît. |
| helix (réglages, langages go/rust/lua) | cz | ≈ | Ajouter lua ; nix : ✗. |
| kitty | cz + pl | ≈ | Presque tout y est. Ajouter `no-preference-theme.auto.conf` ; templater `shell` et `herdr.session` (chemins `/home/gaugendr` du travail). `kdeglobals` → §4. |
| herdr | mise + cz | ≈ | Reprendre la version HM (`auto_switch`, latte/mocha) ; templater `default_shell`. |
| Konsole, btop, Zed, VS Code (thèmes catppuccin) | ✗ | — | Thèmes par défaut ou intégrés. Zed et VS Code suivent le clair/sombre du système (`theme.mode = "system"`, `window.autoDetectColorScheme`). Paquets `zed`, `visual-studio-code-bin` (AUR). VS Code : sa propre synchronisation des réglages plutôt que chezmoi. |
| krunner en démon | cz | ✗ | Pas d'unité maison : activer la `plasma-krunner.service` fournie par Plasma (un lien `…/plasma-workspace.target.wants/`), ou abandonner. |
| `kwallet-ssh` (`SSH_ASKPASS`, `PINENTRY_KDE_USE_WALLET`) | cz | ✗ | ksshaskpass est abandonné. `PINENTRY_KDE_USE_WALLET=1` est **gardé** (§6). |
| Email (Thunderbird + himalaya) | man. | — | himalaya : ✗. Thunderbird : restauration du profil. |
| Python, Go, Rust, Lua | mise + dm + cz | ≈ | Variables d'environnement Python ✓. `~/.config/go/env` (`CGO_ENABLED=0`). pacman : `rustup clang cargo-watch cargo-audit cargo-binstall luajit luarocks luacheck busted stylua lua-language-server`. |
| devenv, agenix, comma, nixpkgs config | ✗ | — | Pas de nix. |
| Polices sous licence | cz | ✗ | §5. |
| Token GitHub en lecture seule | cz | ≈ | Perso : `GITHUB_API_TOKEN`. Le `GITHUB_TOKEN` actuel (travail) passe sous `work`. |
| Claude Code (réglages, statusline, hook herdr, plugins, règles) | dm + cz | ≈ | `settings.json` en template : `ANTHROPIC_BASE_URL` et `crit` sous `work` ; `theme auto`, `language french` ; chemins via `.chezmoi.homeDir`. Statusline : fusion (garder le `LC_ALL=C`). Règles : sections Stash, wip et Références sous `work`. Paquet `claude-code` (AUR). |
| MCP home-assistant | cz | ✗ | Un `run_onchange_` : `claude mcp remove` puis `add-json --scope user`. La commande lit le token git-crypt (`sh -c 'HOMEASSISTANT_TOKEN=$(cat …) exec uvx ha-mcp'`), donc il n'est jamais écrit dans `~/.claude.json`. |
| `.face.icon` | cz | ✗ | Fichier binaire. |

**Côté dotfiles, travail transverse :**
- Un `.chezmoi.toml.tmpl` (`work`, `headless` via `promptBoolOnce` ; `encryption = "transparent"`). Les machines existantes gardent leurs valeurs.
- Un `.chezmoiignore` templaté :
  - réservé au travail : `.ovh.conf .terraformrc .netrc`, `fish/conf.d/host.fish`, les fonctions `corp interne k kctx kgetall kgpg kjsonlogs klogs kpass sdev ansible-encrypt-to-clipboard goland-here`, `jira-mcp`, `stash-mcp` ;
  - réservé au bureau Plasma : polices, `.face.icon`, scripts `kwriteconfig6`, `environment.d/pinentry.conf`.
- Chemins en dur `/home/gaugendr` → `.chezmoi.homeDir` (kitty, herdr, `dot_claude/settings.json`).

---

## 4. Plasma : clés réellement modifiées

Relevé par `nix eval`. J'ai écarté `kuriikwsfilterrc` (valeurs par défaut de plasma-manager) et `Battery`/`LowBattery LidAction=1` (défaut de Plasma).

| Fichier | Groupe(s) | Clé | Valeur | Hôte |
|---|---|---|---|---|
| kdeglobals | KDE | AutomaticLookAndFeel | true | L+D |
| kdeglobals | KDE | AutomaticLookAndFeelOnIdle | false | L+D |
| kdeglobals | General | TerminalApplication | kitty | L+D |
| kdeglobals | General | TerminalService | kitty.desktop | L+D |
| kwinrc | TabBox | ApplicationsMode | 1 | L+D |
| kwinrc | TabBox | HighlightWindows | false | L+D |
| kwinrc | TabBox | LayoutName | big_icons | L+D |
| baloofilerc | General | `exclude folders[$e]` | `$HOME/pCloudDrive/` | L+D |
| kglobalshortcutsrc | plasmashell | activate application launcher | `Alt+F1,,` | L+D |
| kglobalshortcutsrc | kwin | Walk Through Windows | `Meta+Tab,,` | L+D |
| kglobalshortcutsrc | kwin | Walk Through Windows (Reverse) | `Meta+Shift+Tab,,` | L+D |
| kglobalshortcutsrc | kwin | Walk Through Windows of Current Application Alternative | `Alt+Tab,,` | L+D |
| kglobalshortcutsrc | kwin | Walk Through Windows of Current Application Alternative (Reverse) | `Alt+Shift+Tab,,` | L+D |
| powerdevilrc | AC → SuspendAndShutdown | LidAction | 0 | L |
| powerdevilrc | AC / Battery / LowBattery → SuspendAndShutdown | SleepMode | 3 | L |

Points pratiques :
- Les groupes imbriqués s'écrivent avec `--group` répété.
- La clé baloo contient `[$e]`, à passer littéralement.
- **Raccourcis :** kglobalacceld ne relit pas son fichier. On les écrit avant la première connexion graphique : le `chezmoi apply` se fait depuis un TTY (§7).
- Aucun panneau n'est déclaré : pas de script JS.

---

## 5. Secrets

| Secret agenix | Usage | Cible (git-crypt, dotfiles) |
|---|---|---|
| `ro-github-token.age` | `GITHUB_API_TOKEN` | `.secrets/encrypted_ro_github_token` |
| `ha-mcp-token.age` | MCP home-assistant | `.secrets/encrypted_ha_mcp_token` |
| `fonts/*.otf.age` (16) | kitty | `dot_local/share/fonts/encrypted_<nom>.otf`, couverts par le `encrypted_*` de `.gitattributes`. |
| `migadu-password.age` | himalaya | ✗ : himalaya est abandonné et Thunderbird garde son mot de passe dans le profil restauré. `git send-email` utilise déjà `.secrets/encrypted_smtp_password`. |

Le script (phase 3, à relire puis lancer toi-même) :
1. déchiffre chaque `.age` avec `age -d -i ~/.config/agenix/identity.txt` ;
2. écrit le résultat dans le dépôt dotfiles déverrouillé ;
3. vérifie avec `git-crypt status` que chaque nouveau fichier sera bien chiffré ;
4. ne commite rien.

Les secrets de srv-1 ne sont pas touchés.

---

## 6. GnuPG, SSH et wallet

**Choix de base : GnuPG dans `~/.gnupg` (chemin par défaut) et gpg-agent comme agent SSH.** `~/.local/share/gnupg` est abandonné. Hors du chemin par défaut, les sockets `gpg-agent*.socket` fournis par Debian, Ubuntu et Arch ne correspondent plus, et le contournement demanderait des drop-ins calculés sur chaque machine. Sources : listes de fichiers [Debian](https://packages.debian.org/bookworm/amd64/gpg-agent/filelist), [Ubuntu](https://packages.ubuntu.com/noble/amd64/gpg-agent/filelist), [Arch](https://archlinux.org/packages/core/x86_64/gnupg/files/) ; [gnupg homedir.c](https://github.com/gpg/gnupg/blob/STABLE-BRANCH-2-4/common/homedir.c).

**`SSH_AUTH_SOCK` sur Arch.** Il n'est pas publié automatiquement :
- Le patch 0013 qui injecte la variable ne modifie que les unités d'exemple de la documentation.
- Arch installe ses propres `.socket` depuis son dépôt de packaging, et `gpg-agent-ssh.socket` n'y a pas de `ExecStartPost` (vérifié dans [gitlab.archlinux.org/…/gnupg](https://gitlab.archlinux.org/archlinux/packaging/packages/gnupg)).
- D'où un fichier chezmoi `~/.config/environment.d/50-gpg-agent.conf` : `SSH_AUTH_SOCK=${XDG_RUNTIME_DIR}/gnupg/S.gpg-agent.ssh`.
- Le `set -gx SSH_AUTH_SOCK (gpgconf …)` de fish couvre les sessions SSH et les machines sans session graphique.

**Déverrouillage des clés par le wallet.**
- **Le principe :** gpg-agent demande la passphrase à pinentry. pinentry-qt la lit, et la stocke au premier usage si l'on coche « enregistrer », dans le gestionnaire de secrets du bureau, via Secret Service. KWallet fournit Secret Service, et il est ouvert à l'autologin (§2.3). Résultat : aucune question, ni pour les commits signés ni pour SSH.
- **Sur KDE, pinentry désactive exprès cette intégration**, sauf si `PINENTRY_KDE_USE_WALLET` est défini ([pinentry.c](https://github.com/gpg/pinentry/blob/master/pinentry/pinentry.c), variable introduite en 1.3.1). La variable doit arriver jusqu'à pinentry, qui est lancé par gpg-agent, lui-même lancé par systemd. Elle va donc dans `environment.d`, pas dans fish.
- **Arch** : pinentry 1.3.3, compilé avec libsecret ([paquet](https://archlinux.org/packages/core/x86_64/pinentry/json/)). Il faut aussi `kguiaddons` et `kwindowsystem`, déjà là avec Plasma. `pinentry-program /usr/bin/pinentry-qt` va dans `gpg-agent.conf`, sous `not headless`. À vérifier dans la VM : que KWallet 6 expose bien Secret Service par défaut.
- **Laptop du travail (Ubuntu 24.04, Plasma Wayland), constaté sur la machine :**
  - le coffre Secret Service y est **gnome-keyring** (`gnome-keyring-daemon` possède `org.freedesktop.secrets`) ;
  - gpg-agent y utilise **`pinentry-gnome3`** 1.2.1, qui a libsecret ;
  - après `gpgconf --reload gpg-agent`, un `gpg --clearsign` passe sans dialogue : la passphrase vient du coffre ;
  - le blocage KDE de pinentry ne s'y applique pas : `XDG_SESSION_DESKTOP=plasmawayland`, et pinentry ne compare qu'à `KDE` ;
  - `SSH_AUTH_SOCK` est publié dans la session par le patch Debian.
  
  **Ça marche déjà, on n'y touche pas** : les dotfiles ne posent `pinentry-program` que sur Arch (template sur `.chezmoi.osRelease.id`).
- **Sur Arch, KWallet et non gnome-keyring**, parce que c'est le coffre natif de Plasma et qu'il est déjà ouvert à l'autologin. Deux coffres en concurrence pour Secret Service ne feraient que compliquer les choses. `PINENTRY_KDE_USE_WALLET=1` est gardé : il est sans effet si `XDG_SESSION_DESKTOP` n'y vaut pas `KDE` (non vérifié). **Repli** si la VM montre que KWallet n'expose pas Secret Service : reprendre le setup du travail (`gnome-keyring` + `pinentry-gnome3`).
- **Headless (serveur du travail)** : pas de wallet ; on garde le TTL long actuel.

**Migration des clés.** Elles sont aujourd'hui dans `~/.local/share/gnupg` (NixOS). On les restaure dans `~/.gnupg` (`gpg --export-secret-keys` / `--import`, ou copie du dossier, `chmod 700`). La clé SSH s'importe dans gpg-agent avec `ssh-add ~/.ssh/id_ed25519`. srv-1 n'est pas touché.

---

## 7. Étapes

**Avant d'effacer (par machine)**
1. Sauvegarder :
   - `~/.config/agenix/identity.txt` (indispensable, y compris pour srv-1) ;
   - `~/.local/share/gnupg` ;
   - `~/.ssh` ;
   - le profil Thunderbird ;
   - `~/Projects` ;
   - `/etc/rotatrix-key` ;
   - les VM (D) ;
   - la bibliothèque Steam, si tu ne veux pas la retélécharger.
2. Lancer le script de re-chiffrement (§5) **avant** d'effacer la dernière machine NixOS qui contient ces secrets.

**Installation**
1. `archinstall --config-url <url>/user_configuration.json --creds <fichier local>`. Les `custom_commands` s'exécutent dans le chroot et font la bascule vers l'initramfs systemd **en une fois** :
   1. HOOKS systemd dans `mkinitcpio.conf` ;
   2. `/etc/crypttab.initramfs` généré avec `blkid` (racine, plus le swap sur L) ;
   3. `mkinitcpio -P`.
   
   À valider dans la VM : que ces commandes tournent bien après l'installation du bootloader.
2. Installer `decman` depuis l'AUR (`makepkg`), puis `sudo decman --source …/source.py --dry-run --debug`. Comparer avec `pacman -Qqe`, puis lancer le vrai run.

**Amorçage chezmoi** (depuis un TTY, avant la première connexion graphique)
1. `chezmoi init <repo>`, sans `--apply` : les templates incluent des fichiers git-crypt.
2. La clé git-crypt vient du gestionnaire de mots de passe. `git-crypt export-key` produit un binaire : s'il est stocké en base64, `base64 -d > /tmp/gc.key`. Puis `git-crypt unlock /tmp/gc.key` dans `~/.local/share/chezmoi`, et `shred -u /tmp/gc.key`.
3. `chezmoi apply`, puis `mise install`, `rustup default stable`, `fisher update`.
4. Restaurer `~/.gnupg`, puis `ssh-add ~/.ssh/id_ed25519`. À la première demande de passphrase, cocher « enregistrer ».

**Comptes et services**
- `tailscale up` ;
- appairage KDE Connect ;
- connexions : Signal, pCloud, Steam, VS Code (synchronisation des réglages), `claude` ;
- restauration du profil Thunderbird ;
- `herdr integration install claude` ;
- `fprintd-enroll` (L) ;
- `fwupdmgr refresh && fwupdmgr update` ;
- `flatpak remote-add flathub-beta …` puis installer PrusaSlicer `//beta` ;
- Rotatrix : la clé, l'AppImage, et supprimer l'ancien addon FreeCAD.

**Contrôles après le premier démarrage** :
- `sysctl net.ipv4.conf.all.rp_filter` doit valoir 2 (Tailscale) ;
- `test -e /sys/class/rtc/rtc0/wakealarm` (L) ;
- une hibernation, puis une reprise (L) ;
- `ssh-add -l` depuis une application graphique.

**Secure Boot (optionnel, plus tard).** `sbctl create-keys`, `enroll-keys -m`, signer l'EFI de Limine, puis `limine enroll-config`.

---

## 9. Plan de réalisation et de test

Une couche à la fois, chacune validée dans une VM avant de passer à la suivante, en repartant d'un état propre. On fait une pause de relecture à la fin de chaque étape, avec un commit par étape dans `arch-config`.

**Étape 0 : banc de test** (sur desktop-gab, encore sous NixOS)
- libvirt et virt-manager y sont déjà (`virt.nix`) : rien à modifier dans nixos-config.
- La VM est en UEFI, sans Secure Boot, avec une NVRAM persistante (nécessaire pour Limine et `HibernateLocation`). Elle démarre sur l'ISO Arch.
- États sauvegardés : des disques de base qcow2 en lecture seule, un disque de travail en overlay, et une copie de la NVRAM à chaque état. « Revenir à un état », c'est recréer l'overlay et restaurer la NVRAM.
- Les fichiers passent de l'hôte à la VM par `scp`, en SSH vers l'ISO live : pas de serveur HTTP, et rien à ouvrir dans le pare-feu NixOS.
- Tout est décrit dans `vm/README.md`.

**Étape 1 : archinstall**
- On itère sur `archinstall/user_configuration.json` jusqu'à obtenir LUKS + btrfs, la partition swap (L), Limine, snapper, et la bascule vers l'initramfs systemd dans les `custom_commands`.
- Critère de réussite : une seule saisie de la passphrase, puis le démarrage sur un TTY.
- À vérifier au passage : le swap dans crypttab, les discards, et l'ordre d'exécution des `custom_commands`.
- Sauvegarde de l'état **post-archinstall**.

**Étape 2 : decman**, module par module, en revenant à post-archinstall pour chaque essai complet.
1. `base` : `--dry-run` comparé à `pacman -Qqe`, qui ne doit proposer de retirer aucun paquet utile ; puis le vrai run.
2. `snapshots` : snap-pac et limine-snapper-sync, avec un démarrage sur un snapshot.
3. `desktop` : Plasma, plasma-login-manager, l'autologin, le wallet ouvert à l'autologin, ufw.
4. Modules d'hôte : la VM prend tour à tour le hostname `framework-gab-amd`, puis `desktop-gab`. L'hibernation se teste dans la VM.

Sauvegarde de l'état **post-decman**.

**Étape 3 : chezmoi** (branche dans dotfiles)
- **Prérequis :** tu lances le script de re-chiffrement des secrets (§5).
- **Dans la VM**, depuis post-decman : `chezmoi init`, `git-crypt unlock`, puis `chezmoi apply` depuis un TTY. À la première connexion graphique, on contrôle le thème auto, les polices, les clés Plasma et le déverrouillage GPG/SSH par le wallet.
- **Garde-fou avant la fusion :** `chezmoi diff` sur le laptop du travail et sur le serveur du travail. Il ne doit montrer que les changements voulus.

**Étape 4 : matériel réel.** D'abord le laptop AMD (desktop-gab reste sous NixOS et continue de servir de banc), le desktop en dernier. Contrôles impossibles en VM :
- hibernation réelle et réveil RTC ;
- empreinte digitale ;
- réveil par le KVM ;
- carte Ethernet ;
- réglages AMD ;
- sur le desktop, l'écran DisplayPort à l'invite LUKS et la veille (`acpi_osi`).

---

## 8. Paquets Arch : méthode

- **Dépôts officiels :** vérifiés via `archlinux.org/packages/…/json`.
- **AUR :** vérifié via le miroir GitHub officiel `archlinux/aur`, car aur.archlinux.org bloque les requêtes automatiques.
- **Encore à confirmer en phase 2 :** la clé multilib d'archinstall, le fichier d'autologin de plasma-login-manager, et l'ordre d'exécution des `custom_commands`.
