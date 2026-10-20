# Ce qu'une mise à jour d'Arch demande de lire ou de faire à la main, montré au bon moment :
# news avant la mise à jour, .pacnew, redémarrage et firmwares après.
import datetime
import email.utils
import html
import os
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

import decman
from decman import Module
from decman.core import output

NEWS_URL = "https://archlinux.org/feeds/news/"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def pending_upgrades() -> set[str]:
    # checkupdates synchronise sa propre base : pas de mise à jour partielle. Code 2 : rien à faire.
    return {line.split()[0] for line in run(["checkupdates", "--nocolor"]).stdout.splitlines()}


def news_text(description: str) -> str:
    text = re.sub(r"<(br|/p|/li|/pre)[^>]*>", "\n", description)
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


class Maintenance(Module):
    def __init__(self) -> None:
        super().__init__("maintenance")

    # Les news non lues, avec les paquets installés qu'elles nomment, et une confirmation avant de
    # mettre à jour. Elles ne sont marquées lues qu'une fois confirmées.
    def before_update(self, store) -> None:
        try:
            with urllib.request.urlopen(NEWS_URL, timeout=15) as resp:
                items = ET.fromstring(resp.read()).findall("channel/item")
        except (OSError, ET.ParseError) as error:
            output.print_warning(f"News Arch illisibles ({error}) : les lire sur {NEWS_URL}")
            return
        # Premier passage : les news des 30 derniers jours.
        now = datetime.datetime.now(datetime.UTC)
        seen = datetime.datetime.fromisoformat(
            store.get("news_seen") or (now - datetime.timedelta(days=30)).isoformat()
        )
        unread = [i for i in items if email.utils.parsedate_to_datetime(i.findtext("pubDate")) > seen]
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
        store["news_seen"] = now.isoformat()

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
