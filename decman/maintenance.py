# Ce qu'une mise à jour d'Arch demande de lire ou de faire à la main, montré au bon moment :
# news avant la mise à jour, .pacnew, redémarrage et firmwares après. Lancé comme script
# (maintenance.py remind <user>), c'est le rappel hebdomadaire d'update-reminder.timer.
import datetime
import email.utils
import html
import json
import os
import pwd
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

import decman
from decman import File, Module, prg
from decman.core import output
from decman.plugins import pacman, systemd

NEWS_URL = "https://archlinux.org/feeds/news/"
INSTALLED_SCRIPT = "/usr/local/lib/arch-maintenance/maintenance.py"
STORE_FILE = "/var/lib/decman/store.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def pending_upgrades() -> set[str]:
    # checkupdates synchronise sa propre base : pas de mise à jour partielle. Code 2 : rien à faire.
    return {line.split()[0] for line in run(["checkupdates", "--nocolor"]).stdout.splitlines()}


def fetch_news() -> list[ET.Element]:
    with urllib.request.urlopen(NEWS_URL, timeout=15) as resp:
        return ET.fromstring(resp.read()).findall("channel/item")


def unread_news(items: list[ET.Element], seen: str | None) -> list[ET.Element]:
    # Premier passage : les news des 30 derniers jours.
    now = datetime.datetime.now(datetime.UTC)
    since = datetime.datetime.fromisoformat(seen or (now - datetime.timedelta(days=30)).isoformat())
    return [i for i in items if email.utils.parsedate_to_datetime(i.findtext("pubDate")) > since]


def news_text(description: str) -> str:
    text = re.sub(r"<(br|/p|/li|/pre)[^>]*>", "\n", description)
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


class Maintenance(Module):
    def __init__(self, user: str) -> None:
        super().__init__("maintenance")
        self.user = user

    @pacman.packages
    def pacman_packages(self) -> set[str]:
        return {"libnotify"}  # notify-send ; checkupdates et pacdiff viennent de pacman-contrib (base.py)

    @systemd.units
    def units(self) -> set[str]:
        return {"update-reminder.timer"}

    def files(self) -> dict[str, File]:
        return {
            INSTALLED_SCRIPT: File(source_file="./maintenance.py"),
            "/etc/systemd/system/update-reminder.service": File(content=(
                "[Unit]\nDescription=Weekly reminder of pending updates and Arch news\n"
                "Wants=network-online.target\nAfter=network-online.target\n\n"
                f"[Service]\nType=oneshot\nExecStart=/usr/bin/python3 {INSTALLED_SCRIPT} remind {self.user}\n"
            )),
            # Pas plus d'une fois par semaine.
            "/etc/systemd/system/update-reminder.timer": File(content=(
                "[Unit]\nDescription=Weekly reminder of pending updates and Arch news\n\n"
                "[Timer]\nOnCalendar=weekly\nRandomizedDelaySec=1h\nPersistent=true\n\n"
                "[Install]\nWantedBy=timers.target\n"
            )),
        }

    # Les news non lues, avec les paquets installés qu'elles nomment, et une confirmation avant de
    # mettre à jour. Elles ne sont marquées lues qu'une fois confirmées.
    def before_update(self, store) -> None:
        try:
            unread = unread_news(fetch_news(), store.get("news_seen"))
        except (OSError, ET.ParseError) as error:
            output.print_warning(f"News Arch illisibles ({error}) : les lire sur {NEWS_URL}")
            return
        if not unread:
            return

        installed = set(run(["pacman", "-Qq"]).stdout.split())
        pending = pending_upgrades()
        for item in reversed(unread):
            title = item.findtext("title")
            # ponytail: paquets repérés par leur nom dans le titre ; une news qui n'en cite aucun
            # peut quand même concerner la machine, d'où la confirmation pour toutes.
            named = installed & set(re.findall(r"[a-z0-9][a-z0-9+._-]*", title.lower()))
            date = email.utils.parsedate_to_datetime(item.findtext("pubDate")).date()
            output.print_summary(f"News Arch du {date:%d/%m/%Y} : {title}")
            if named:
                marks = [f"{p} (mise à jour en attente)" if p in pending else p for p in sorted(named)]
                output.print_warning(f"Installé ici : {', '.join(marks)}")
            print(news_text(item.findtext("description")))
            print(item.findtext("link"), end="\n\n")
        if not output.prompt_confirm("News lues, continuer la mise à jour ?", default=False):
            raise SystemExit("Mise à jour annulée : les news restent non lues.")
        store["news_seen"] = datetime.datetime.now(datetime.UTC).isoformat()

    # decman active le timer sans le démarrer : sans ça, il attendrait le prochain démarrage.
    def on_change(self, store) -> None:
        prg(["systemctl", "start", "update-reminder.timer"])

    def after_update(self, store) -> None:
        self.report_pacnew()
        self.report_reboot()
        self.report_firmware()

    # Un .pacnew d'un fichier que decman écrit n'est pas à fusionner sur place (decman l'écraserait) :
    # ce qui sert va dans le dépôt, puis le .pacnew se supprime.
    def report_pacnew(self) -> None:
        managed = {path for module in decman.modules for path in module.files()}
        for path in run(["pacdiff", "--output"]).stdout.split():
            target = re.sub(r"\.pac(new|save)$", "", path)
            if target == "/etc/pacman.d/mirrorlist":  # réécrit par reflector (base.py)
                os.remove(path)
                continue
            if target in managed:
                output.print_warning(f"{path} : fichier géré par decman, reporter les changements "
                                     f"utiles dans le dépôt, puis : sudo rm {path}")
            else:
                output.print_warning(f"{path} : à fusionner avec sudo pacdiff")
            print(run(["diff", "-u", target, path]).stdout)

    def report_reboot(self) -> None:
        # ponytail: seul le paquet linux est comparé, le seul noyau déclaré (base.py). kernel-modules-hook
        # garde les modules du noyau en cours : leur présence ne dit rien.
        running = os.uname().release.replace("-", ".", 1)  # 7.2.11-arch1-1 → 7.2.11.arch1-1
        installed = run(["pacman", "-Q", "linux"]).stdout.split()[1]
        if installed != running:
            output.print_warning(f"Noyau {installed} installé, {running} en cours : redémarrer.")

    def report_firmware(self) -> None:
        # Métadonnées tenues à jour par fwupd-refresh.timer. Code 2 : rien à faire.
        res = run(["fwupdmgr", "get-updates", "--no-unreported-check", "--no-metadata-check"])
        if res.returncode == 0:
            output.print_warning("Firmwares à mettre à jour (fwupdmgr update) :")
            print(res.stdout)


# Rappel hebdomadaire : une notification dans la session de user s'il y a des mises à jour ou des
# news non lues, rien sinon. Le noyau est signalé : il demande un redémarrage.
def remind(user: str) -> None:
    pending = pending_upgrades()
    with open(STORE_FILE, encoding="utf-8") as f:
        seen = json.load(f).get("news_seen")
    try:
        news = len(unread_news(fetch_news(), seen))
    except (OSError, ET.ParseError):
        news = 0
    parts = []
    if pending:
        parts.append(f"{len(pending)} paquet(s) à mettre à jour" + (", dont le noyau" if "linux" in pending else ""))
    if news:
        parts.append(f"{news} news Arch non lue(s)")
    uid = pwd.getpwnam(user).pw_uid
    bus = f"/run/user/{uid}/bus"
    if not parts or not os.path.exists(bus):  # pas de session ouverte : la semaine prochaine
        return
    subprocess.run(["runuser", "-u", user, "--", "env", f"DBUS_SESSION_BUS_ADDRESS=unix:path={bus}",
                    "notify-send", "--app-name=Mises à jour", "--icon=system-software-update",
                    "Mises à jour Arch", " ; ".join(parts) + ". Lancer sudo decman."], check=True)


if __name__ == "__main__" and sys.argv[1:2] == ["remind"]:
    remind(sys.argv[2])
