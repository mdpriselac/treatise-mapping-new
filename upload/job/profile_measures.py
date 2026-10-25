"""Profile measures for one paper, against the corpus reference: focus, breadth-adjusted
surprise, theme mix and nearest corpus papers. Shared by the parse job and the API (which
re-scores when an uploader unticks a citation). Needs only numpy, scipy and reference.json."""
import collections
import json
import math
import os
import re

import numpy as np
from scipy.optimize import nnls

HERE = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.environ.get("TM_REFERENCE", os.path.join(HERE, "reference"))
REF = json.load(open(os.path.join(REF_DIR, "reference.json")))


def _chapter(p):
    return re.match(r"(App\.|Abs|\d+\.\d+\.\d+|0)", p).group(1).rstrip(".")


def build_profile(cites: list) -> dict:
    weights = collections.Counter()
    for c in cites:
        weights.update(c["weights"])
    n = len(cites)
    total = sum(weights.values())
    prof = {"cites": n, "weights": {k: round(v, 4) for k, v in weights.items()},
            "sources": dict(collections.Counter(c["source"] for c in cites)),
            "focus": None, "surprise": None, "rare": [], "themes": None, "nearest": []}
    if not total:
        return prof
    share = {k: v / total for k, v in weights.items()}
    prof["focus"] = round(sum(share.get(p, 0) for p in REF["core"]), 3)
    # breadth-adjusted surprise: how unlikely a paper citing this much was to cite p precisely
    surprise = {}
    for p, w in weights.items():
        if w >= 0.3:
            r = REF["rates"].get(p, REF["default_rate"])
            surprise[p] = -math.log(1 - (1 - r) ** n)
    if surprise:
        top = sorted(surprise.items(), key=lambda kv: -kv[1])
        prof["surprise"] = round(top[0][1], 2)
        prof["rare"] = [{"paragraph": p, "surprise": round(s, 2)} for p, s in top[:5] if s > math.log(20)]
    # chapter profile, themes (core set aside, as in the corpus fit) and nearest corpus papers
    chapters = collections.Counter()
    for p, v in share.items():
        chapters[_chapter(p)] += v
    tm = REF["themes"]
    x = np.array([chapters.get(c, 0) for c in tm["chapters"]])
    if x.sum() > 0:
        H = np.array([tm["components"][t] for t in tm["components"]])
        w, _ = nnls(H.T, x / x.sum())
        if w.sum() > 0:
            prof["themes"] = {t: round(float(v), 3) for t, v in zip(tm["components"], w / w.sum())}
    keys = sorted(set(chapters) | {c for pp in REF["papers"].values() for c in pp["chapters"]})
    me = np.array([chapters.get(k, 0) for k in keys])
    sims = []
    for pid, pp in REF["papers"].items():
        v = np.array([pp["chapters"].get(k, 0) for k in keys])
        sims.append((float(me @ v / (np.linalg.norm(me) * np.linalg.norm(v) or 1)), pid))
    prof["nearest"] = [{"id": pid, "similarity": round(s, 3), "title": REF["papers"][pid]["title"],
                        "author": REF["papers"][pid]["author"], "year": REF["papers"][pid]["year"]}
                       for s, pid in sorted(sims, reverse=True)[:5]]
    prof["focused"] = prof["focus"] >= REF["focus_min"]
    prof["surprising"] = (prof["surprise"] or 0) >= REF["surprise_min"]
    return prof
