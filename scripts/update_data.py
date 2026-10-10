#!/usr/bin/env python3
"""Обновляет data.json Demonhub живыми данными demonlist.org + AREDL.
Запускается локально и из GitHub Action (ежедневно). Формат снимка —
кортежи в точности как в оригинальном SNAPSHOT (см. fromSnap в index.html)."""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

DL = "https://api.demonlist.org/level/classic/list?limit=100&offset=%d"
AREDL = "https://api.aredl.net/v2/api/aredl/levels"
UA = {"User-Agent": "demonhub-data-updater/1.0"}
# data.json всегда лежит в корне репозитория (на уровень выше scripts/)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")


def get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                raise
            print("  retry %d (%s)" % (i + 1, e))
            time.sleep(5 * (i + 1))


def fetch_levels():
    levels, offset = [], 0
    while True:
        d = get_json(DL % offset)
        batch = d["data"]["levels"]
        levels.extend(batch)
        print("  demonlist: +%d (всего %d)" % (len(batch), len(levels)))
        if len(batch) < 100:
            break
        offset += 100
        time.sleep(0.4)
    return levels


def to_tuple(x):
    v = x.get("verifier") or {}
    return [x["id"], x["ingame_id"], x["placement"], x["name"], x["points"],
            x["list_percent"], x["length"], x["holder"], v.get("username"),
            x["verification_url"], x["date_created"]]


def main():
    levels = fetch_levels()
    aredl = get_json(AREDL)
    aredl_obj = {}
    for x in aredl:
        aredl_obj[str(x["level_id"])] = [x["position"], None, x.get("gddl_tier"), x.get("tags")]
    print("aredl: %d записей" % len(aredl_obj))

    data = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "snapshot": [to_tuple(x) for x in levels],
        "aredl": aredl_obj,
    }
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    path = OUT
    old = None
    try:
        old = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        pass
    if old == out:
        print("изменений нет, data.json не тронут")
        return
    open(path, "w", encoding="utf-8", newline="\n").write(out)
    print("data.json обновлён: %d уровней, %d KB" % (len(data["snapshot"]), len(out) // 1024))


if __name__ == "__main__":
    main()
