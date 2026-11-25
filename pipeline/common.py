"""Shared paths and helpers for the Gothic Atlas data pipeline."""
import csv, os, pathlib, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")
csv.field_size_limit(10**9)

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Raw source files are large (about 1.8 GB), so they live outside the repo.
RAW = pathlib.Path(os.environ.get("GOTHIC_RAW") or pathlib.Path(os.environ.get("LOCALAPPDATA", ROOT)) / "gothic-atlas" / "raw")
CACHE = RAW.parent / "cache"
OUT = ROOT / "data"            # compiled, versioned outputs (committed)
USER_AGENT = "GothicAtlas/0.1 (https://gothic.onuralp.co)"

POP_BUCKET = "https://ministere-culture.s3.sbg.io.cloud.ovh.net/POP/"
POP_FILES = {"merimee.csv": "merimee.csv", "palissy.csv": "palissy.csv", "memoire.csv": "memoire_palissy_merimee.csv"}


def pop_rows(name):
    """Yield dict rows from a POP export (pipe-separated, quoted, UTF-8)."""
    with open(RAW / name, encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh, delimiter="|")


TYPES = [  # French denomination -> English type; first match wins, so order matters
    ("cathédrale", "cathedral"), ("collégiale", "collegiate church"), ("basilique", "basilica"),
    ("abbatiale", "abbey church"), ("abbaye", "abbey"), ("prieuré", "priory"), ("chartreuse", "charterhouse"),
    ("monastère", "monastery"), ("couvent", "convent"), ("commanderie", "commandery"), ("cloître", "cloister"),
    ("église", "church"), ("chapelle", "chapel"), ("oratoire", "oratory"),
]


def religious_type(row):
    """English type of a Mérimée row if it is a religious building we cover, else None."""
    if "religieuse" not in row["Domaine"]:
        return None
    den = row["Denomination_de_l_edifice"].lower()
    return next((en for fr, en in TYPES if fr in den), None)


def http(url, dest=None, accept="application/json", tries=5, wait=70):
    """GET with curl. Wikimedia throttles Python's own HTTP client hard, curl with a clear User-Agent is fine.
    Returns the body as bytes, or writes it to dest."""
    cmd = ["curl", "-sS", "--fail", "--location", "--max-time", "900", "-A", USER_AGENT, "-H", f"Accept: {accept}", url]
    for i in range(tries):
        r = subprocess.run(cmd + (["-o", str(dest)] if dest else []), capture_output=True)
        if r.returncode == 0:
            return r.stdout
        print(f"  retry {i + 1}: {r.stderr.decode(errors='replace').strip()[:160]}", flush=True)
        time.sleep(wait)
    raise SystemExit(f"could not fetch {url[:120]}")
