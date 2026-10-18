"""Export the site's data from the private corpus workspace.

Reads the phase 1-2 outputs (re-scored citations, novelty, themes) plus the
Treatise text and bibliography, and writes only derived data into
site/src/data/: citation locations, scores, short citing snippets (the
~120-character context the detector kept) and bibliographic records. No
paper full text leaves the corpus workspace.

    python pipeline/build_data.py \
        --lab ~/Single-File-Processing-for-Hume-Project/modernization_lab \
        --treatise "~/Single-File-Processing-for-Hume-Project/data/Full Treatise in HTML.txt" \
        --runtime ~/Hume-on-Personal-Identity/data/runtime
"""
import argparse
import csv
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site" / "src" / "data"

THEMES = [
    {"id": "t0", "name": "Self and the passions"},
    {"id": "t1", "name": "Causation and the Appendix problem"},
    {"id": "t2", "name": "Body and the external world"},
    {"id": "t3", "name": "Immateriality of the soul"},
]

BOOKS = {"0": "Introduction", "1": "Book 1: Of the Understanding",
         "2": "Book 2: Of the Passions", "3": "Book 3: Of Morals",
         "App": "Appendix", "Abs": "Abstract"}

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
         "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13,
         "XIV": 14, "XV": 15, "XVI": 16}

FOCUS_MIN, SURPRISE_MIN = 0.40, 4.4  # phase 2 thresholds for "focused" / "surprising"


def flatten(d, prefix=""):
    """treatise_structure_dict.json -> ordered Norton ids."""
    if isinstance(d, list):
        sep = "" if prefix == "Abs" else "."  # 2020 ids: App.20 but Abs20
        return [f"{prefix}{sep}{p}" if prefix else p for p in d]
    out = []
    for k, v in d.items():
        out += flatten(v, f"{prefix}.{k}" if prefix else k)
    return out


def section_of(pid):
    if pid.startswith(("App", "Abs")):
        return pid[:3]
    parts = pid.split(".")
    return parts[0] if parts[0] == "0" else ".".join(parts[:3])


def book_of(pid):
    return pid[:3] if pid.startswith(("App", "Abs")) else pid.split(".")[0]


def parse_treatise(path):
    """Paragraph text and section/part titles from the Hume Texts Online dump."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    marker = re.compile(r"^T ((?:\d+\.)*\d+(?:n\d+)?|App\.\d+(?:n\d+)?), SBN (\S+)")
    text, sbn, titles = {}, {}, {}
    pending_part = pending_sect = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^PART [IVX]+\.?$", line):
            pending_part = lines[i + 1].strip()
        elif re.match(r"^SECT\. [IVX]+\.?$", line):
            pending_sect = lines[i + 1].strip()
        m = marker.match(line)
        if m:
            pid, page = m.group(1), m.group(2)
            body = []
            j = i + 1
            if "n" in pid.split(".")[-1]:
                j += 1  # footnote number line
            while j < len(lines) and lines[j].strip() and not marker.match(lines[j].strip()):
                body.append(lines[j].strip())
                j += 1
            text[pid] = " ".join(body)
            sbn[pid] = page
            sec = section_of(pid)
            if pending_sect and pid.endswith(".1") and sec not in titles:
                titles[sec] = pending_sect.rstrip(".")
                pending_sect = None
            if pending_part and pid.endswith(".1.1"):
                titles[".".join(pid.split(".")[:2])] = pending_part.rstrip(".")
                pending_part = None
            i = j
            continue
        i += 1
    return text, sbn, titles


def clean(s):
    """Tidy bibliography strings exported from BibTeX."""
    return re.sub(r"\\textquoteright", "’", s).strip()


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", required=True)
    ap.add_argument("--treatise", required=True)
    ap.add_argument("--runtime", required=True)
    a = ap.parse_args()
    lab, runtime = Path(os.path.expanduser(a.lab)), Path(os.path.expanduser(a.runtime))
    OUT.mkdir(parents=True, exist_ok=True)

    order = flatten(json.loads((runtime / "treatise_structure_dict.json").read_text()))
    text, sbn, titles = parse_treatise(os.path.expanduser(a.treatise))
    n2s = {}
    for line in (runtime / "Norton to SBN Dictionary.txt").read_text().splitlines():
        if " : " in line:
            k, v = line.split(" : ", 1)
            n2s[k.strip()] = v.strip()

    # Bibliography
    works = {r["Filename"].rsplit(".", 1)[0]: r for r in read_csv(runtime / "List-of-Works.csv")}
    novelty = {r[""]: r for r in read_csv(lab / "phase2_papers.csv")}
    themes = {r[""]: r for r in read_csv(lab / "phase2_themes_noncore_k4.csv")}
    rare = read_csv(lab / "phase2_passages.csv")
    meta = json.loads((lab / "phase2_meta.json").read_text())
    core = set(meta["core"])

    papers, citations = [], {}
    para_w = defaultdict(float)
    para_citers = defaultdict(dict)
    for pid in sorted(works):
        d = json.loads((lab / "rescored" / f"{pid}.json").read_text())
        w = works[pid]
        weights = {k: v for k, v in d["paragraph_weights"].items() if v > 0}
        for k, v in weights.items():
            para_w[k] += v
            para_citers[k][pid] = round(v, 3)
        by_source = defaultdict(int)
        cites = []
        for c in d["cites"]:
            by_source[c["source"]] += 1
            cites.append({
                "text": c["text"], "kind": c["kind"], "source": c["source"],
                "context": c["context"],
                "paras": list(c["weights"].keys()),
                "precise": max(c["weights"].values(), default=0) >= 0.3,
            })
        citations[pid] = cites
        nv = novelty.get(pid)
        th = themes.get(pid)
        papers.append({
            "id": pid,
            "author": w["Author"].strip(),
            "title": clean(w["Title of Work"]),
            "year": int(w["Year"]) if w["Year"].strip().isdigit() else None,
            "venue": (w["Journal"] or w["Book Title"]).strip(),
            "volume": w["Volume"].strip(), "issue": w["Issue"].strip(),
            "pages": w["Pages"].strip().replace("--", "–"),
            "editor": re.sub(r"\s{2,}", "; ", w["Editor"].strip()),
            "cites": len(d["cites"]),
            "sources": dict(by_source),
            "weights": {k: round(v, 3) for k, v in weights.items()},
            "focus": float(nv["focus"]) if nv else None,
            "surprise": float(nv["surprise"]) if nv else None,
            "topRare": [s.strip() for s in nv["top_rare"].split(",")] if nv and nv["top_rare"] else [],
            "themes": [float(th[t["id"]]) for t in THEMES] if th else None,
        })

    # Nearest neighbours: cosine on section-level profiles, papers with 10+ cites
    def sect_profile(p):
        prof = defaultdict(float)
        for k, v in p["weights"].items():
            prof[section_of(k)] += v
        n = math.sqrt(sum(v * v for v in prof.values())) or 1
        return {k: v / n for k, v in prof.items()}
    profs = {p["id"]: sect_profile(p) for p in papers if p["cites"] >= 10}
    for p in papers:
        if p["id"] not in profs:
            p["neighbours"] = []
            continue
        a = profs[p["id"]]
        sims = [(q, sum(a.get(k, 0) * v for k, v in b.items())) for q, b in profs.items() if q != p["id"]]
        p["neighbours"] = [{"id": q, "sim": round(s, 3)} for q, s in sorted(sims, key=lambda x: -x[1])[:5]]

    rare_by = {r["passage"]: r for r in rare}
    paragraphs = []
    for pid in order:
        citers = para_citers.get(pid, {})
        sec = section_of(pid)
        paragraphs.append({
            "id": pid, "book": book_of(pid), "section": sec,
            "sbn": sbn.get(pid) or n2s.get(pid, ""),
            "w": round(para_w.get(pid, 0), 3),
            "n": len(citers),
            "core": pid in core,
            "rare": pid in rare_by,
        })
    ids = set(order)
    unknown = [k for k in para_w if k not in ids]
    if unknown:
        print("weights on paragraphs outside the structure:", unknown[:10])

    passages = {}
    for p in paragraphs:
        pid = p["id"]
        r = rare_by.get(pid)
        passages[pid] = {
            "text": text.get(pid, ""),
            "citers": sorted(para_citers.get(pid, {}).items(), key=lambda x: -x[1]),
            "rareScore": float(r["score"]) if r else None,
            "rareN": int(r["n_papers"]) if r else None,  # papers citing it precisely
            "focusedCiters": [s.strip() for s in r["focused_citers"].split(",")] if r and r["focused_citers"] else [],
        }

    sections = []
    seen = set()
    for p in paragraphs:
        s = p["section"]
        if s in seen:
            continue
        seen.add(s)
        part = ".".join(s.split(".")[:2]) if s[0].isdigit() and s != "0" else None
        sections.append({"id": s, "book": p["book"], "title": titles.get(s, BOOKS.get(s, "")),
                         "part": part, "partTitle": titles.get(part, "") if part else ""})

    def dump(name, obj):
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    dump("paragraphs.json", paragraphs)
    dump("sections.json", sections)
    dump("passages.json", passages)
    dump("papers.json", papers)
    dump("citations.json", citations)
    dump("meta.json", {
        "themes": THEMES, "books": BOOKS, "core": sorted(core, key=order.index),
        "focusMin": FOCUS_MIN, "surpriseMin": SURPRISE_MIN,
        "totals": {"papers": len(papers), "cites": sum(p["cites"] for p in papers),
                   "paragraphs": len(paragraphs),
                   "cited": sum(1 for p in paragraphs if p["n"]),
                   "scored": sum(1 for p in papers if p["focus"] is not None)},
    })

    # sanity: theme names vs. their heaviest sections
    for i, t in enumerate(THEMES):
        prof = defaultdict(float)
        for p in papers:
            if p["themes"]:
                for k, v in sect_profile(p).items():
                    prof[k] += v * p["themes"][i]
        top = [k for k, _ in sorted(prof.items(), key=lambda x: -x[1]) if k not in ("1.4.6", "App")][:4]
        print(t["id"], t["name"], top)
    print("paragraphs", len(paragraphs), "with text", sum(1 for p in paragraphs if passages[p["id"]]["text"]),
          "titled sections", sum(1 for s in sections if s["title"]), "/", len(sections))


if __name__ == "__main__":
    main()
