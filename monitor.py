import json
import os
import urllib.request
import urllib.error
from pathlib import Path

PROGRESS_URL = "https://boykopovar.github.io/AnyPS5/progress.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
STATE_FILE = Path("state/stats.json")
STAT_KEYS = {"done", "total", "percent", "todo"}

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
        label = value.get("name")
        for key, child in value.items():
            if key in STAT_KEYS and isinstance(child, (int, float)) and not isinstance(child, bool):
                stats[f"{path}.{key}"] = child
            elif isinstance(child, (dict, list)):
                child_path = f"{path}.{key}"
                stats.update(extract_stats(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, dict):
                # Use stable names for groups instead of list indexes when possible.
                label = child.get("name")
                item_path = f"{path}[{label}]" if label else f"{path}[{index}]"
                stats.update(extract_stats(child, item_path))
            elif isinstance(child, list):
                stats.update(extract_stats(child, f"{path}[{index}]"))
    return stats

def fmt(value, key):
    if key.endswith(".percent"):
        return f"{value:g}%"
    return str(value)

def send_discord(changes):
    if not WEBHOOK_URL:
        raise RuntimeError("Le secret DISCORD_WEBHOOK_URL est absent.")
    lines = ["**AnyPS5 — progression mise à jour**", "[Ouvrir le suivi](https://boykopovar.github.io/AnyPS5/)"]
    for key, old, new in changes[:35]:
        label = key.replace("$.", "").replace(".libraries", " · Bibliothèques").replace(".shaders", " · Shaders")
        lines.append(f"• `{label}` : **{fmt(old, key)} → {fmt(new, key)}**")
    if len(changes) > 35:
        lines.append(f"… et {len(changes) - 35} autre(s) statistique(s) modifiée(s).")
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
    current = extract_stats(current_json)
    if not current:
        raise RuntimeError("Aucune statistique reconnue dans progress.json ; état non modifié.")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Initialisation terminée : {len(current)} statistiques enregistrées, aucune notification envoyée.")
        return

    previous = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    keys = sorted(set(previous) | set(current))
    changes = [(key, previous.get(key, "—"), current.get(key, "—"))
               for key in keys if previous.get(key) != current.get(key)]

    if not changes:
        print("Aucun changement de statistique.")
        return

    send_discord(changes)
    STATE_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(changes)} statistique(s) modifiée(s) ; notification Discord envoyée.")

if __name__ == "__main__":
    main()
