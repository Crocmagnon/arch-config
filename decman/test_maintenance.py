# Auto-test de maintenance.py, hors ligne (flux de news factice) : python3 decman/test_maintenance.py
import io, sys, datetime, email.utils
sys.path.insert(0, __import__("os").path.dirname(__file__))
import maintenance as m

now = datetime.datetime.now(datetime.UTC)
def item(days, title, desc):
    d = email.utils.format_datetime(now - datetime.timedelta(days=days))
    return f"<item><title>{title}</title><link>https://archlinux.org/news/x/</link><description>{desc}</description><pubDate>{d}</pubDate></item>"
FEED = f"<rss><channel>{item(2, 'linux-firmware &gt;= 2026 requires manual intervention', '&lt;p&gt;Run &lt;code&gt;pacman -Syu --overwrite&lt;/code&gt;&lt;/p&gt;')}{item(60, 'Old news', 'old')}</channel></rss>"

class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass
m.urllib.request.urlopen = lambda *a, **k: Resp(FEED.encode())
m.pending_upgrades = lambda: {"linux-firmware"}
answers = iter(["n", "y"])
m.output.input = lambda prompt: (print(prompt), next(answers))[1]

store = {}
mod = m.Maintenance()
try:
    mod.before_update(store); raise AssertionError("aurait dû s'arrêter")
except SystemExit as e:
    print("refus ->", e)
assert "news_seen" not in store
mod.before_update(store)
assert "news_seen" in store
out = io.StringIO(); sys.stdout, real = out, sys.stdout
mod.before_update(store)  # tout est lu : rien à afficher
sys.stdout = real
assert "News" not in out.getvalue(), out.getvalue()
mod.after_update(store)
print("OK")
