import json
import os
import urllib.request
import urllib.error
from pathlib import Path

PROGRESS_URL = "https://boykopovar.github.io/AnyPS5/progress.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
STATE_FILE = Path("state/stats.json")
STAT_KEYS = {"done", "total", "percent", "todo"}
IGNORED = ("libkernel",)  # toute clé contenant ce texte (insensible à la casse) est ignorée

def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AnyPS5-Progress-Monitor/1.0", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def extract_stats(value, path="$"):
    """Keep only numeric progress fields, not the long lists of function names."""
    stats = {}
    if isinstance(value, dict):
        for key, child in value.items():
            if key in STAT_KEYS and isinstance(child, (int, float)) and not isinstance(child, bool):
                stats[f"{path}.{key}"] = child
            elif isinstance(child, (dict, list)):
                stats.update(extract_stats(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, dict):
                label = child.get("name")
                item_path = f"{path}[{label}]" if label else f"{path}[{index}]"
                stats.update(extract_stats(child, item_path))
            elif isinstance(child, list):
                stats.update(extract_stats(child, f"{path}[{index}]"))
    return stats

def filter_ignored(stats):
    return {k: v for k, v in stats.items()
            if not any(word.lower() in k.lower() for word in IGNORED)}

def make_label(base):
    label = base.removeprefix("$").lstrip(".")
    return label.replace("libraries", "Bibliothèques").replace("shaders", "Shaders")

def progress_text(stats, base):
    done = stats.get(f"{base}.done")
    total = stats.get(f"{base}.total")
    if done is not None or total is not None:
        return f"{'—' if done is None else done}/{'—' if total is None else total}"
    percent = stats.get(f"{base}.percent")
    return "—" if percent is None else f"{percent:g}%"

def send_discord(previous, current, changed_bases):
    if not WEBHOOK_URL:
        raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est absent.")
    lines = ["**AnyPS5 — progression mise à jour**", "[Ouvrir le suivi](https://boykopovar.github.io/AnyPS5/)"]
    for base in changed_bases[:35]:
        old = progress_text(previous, base)
        new = progress_text(current, base)
        lines.append(f"• `{make_label(base)}` : **{old} → {new}**")
    if len(changed_bases) > 35:
        lines.append(f"… et {len(changed_bases) - 35} autre(s) catégorie(s) modifiée(s).")
    content = "\n".join(lines)
    # Discord's message content limit is 2000 characters.
    if len(content) > 1950:
        content = content[:1900] + "\n… (liste raccourcie)"
    payload = json.dumps({"content": content, "allowed_mentions": {"parse": []}}).encode("utf-8")
    request = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "AnyPS5-Progress-Monitor/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"Discord a répondu avec le code HTTP {response.status}")

def main():
    current_json = fetch_json(PROGRESS_URL)
    current = filter_ignored(extract_stats(current_json))
    if not current:
        raise RuntimeError("Aucune statistique reconnue dans progress.json ; état non modifié.")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Initialisation terminée : {len(current)} statistiques enregistrées, aucune notification envoyée.")
        return

    previous = filter_ignored(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    keys = sorted(set(previous) | set(current))
    changed_keys = [k for k in keys if previous.get(k) != current.get(k)]

    if not changed_keys:
        print("Aucun changement de statistique.")
        return

    # On regroupe par catégorie (tout ce qui précède le dernier ".done" / ".total" / ...)
    changed_bases = sorted({k.rpartition(".")[0] for k in changed_keys})

    send_discord(previous, current, changed_bases)
    STATE_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(changed_bases)} catégorie(s) modifiée(s) ; notification Discord envoyée.")

if __name__ == "__main__":
    main()
