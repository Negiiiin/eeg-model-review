#!/usr/bin/env python3
"""
make_signals_manifest.py — write the manifest that turns the 25 stage-2 examples into
signals.json for the review page (EEG-trace view), with windows matching the videos.

    python make_signals_manifest.py --examples index.html \
        --root /data/tuh/tuab --root /data/tuh/tusz --root /data/tuh/tuep \
        --root /data/tuh/tuev --root /data/tuh/tusl --root /data/eegmat \
        --out signals_manifest.csv
    python make_recordings.py build --manifest signals_manifest.csv --out signals.json
    # put signals.json next to index.html and push

The EDF for each example is found by basename under the given roots
(tuab_aaaaaama_s002_t000 -> aaaaaama_s002_t000.edf, tuev_..._e0020 -> aaaaadud_00000001.edf,
eegmat_Subject18_1_w007 -> Subject18_1.edf). Examples whose EDF is not found are listed and
left out; the page shows a placeholder for them.
"""
import argparse, csv, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument("--examples", required=True, help="index.html (examples embedded) or a JSON with {examples:[...]}")
ap.add_argument("--root", action="append", default=[], help="directory to search for EDFs (repeatable)")
ap.add_argument("--out", default="signals_manifest.csv")
a = ap.parse_args()

txt = open(a.examples, encoding="utf-8").read()
if txt.lstrip().startswith("<"):
    i = txt.index("const DATA = ") + len("const DATA = "); j = txt.index(";\n", i)
    txt = txt[i:j]
examples = json.loads(txt)["examples"]

DS = {"tuab": "TUAB", "tusz": "TUSZ", "tuep": "TUEP", "tuev_events": "TUEV", "hmc": "HMC",
      "eegmat": "EEGMAT", "tusl_events": "TUSL"}


def edf_basename(ex_id):
    s = re.sub(r"^(tuab|tusz|tuep|tuev|hmc|eegmat|tusl)_", "", ex_id)
    s = re.sub(r"_e\d{4}$", "", s)          # TUEV / TUSL event suffix
    s = re.sub(r"_w\d{3}$", "", s)          # EEGMAT window suffix
    return s + ".edf"


index = {}
for root in a.root:
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".edf"):
                index.setdefault(fn, os.path.join(dp, fn))

rows, missing = [], []
for e in examples:
    fn = edf_basename(e["id"])
    path = index.get(fn)
    if not path:
        missing.append((e["id"], fn)); continue
    t0, t1 = e["span_s"]
    rows.append({
        "id": e["id"], "dataset": DS.get(e["corpus"], e["corpus"].upper()), "edf_path": path,
        "start_s": t0, "stop_s": t1,
        "true_label": e["options"].get(e["gold"], e["gold"]), "label_scope": "recording",
        "true_label_source": "stage-2 gold", "question": e["question"],
        "display_label": f"{e['n']:02d} · {e['id']}", "note": f"window {t0:.0f}–{t1:.0f} s of the recording (same span as the video)",
        "gt_intervals": json.dumps([]),
    })

with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} of {len(examples)} examples matched -> {a.out}")
for i, fn in missing:
    print(f"  not found: {i}  ({fn})")
