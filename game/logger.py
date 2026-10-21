"""logger.py: records one row per recorded round (practice rounds are never recorded).

On a computer the rows are appended to data/rounds.csv next to main.py.
In a browser (pygbag) files do not persist, so rows are kept in memory and printed to the browser console."""
import csv
import os
import sys
import json
import time

COLUMNS = ["participant", "build", "round", "order", "hudCondition", "map", "startedAt", "durationSec", "result", "lanternsFound",
           "lanternsTotal", "firstLanternSec", "distance", "pauses", "tilesVisited", "hits", "shadowCloseSec", "sprintSec", "exhaustions"]
WEB = sys.platform == "emscripten"


class Logger:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.rounds = []
        self.path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rounds.csv")

    def record(self, row):
        self.rounds.append(row)
        if not self.enabled:
            return
        if WEB:
            print("ROUND " + json.dumps(row))
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            new = not os.path.exists(self.path)
            with open(self.path, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                if new:
                    w.writeheader()
                w.writerow({c: row.get(c, "") for c in COLUMNS})
        except OSError as e:
            print("Could not write the data file:", e)
