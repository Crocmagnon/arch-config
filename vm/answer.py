#!/usr/bin/env python3
# VM de test seulement : lance une commande interactive (decman, qui laisse pacman poser ses
# questions) dans un pseudo-terminal et répond à la place du clavier :
#   - « Review PKGBUILD … ? » de decman : n (la relecture ouvre un pager, qui bloquerait)
#   - autres confirmations « [Y/n] », « (y/N) », etc. : y
#   - choix numérotés de pacman (« Enter a number », « Enter a selection ») : Entrée, le défaut
# La sortie est recopiée telle quelle sur stdout.
#   answer.py decman --no-color
# ponytail: détection par expressions régulières sur la fin de la sortie ; un prompt d'un autre
# format bloque, et le timeout de l'appelant l'arrête.
import os
import pty
import re
import sys

CONFIRM = re.compile(rb"[\[(][Yy]/[Nn][\])]")
REVIEW = re.compile(rb"Review PKGBUILD[^\n]*\?\s*$")
# Des séquences ANSI suivent parfois le « : » final (couleur, ou ESC[?25h qui réaffiche le curseur).
SELECT = re.compile(rb"Enter a (number|selection)[^\n]*:(\s|\x1b\[[0-9;?]*[A-Za-z])*$")

pid, fd = pty.fork()
if pid == 0:
    os.execvp(sys.argv[1], sys.argv[1:])

tail = b""
while True:
    try:
        chunk = os.read(fd, 4096)
    except OSError:  # EIO : le processus fils a fermé le terminal
        break
    if not chunk:
        break
    sys.stdout.buffer.write(chunk)
    sys.stdout.buffer.flush()
    tail = (tail + chunk)[-300:]
    if REVIEW.search(tail):
        os.write(fd, b"n\n")
        tail = b""
    elif CONFIRM.search(tail):
        os.write(fd, b"y\n")
        tail = b""
    elif SELECT.search(tail):
        os.write(fd, b"\n")
        tail = b""

sys.exit(os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]))
