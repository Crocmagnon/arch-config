# YubiKey Bio : reste à faire

La config est dans decman (`desktop.py`, `files/desktop/kde-fingerprint`, `files/desktop/u2f_mappings`), et documentée dans `CLAUDE.md` et le README. Elle est vérifiée sur `framework-gab` (19/10/2026). Ce fichier disparaîtra une fois le desktop vérifié.

## À vérifier sur `desktop-gab`

`desktop-gab` n'a pas `fprintd`, donc la ligne `-auth required pam_fprintd.so` y vise un module absent.

1. **Sécurité d'abord.** Verrouiller avec la clé absente, ou le KVM sur le laptop, puis revenir et attendre sans toucher la clé. L'écran ne doit **pas** se déverrouiller tout seul. Si c'est le cas, le module absent ne compte pas comme un échec, et la pile finit sur `pam_permit` : supprimer aussitôt `/etc/pam.d/kde-fingerprint` et revoir le fichier.
2. Clé présente : verrouiller, poser le doigt, l'écran doit se déverrouiller.
3. **Le cas général** : verrouiller pendant que le KVM est sur le laptop, revenir, puis poser le doigt. Sur le laptop, ce cas fonctionne. Mais `fprintd` y attend peut-être un doigt, puis kscreenlocker relance la pile, et cette fois `pam_u2f` trouve la clé. Sans `fprintd`, `pam_u2f` échoue tout de suite : reste à voir si kscreenlocker relance quand même la pile. Sinon, la piste est `kde-smartcard`, qui attend une carte (voir `CLAUDE.md`).
4. Vérifier aussi que kscreenlocker propose l'empreinte sans capteur `fprintd`. Ses réglages « Fingerprint » et « Smartcard » sont dans Configuration du système, Verrouillage d'écran.

## Références

- [Arch Wiki : U2F](https://wiki.archlinux.org/title/U2F)
- [Yubico pam-u2f](https://developers.yubico.com/pam-u2f/)
