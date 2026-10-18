#!/usr/bin/env python3
"""Generate the frozen, stratified efficiency corpus. Deterministic (seeded).

Strata (efficiency-plan §6): tabular/records + prose reports now;
text-PDF and scanned strata are deferred (importer stubs) — recorded as a
known limitation in FREEZE.md, not silently dropped.
"""
import csv, hashlib, json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "corpus"
SEED = 20261015

CATEGORIES = ["travel", "food", "tools", "other"]
VENDORS = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne", "Hooli", "Soylent"]

def make_csv(path, rows, rng):
    rng_i = random.Random(rng)  # per-file stream so file contents are independent of order
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "date", "amount", "category", "vendor"])
        for i in range(rows):
            w.writerow([
                f"r_{i:04d}",
                f"2026-{rng_i.randint(1,9):02d}-{rng_i.randint(1,28):02d}",
                round(rng_i.uniform(3, 900), 2),
                rng_i.choice(CATEGORIES),
                rng_i.choice(VENDORS),
            ])

TOPICS = ["quarterly expenses", "vendor consolidation", "travel policy", "tooling budget"]

def make_md(path, words, rng):
    rng_i = random.Random(rng)
    topic = path.stem.replace("_", " ")
    lines = [f"# Report: {topic.title()}", ""]
    n = 0
    while n < words:
        para = (
            f"In this section we discuss {topic}. "
            f"The observed value was {rng_i.uniform(1,100):.1f} compared to "
            f"{rng_i.uniform(1,100):.1f} in the prior period, a change of "
            f"{rng_i.uniform(-20,20):.1f} percent. "
            f"This reflects {rng_i.choice(TOPICS)} across {rng_i.randint(2,9)} units. "
        ) * 4
        lines += [para, ""]
        n += len(para.split())
    path.write_text("\n".join(lines))

def main():
    rng = SEED
    manifest = []
    specs = [
        ("tabular", "expenses_small.csv", 50), ("tabular", "expenses_medium.csv", 200),
        ("tabular", "expenses_large.csv", 800), ("tabular", "invoices_small.csv", 60),
        ("tabular", "invoices_medium.csv", 250), ("tabular", "invoices_large.csv", 900),
        ("prose", "report_quarterly.md", 800), ("prose", "report_vendor.md", 1500),
        ("prose", "report_travel.md", 2500), ("prose", "report_budget.md", 4000),
    ]
    for stratum, name, size in specs:
        d = OUT / stratum
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        if stratum == "tabular":
            make_csv(p, size, rng)
        else:
            make_md(p, size, rng)
        rng += 1
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.append({"stratum": stratum, "file": f"{stratum}/{name}",
                         "size_param": size, "bytes": p.stat().st_size, "sha256": h})
    (OUT / "manifest.json").write_text(json.dumps(
        {"seed": SEED, "frozen": "2026-10-15", "docs": manifest}, indent=2))
    print(f"corpus: {len(manifest)} docs -> {OUT}")

if __name__ == "__main__":
    sys.exit(main())
