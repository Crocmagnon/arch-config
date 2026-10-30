# Essai de niri à côté de Plasma

## Intention

Gabriel est curieux du tiling scrollable et d'un usage tout au clavier. Plasma lui convient : niri est une expérience, pas un remplacement. Il ne connaît pas niri, la config part donc des défauts de niri.

## Objectifs

- Une session niri, choisie sur l'écran de connexion, à côté de la session Plasma, sur desktop-gab d'abord.
- Dans cette session : un lanceur d'applis, un écran de verrouillage où la YubiKey Bio marche comme sous Plasma, plusieurs écrans en extension, les notifications (rappel hebdo de `maintenance.py`), un agent polkit. *(Partage d'écran retiré du premier essai : son portail tire Nautilus et un indexeur jusque dans Plasma.)*
- Tout le côté système dans **un seul module decman, `decman/niri.py`**. Pour le retirer, on enlève `Niri()` de `source.py` puis on lance `sudo decman`. Côté dotfiles, la config niri tient dans un dossier qu'on supprime.

## Non-objectifs (pour plus tard, le laptop)

- Le capot et la mise en veille puis l'hibernation sans powerdevil (`HandleLidSwitch=suspend-then-hibernate` côté logind, ou `SuspendThenHibernate` côté Dux Shell).
- La duplication d'écran vers un projecteur (`wl-mirror`).
- L'empreinte fprintd au verrouillage.
- Remplacer Plasma, changer l'autologin, retrouver les raccourcis de Plasma, le thème.

## Anti-objectifs (échec même si ça marche)

- Un changement visible sous Plasma : paquets en conflit, autre agent polkit, autre portail, variables d'environnement qui fuient dans la session Plasma.
- Toucher `/etc/pam.d/login` ou `kde-fingerprint`.
- Un paquet AUR.
- Revenir à Plasma demande autre chose que se déconnecter et choisir Plasma.

## Contraintes et faits établis

Recherche du 30/10/2026 :
- niri 26.04 est dans `extra`. Le paquet livre `niri.desktop` (session Wayland) et `niri-portals.conf`, qui préfère les portails `gnome;gtk`. xwayland-satellite est intégré depuis niri 25.08 : il ne manque que le paquet `xwayland-satellite`.
- **Dux Shell** (ex-DankMaterialShell, renommé le 21/10/2026, binaire `dms`) est dans `extra` (`dux-shell`). Il dépend de `quickshell` et `accountsservice`. Il fournit lanceur, notifications, agent polkit, OSD, réglage des écrans, verrouillage et presse-papiers. **Choisi plutôt que Noctalia**, dont le verrou est figé sur le service PAM `login` et n'accepte qu'un prompt.
- Verrouillage Dux Shell (`quickshell/Modules/Lock/Pam.qml`) : il essaie `/etc/pam.d/dankshell-u2f` pour la clé. En `u2fMode` `or`, la clé suffit, mais la pile ne démarre qu'à la demande (Ctrl+Q si `lockScreenSecurityKeyShortcutEnabled`, ou le bouton clé de sécurité) et s'annule après 30 s *(corrigé après relecture du code : pas au simple affichage du verrou)*. Il obéit à `loginctl unlock-sessions` et pose `LockedHint`.
- *(Retiré du premier essai.)* `xdg-desktop-portal-gnome` serait nécessaire au partage d'écran sous niri. `xdg-desktop-portal-kde` reste en place pour Plasma : `niri-portals.conf` ne le sélectionne pas.
- Applis KDE hors Plasma : il faut `QT_QPA_PLATFORMTHEME=kde`, sinon le thème est perdu, et `XDG_MENU_PREFIX=plasma-`, sinon le menu « Ouvrir avec » de Dolphin est vide. Ces deux variables ne doivent valoir **que dans la session niri** : à poser dans le bloc `environment {}` de `config.kdl`, pas dans `environment.d` (dotfiles), qui sert aussi à Plasma.
- Le portefeuille KDE a un mot de passe vide et s'ouvre par activation D-Bus : il doit marcher sans autologin. C'est une déduction, à vérifier.

## Décisions

### decman : `decman/niri.py`

- La classe `Niri(Module)` déclare les paquets `niri`, `dux-shell` et `xwayland-satellite`. Aucune dépendance optionnelle de Dux Shell n'est ajoutée au départ.
- Elle pose `/etc/pam.d/dankshell-u2f`, dans `decman/files/niri/`. Son contenu est la pile YubiKey de `kde-fingerprint` : `u2f-wait-key` puis `pam_u2f`, trois fois, avec les mêmes options (`authfile=/etc/u2f_mappings origin=pam://gab appid=pam://gab userverification=1 pinverification=0 cue`). Il n'y a pas de fprintd. L'en-tête et les lignes `account`/`session` sont à adapter à un service de verrou. Le `debug` temporaire de `kde-fingerprint` (commit 5d9ae1d) est à reprendre seulement s'il y est encore.
- La ligne de `source.py` ajoute `Niri()` aux modules communs, donc sur les deux hôtes : le laptop n'y gagne qu'une session de plus, inutilisée. `u2f-wait-key`, `/etc/u2f_mappings` et `pam-u2f` restent dans `desktop.py`, d'où le module les utilise.
- `CLAUDE.md` et `README.md` : une entrée sur le module niri (rôle, retrait en une ligne, service PAM du verrou).

### dotfiles

- `dot_config/niri/config.kdl` : la config par défaut de niri (`default-config.kdl` du paquet), avec le minimum de retouches :
  - le terminal de `Mod+T` est `kitty` (alacritty n'est pas installé) ;
  - le lanceur, la session et le verrou passent par Dux Shell : `Mod+D` remplace fuzzel, et Dux Shell est lancé au démarrage, selon sa doc niri ;
  - le bloc `environment {}` pose les deux variables KDE ;
  - les sorties de desktop-gab sont décrites, ou laissées à Dux Shell (voir « Laissé au builder »).
- Arch seulement : une ligne dans `.chezmoiignore` exclut `.config/niri` hors Arch, selon la convention du dépôt (`.chezmoi.osRelease.id "arch"`). Les rendus sur les machines du boulot doivent rester identiques à l'octet près.
- Les réglages de Dux Shell (écrits par son interface) ne sont **pas** versionnés pendant l'essai. *(Mon choix : un JSON réécrit par une GUI se gère mal dans chezmoi, à revoir si l'essai est concluant.)*

### Verrouillage, inactivité, veille

*(Mes choix.)* Dux Shell reproduit le comportement de Plasma :
- **Verrouillage avant la veille** (`lockBeforeSuspend`) et intégration logind (`loginctlLockIntegration`). Une session non verrouillée au réveil serait un trou de sécurité.
- **Délais d'inactivité calqués sur les défauts de Plasma 6**, puisque desktop-gab n'a ni `powerdevilrc` ni `kscreenlockerrc` : verrou à 5 min, extinction de l'écran et veille aux délais par défaut de powerdevil sur secteur, à relever par le builder dans la source de powerdevil.

Ces réglages vivent dans le JSON de Dux Shell, qui n'est pas versionné. Comme pour `u2fMode`, le builder dit à Gabriel quoi régler, ou passe par `dms` si une commande le permet.

### Environnement des applis KDE

*(Mon choix.)* Dux Shell est lancé par `spawn-at-startup`, pas par une unité systemd utilisateur. Ainsi, ce qui part de son lanceur hérite du bloc `environment {}`.
- **Limite acceptée :** une appli lancée par activation D-Bus, donc par le gestionnaire systemd utilisateur, n'a pas ces variables. Dolphin ouvert depuis un navigateur peut perdre son thème.
- **Pourquoi on ne les importe pas dans systemd :** elles fuiraient vers Plasma si le gestionnaire utilisateur survit à la déconnexion.
- Limite à noter dans `CLAUDE.md`.

### Autostart

*(Mon choix.)* Les entrées XDG existantes tournent aussi sous niri, sans `NotShowIn` :
- `gpg-agent-display` y est nécessaire pour pinentry ;
- `KTailctl`, `pcloud` et `rotatrix` devraient marcher hors KWin ;
- le notifier Discover est déjà masqué.

Si l'une casse sous niri, on l'exclut au cas par cas, avec `NotShowIn=niri;` côté dotfiles.

### Retour en arrière

- **Ponctuel :** se déconnecter de niri et choisir Plasma sur l'écran de connexion. L'autologin reste `Session=plasma`.
- **Définitif :** retirer `Niri()` de `source.py` et lancer `sudo decman`, qui désinstalle les paquets et supprime le fichier PAM. Puis supprimer `dot_config/niri` de dotfiles et l'ajouter à `.chezmoiremove`.

## Laissé au builder

- La façon de lancer Dux Shell sous niri et de câbler ses raccourcis : `spawn-at-startup`, unité systemd utilisateur, ou les fichiers que `dms` propose d'inclure dans `config.kdl`. Suivre la doc Dux Shell actuelle, avec le moins de config possible.
- Le réglage `u2fMode` `or` de Dux Shell : il vit dans ses réglages utilisateur. Dire à Gabriel où le cocher, ou le poser par la commande `dms` si elle existe.
- Les sorties de desktop-gab : les décrire dans `config.kdl` (noms relevés par `niri msg outputs`) ou laisser niri les détecter. Préférer la détection tant qu'elle convient.
- Le test : le banc VM (`vm/README.md`) si niri y démarre (GPU virtio), sinon directement sur desktop-gab, puisque revenir à Plasma ne coûte qu'une déconnexion. Dans les deux cas, une `--dry-run` decman d'abord, comparée à `pacman -Qqe`.

## À vérifier sur la machine

1. La session niri apparaît sur l'écran de connexion. La session Plasma est inchangée après un aller-retour.
2. Mod+D ouvre le lanceur, et Mod+T ouvre kitty.
3. Le verrou se déverrouille au doigt sur la YubiKey, y compris quand le verrou a été pris KVM basculé ailleurs. Le mot de passe marche en secours.
4. Une notification `notify-send` s'affiche, et une action admin (`pkexec true`) affiche l'agent polkit de Dux Shell.
5. Les écrans sont en extension, chacun avec ses espaces de travail.
7. Dolphin garde le thème KDE et son menu « Ouvrir avec ». Le portefeuille s'ouvre sans demander de mot de passe.
8. Le verrou se met avant la veille (`systemctl suspend`) et après 5 min d'inactivité.
9. `gpg-agent-display`, KTailctl, pCloud et Rotatrix démarrent sous niri sans erreur.
10. Réveil derrière le KVM : noter si l'écran revient. `journalctl -t drm-redetect` donne la comparaison avec Plasma.
