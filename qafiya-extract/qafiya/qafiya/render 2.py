"""Deterministic deck/view renderer (spec §2 job 1): data + blocks + bindings -> an
interactive HTML deck where every value is clickable to its source span. No model, no token.
Print-to-PDF of the output gives the 'ppt'; the point is that each figure is bound."""
import os, json, html


def _prov_span(value, prov):
    data = html.escape(json.dumps(prov, ensure_ascii=False))
    return f'<span class="prov" data-prov="{data}">{html.escape(str(value))}</span>'


def render_deck(out_html: str, title: str, schema=None, records=None, blocks=None, bindings=None):
    slides = [f'<section class="slide"><h1>{html.escape(title)}</h1>'
              f'<p class="sub">Qāfiya deck — every value bound to its source. Click any figure.</p></section>']

    if schema and records:
        cols = list(schema["fields"].keys())
        head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
        body = ""
        for r in records:
            tds = ""
            for c in cols:
                prov = r.get("_prov", {}).get(c, {})
                tds += f"<td>{_prov_span(r.get(c), prov)}</td>"
            body += f"<tr>{tds}</tr>"
        slides.append(f'<section class="slide"><h2>Dataset: {html.escape(schema["dataset"])}</h2>'
                      f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></section>')

    if blocks:
        lis = "".join(f"<li>{_prov_span(b['content'], b['_prov'])}</li>" for b in blocks)
        slides.append(f'<section class="slide"><h2>Document blocks</h2><ul>{lis}</ul></section>')

    if bindings:
        rows = ""
        for b in bindings:
            state, detail = b.get("_status", ("?", ""))
            cls = {"PASS": "pass", "FAIL": "fail", "FLAG": "flag"}.get(state, "na")
            label = b.get("assertion", {}).get("statement") or b.get("derivation") or b["id"]
            ev = html.escape(json.dumps(b.get("sources", []), ensure_ascii=False))
            rows += (f'<div class="claim"><span class="badge {cls}">{state}</span>'
                     f' <b>{html.escape(str(label))}</b> <span class="detail">{html.escape(detail)}</span>'
                     f' <span class="prov ev" data-prov="{ev}">▸evidence</span></div>')
        slides.append(f'<section class="slide"><h2>Claims &amp; bindings</h2>{rows}</section>')

    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8><title>{html.escape(title)}</title><style>
body{{margin:0;background:#222;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif}}
.slide{{background:#fff;max-width:820px;margin:24px auto;padding:48px 56px;border-radius:8px;min-height:420px;box-shadow:0 4px 18px rgba(0,0,0,.3)}}
h1{{color:#1f3d63;font-size:34px}} h2{{color:#1f3d63;border-bottom:2px solid #e3ebf5;padding-bottom:6px}}
.sub{{color:#667}}
table{{border-collapse:collapse;width:100%;font-size:15px}} th,td{{border:1px solid #d7e0ec;padding:8px 10px;text-align:left}}
th{{background:#eaf1fb}} .prov{{cursor:pointer;border-bottom:1px dotted #2f5fa3}}
.prov:hover{{background:#fff6d6}} .badge{{padding:2px 8px;border-radius:10px;color:#fff;font-size:12px;font-weight:700}}
.pass{{background:#3f8f4f}} .fail{{background:#b23a52}} .flag{{background:#c47a24}} .na{{background:#888}}
.claim{{margin:10px 0;font-size:15px}} .detail{{color:#667;font-size:13px}} .ev{{color:#2f5fa3;font-size:13px}}
#panel{{position:fixed;right:16px;bottom:16px;max-width:360px;background:#0f2338;color:#e6edf5;padding:14px 16px;border-radius:8px;font:12px/1.5 ui-monospace,Menlo,monospace;white-space:pre-wrap;display:none;box-shadow:0 6px 20px rgba(0,0,0,.4)}}
@media print{{body{{background:#fff}}.slide{{box-shadow:none;margin:0;page-break-after:always;border-radius:0}}#panel{{display:none!important}}}}
</style></head><body>
{''.join(slides)}
<div id="panel"></div>
<script>
document.querySelectorAll('.prov').forEach(function(el){{el.addEventListener('click',function(){{
var p=document.getElementById('panel');p.textContent=JSON.stringify(JSON.parse(el.dataset.prov),null,2);p.style.display='block';}});}});
</script></body></html>"""
    os.makedirs(os.path.dirname(os.path.abspath(out_html)), exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_html
