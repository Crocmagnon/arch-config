# YubiKey Bio : notes de travail

Travail en cours, à reprendre à la réception de la clé. Ces notes disparaîtront une fois la config intégrée à decman, `CLAUDE.md` et `README.md` (comme `MIGRATION.md`).

## Objectif

Une empreinte pour sudo et le verrouillage Plasma, sur les deux machines perso, au bureau, derrière le KVM :
- `desktop-gab` n'a pas de capteur ;
- `framework-gab` sert souvent capot fermé, ce qui rend inaccessible son capteur Goodix intégré au bouton d'alimentation (`27c6:609c`, déjà géré par `fprintd`, trois doigts enrôlés).

Le laptop du bureau est hors périmètre : c'est la YubiKey de l'entreprise qui s'impose, et il n'y a pas d'accès root.

## Décision

Une YubiKey Bio FIDO Edition (USB-A, pour le KVM), avec `pam-u2f`. Les empreintes sont stockées dans la clé : elle sert aux deux machines sans réenrôlement.

Options écartées :
- **un lecteur libfprint externe** : sur le laptop, il entrerait en concurrence avec le Goodix, et `pam_fprintd` n'utilise qu'un capteur ;
- **les Kensington VeriMark et les dongles CS9711** : pas de pilote libfprint upstream ;
- **les claviers à lecteur** : Windows Hello uniquement.

Moins chère mais moins sûre sous Linux : Token2 PIN+ Bio3 (37 €).

## Établi (avant réception)

- **Le PIN FIDO2 est obligatoire pour enrôler les empreintes.** `ykman fido access change-pin`, puis `ykman fido fingerprints add`. Ensuite, `userverification=1 pinverification=0` ne demande que le doigt. La biométrie se bloque après plusieurs échecs d'affilée et exige alors le PIN (nombre exact à vérifier).
- **Fichiers PAM sur ce système :**
  - `kde-fingerprint` est fourni par `kscreenlocker` dans `/usr/lib/pam.d/` (`-auth required pam_fprintd.so`). Un fichier du même nom dans `/etc/pam.d/` le remplace : c'est là que decman devra l'écrire, en reprenant tout son contenu.
  - `/etc/pam.d/sudo` inclut `system-auth`.
- **Sur le laptop, `pam_u2f` passe avant `pam_fprintd`.** Dans l'ordre inverse, capot fermé, `fprintd` attend jusqu'à son délai d'expiration un doigt sur un capteur inaccessible.
- **Le mot de passe reste en repli** (`sufficient`), pour ne pas risquer de s'enfermer dehors.

## Problème ouvert : la clé branchée à chaud, écran verrouillé

C'est le cas **général** au bureau : le laptop se verrouille pendant que le KVM est sur le desktop. Au retour, on bascule le KVM, et la clé apparaît après le lancement de l'authentification. Or `pam_u2f` cherche la clé au démarrage de l'authentification, ne l'attend pas, et échoue tout de suite si elle est absente.

Pistes, dans l'ordre :
1. **Tester d'abord** si kscreenlocker relance l'authentification par empreinte après un échec (au réveil de l'écran, au clic, au mouvement de souris).
2. **Utiliser le service `kde-smartcard`.** kscreenlocker l'exécute en parallèle du mot de passe, et le fichier fourni attend la carte (`pam_pkcs11 wait_for_card`). On pourrait écrire un `/etc/pam.d/kde-smartcard` où un `pam_exec` attend qu'une clé FIDO apparaisse, suivi de `pam_u2f`. Le mot de passe fonctionnant en parallèle, cette attente ne bloque rien. À vérifier : la condition dans laquelle kscreenlocker active ce service (peut-être seulement si `pam_pkcs11` est présent).
3. **Faire attendre `kde-fingerprint` selon le capot** (`/proc/acpi/button/lid/LID0/state`) : capot fermé, attendre la clé puis `pam_u2f` ; capot ouvert, passer à `pam_fprintd`.

À exclure : une règle udev qui déverrouille la session à l'apparition de la clé. Ce serait un contournement de l'authentification.

## Plan de test à réception

1. `pacman -S yubikey-manager pam-u2f` en local, sans decman pour l'instant. Définir le PIN, enrôler 2 ou 3 doigts.
2. `pamu2fcfg -u gaugendre -o pam://gab -i pam://gab`. Avec un `origin` commun, un seul fichier de mapping sert aux deux machines. Le placer dans un `authfile` système, par exemple `/etc/u2f_mappings`. Il ne contient pas de secret : un handle de clé et une clé publique.
3. sudo : ajouter `auth sufficient pam_u2f.so authfile=/etc/u2f_mappings cue userverification=1 pinverification=0` en tête de `/etc/pam.d/sudo`. Garder un shell root ouvert et tester avec `sudo -K && sudo true` :
   - clé présente ;
   - clé absente : vérifier que l'échec est rapide.
4. Écran de verrouillage : copier `kde-fingerprint` dans `/etc/pam.d/` avec `pam_u2f` avant `pam_fprintd`. Tester :
   - capot ouvert sans la clé ;
   - capot fermé avec la clé ;
   - **verrouillage avec le KVM sur le desktop, puis bascule** : c'est le cas ouvert, à traiter avec les pistes ci-dessus.
5. Même chose sur `desktop-gab`, sans `pam_fprintd`.
6. Puis intégrer à decman : un module commun aux deux machines (paquets, `/etc/u2f_mappings`, fichiers PAM), une entrée de règle dans `CLAUDE.md`, et une étape d'installation dans le README (enrôlement, `pamu2fcfg`).

## Références

- Achat (prix relevés le 2026-10-16) :
  - YubiKey Bio FIDO Edition, environ 110 à 118 € : [Yubico FR](https://www.yubico.com/fr/product/yubikey-bio/), [Amazon.fr](https://www.amazon.fr/Yubico-YubiKey-Bio-FIDO-USB/dp/B09KM668XJ) ;
  - Token2 PIN+ Bio3, 37 € : [Token2](https://www.token2.com/shop/product/token2-pin-bio3-fido2-security-key-with-biometric-authentication).
- [Liste des périphériques supportés par libfprint](https://fprint.freedesktop.org/supported-devices.html)
- [Arch Wiki : U2F](https://wiki.archlinux.org/title/U2F)
- [Yubico pam-u2f](https://developers.yubico.com/pam-u2f/)
