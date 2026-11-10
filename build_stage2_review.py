#!/usr/bin/env python3
"""
build_stage2_review.py — stage2_traces/ -> a GitHub-Pages-ready site:
  site/index.html      (examples embedded)
  site/media/NN.mp4    (videos re-encoded to H.264 so browsers can play them)

    python build_stage2_review.py --src stage2_traces --template review_template.html --out site
"""
import argparse, csv, json, os, re, shutil, subprocess

CORPUS = {
    "tuab": ("TUAB", "TUAB — Normal vs. abnormal"),
    "tusz": ("TUSZ", "TUSZ — Seizure detection"),
    "tuep": ("TUEP", "TUEP — EEG evidence supporting epilepsy"),
    "tuev_events": ("TUEV", "TUEV — Event classification"),
    "hmc": ("HMC", "HMC — Sleep staging"),
    "eegmat": ("EEGMAT", "EEGMAT — Rest vs. mental arithmetic"),
    "tusl_events": ("TUSL", "TUSL — Normal background vs. slowing vs. seizure"),
}
FRAME_S = 10.0


def parse_question(q):
    """full prompt -> (preamble, question line, {letter: text})"""
    lines = [l.rstrip() for l in q.strip().split("\n")]
    opts, question, pre = {}, None, []
    i_opt = next((i for i, l in enumerate(lines) if l.strip().lower() == "options:"), None)
    if i_opt is not None:
        for l in lines[i_opt + 1:]:
            m = re.match(r"^\s*([A-Z])\.\s*(.+)$", l)
            if m: opts[m.group(1)] = m.group(2).strip()
            elif l.strip(): break
        qs = [l for l in lines[:i_opt] if l.strip()]
        question = qs[-1] if qs else ""
        pre = qs[:-1]
    return "\n".join(pre).strip(), question, opts


def parse_trace(ans):
    m = re.search(r"<answer>\s*([A-Z])\s*</answer>", ans)
    letter = m.group(1) if m else None
    t = re.sub(r"</?think>", "", ans)
    t = re.sub(r"<answer>[\s\S]*?</answer>", "", t).strip()
    return t, letter


def span_from_frames(folder):
    fr = sorted(f for f in os.listdir(os.path.join(folder, "frames")) if f.endswith("s.png"))
    starts = [float(f[:-5]) for f in fr]
    return (starts[0], starts[-1] + FRAME_S, len(starts)) if starts else (0.0, 0.0, 0)


def reencode(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-g", "1", "-crf", "23", "-movflags", "+faststart", dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", default="site")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "media"), exist_ok=True)

    index = {r["folder"]: r for r in csv.DictReader(open(os.path.join(a.src, "INDEX.csv")))}
    examples = []
    for folder in sorted(index):
        d = os.path.join(a.src, folder)
        row = json.load(open(os.path.join(d, "row.json")))
        n = int(index[folder]["n"])
        pre, question, opts = parse_question(row["question"])
        trace, letter = parse_trace(row["answer"])
        t0, t1, nfr = span_from_frames(d)
        sp = index[folder].get("span_s", "")
        if "-" in sp:                                    # INDEX keeps the exact decimals
            t0, t1 = (float(x) for x in sp.split("-"))
        code, title = CORPUS.get(row["corpus"], (row["corpus"].upper(), row["corpus"]))
        vid = f"media/{n:02d}.mp4"
        reencode(os.path.join(d, "video.mp4"), os.path.join(a.out, vid))
        examples.append({
            "n": n, "id": row["report_id"], "corpus": row["corpus"], "corpus_code": code, "corpus_title": title,
            "task": index[folder]["task"], "question": question, "prompt_preamble": pre, "options": opts,
            "gold": row["gold"], "trace": trace, "trace_answer": letter,
            "frames": nfr, "span_s": [t0, t1], "frame_s": FRAME_S, "video": vid,
            "annotation": row.get("annotation") or {},
        })
        print(f"{n:02d} {code:7s} gold {row['gold']} frames {nfr:3d} span {t0:.0f}-{t1:.0f}s  {vid}")

    tpl = open(a.template, encoding="utf-8").read()
    assert tpl.count("__EXAMPLES__") == 1
    meta = {"title": "Stage-2 training traces — expert review", "examples": examples}
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(
        tpl.replace("__EXAMPLES__", json.dumps(meta, ensure_ascii=False)))
    open(os.path.join(a.out, ".nojekyll"), "w").close()
    mb = sum(os.path.getsize(os.path.join(a.out, "media", f)) for f in os.listdir(os.path.join(a.out, "media"))) / 1e6
    print(f"\n{a.out}/index.html + {len(examples)} videos ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
