r"""Preview of the Prokhorovka turn briefings: the operation map with each turn's briefing sketch drawn on it, written as
PNGs plus one HTML page (turn picker, both sides' texts in English and Russian).

  python tools/brief_preview.py <out dir> [--px 260]

Needs build\prokhorovka\cellsrc (tools\gen_prokh.cmd) for the map and build\prokhorovka\op1011_GER\text.text.loc_eng.bin
for the label names.  The sketch is replayed from tools/briefing.py's instruction list (line, polygon, pen, brush, text)
in the engine's canvas convention: lines have y = 0 at the south edge, text y = 0 at the north edge.
"""
import argparse, base64, html, io, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, 'm13')]
import azsc, briefing, textpack

ROOT = os.path.dirname(HERE)
OPN = {v: k for k, v in azsc.OP.items()}


def names():
    out = {}
    for d in ('op1011_GER', 'op1011_RUS', 'op_GER', 'op_RUS'):
        p = os.path.join(ROOT, 'build', 'prokhorovka', d, 'text.text.loc_eng.bin')
        if os.path.exists(p):
            for k, v in textpack.read(p)[1]:
                if v and k not in out: out[k] = v[0]
    return out


def colour(c): return ((c >> 16) & 255, (c >> 8) & 255, c & 255, 255)


def draw(img, ins, NM, font):
    W, H = img.size; dr = ImageDraw.Draw(img, 'RGBA'); pen = (255, 0, 0, 255); width = 3; dash = 0.0; brush = pen; tcol = (40, 40, 40, 255)
    for op, args in ins:
        n = OPN[op]; v = [a[1] for a in args]
        if n == 'pen': pen = colour(v[1]); width = max(2, int(v[2] * W * 0.9))
        elif n == 'line_style': dash = v[3]
        elif n == 'brush': brush = colour(v[0])
        elif n == 'text_color': tcol = colour(v[0])
        elif n in ('line', 'polygon'):
            pts = [(v[i] * W, (1.0 - v[i + 1]) * H) for i in range(0, len(v) - 1, 2)]
            if n == 'polygon': dr.polygon(pts, fill=brush); continue
            if dash > 0:
                seg = dash * W; on = True; acc = 0.0
                for a, b in zip(pts, pts[1:]):
                    L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
                    if on: dr.line([a, b], fill=pen, width=width)
                    acc += L
                    if acc > seg: acc = 0.0; on = not on
            else: dr.line(pts, fill=pen, width=width, joint='curve')
        elif n == 'text':
            key, x0, y0, x1, y1 = v[0], v[1], v[2], v[3], v[4]; t = NM.get(key, key)
            cx, cy = (x0 + x1) / 2 * W, (y0 + y1) / 2 * H; bb = dr.textbbox((0, 0), t, font=font)
            p = (cx - (bb[2] - bb[0]) / 2, cy - (bb[3] - bb[1]) / 2)
            dr.rectangle([p[0] - 3, p[1] - 2, p[0] + bb[2] - bb[0] + 3, p[1] + bb[3] - bb[1] + 4], fill=(255, 255, 240, 170))
            dr.text(p, t, fill=tcol, font=font)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--px', type=int, default=260); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); mp = os.path.join(a.out, 'opmap.png')
    if not os.path.exists(mp):
        subprocess.check_call([sys.executable, os.path.join(HERE, 'opmap_png.py'), os.path.join(ROOT, 'build', 'prokhorovka', 'cellsrc'), mp, '--px', str(a.px)])
    base = Image.open(mp).convert('RGBA'); NM = names()
    try: font = ImageFont.truetype('arial.ttf', max(14, base.size[0] // 110))
    except OSError: font = ImageFont.load_default()
    L = json.load(open(os.path.join(ROOT, 'docs', 'm11_prokhorovka', 'layout_10jul.json'), encoding='utf-8')); B = L['briefing']
    shots = {}; turns = []
    for t, fr in enumerate(L['frames'], 1):
        k = fr['brief']; fn = briefing.SKETCHES[k]
        if fn.__name__ not in shots:
            s = briefing.Sketch(); fn(s); img = base.copy(); draw(img, s.ins, NM, font)
            img = img.convert('RGB'); img.save(os.path.join(a.out, 'sketch_%s.png' % fn.__name__))
            small = img.resize((1100, 1100 * img.size[1] // img.size[0]), Image.LANCZOS); buf = io.BytesIO(); small.save(buf, 'JPEG', quality=82)
            shots[fn.__name__] = base64.b64encode(buf.getvalue()).decode()
        turns.append(dict(t=t, sketch=fn.__name__, w0=fr['w0'], w1=fr['w1'], sov=B['briefs'][k], ger=B['briefs_ger'][k], sov_ru=B['briefs_rus'][k], ger_ru=B['briefs_ger_rus'][k]))
    page = PAGE.replace('/*DATA*/', json.dumps(dict(shots=shots, turns=turns), ensure_ascii=False))
    open(os.path.join(a.out, 'briefings.html'), 'w', encoding='utf-8').write(page)
    print('sketches', sorted(shots), '->', a.out)


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prokhorovka Turn Briefings</title>
<style>
:root{--bg:#f4f1ea;--fg:#22201c;--mut:#6b655a;--card:#fffdf8;--line:#d9d2c3;--sov:#b3261e;--ger:#2a4fb0;--acc:#7a5c1e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1b1a17;--fg:#ece7dc;--mut:#a39c8e;--card:#25231f;--line:#3a362f;--sov:#ef6b62;--ger:#7d9bf0;--acc:#d4b16a}}
:root[data-theme="dark"]{--bg:#1b1a17;--fg:#ece7dc;--mut:#a39c8e;--card:#25231f;--line:#3a362f;--sov:#ef6b62;--ger:#7d9bf0;--acc:#d4b16a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 Georgia,serif}
header{padding:16px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:var(--mut);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:6px;padding:12px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:2}
.bar button{font:13px system-ui,sans-serif;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:5px 8px;border-radius:6px;cursor:pointer;min-width:44px}
.bar button.on{background:var(--acc);color:#fff;border-color:var(--acc)}.bar .sp{flex:1}
main{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:16px;padding:16px;max-width:1500px;margin:0 auto}
@media (max-width:900px){main{grid-template-columns:1fr}}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}figure img{width:100%;display:block}
figcaption{padding:8px 12px;color:var(--mut);font-size:12px;font-family:system-ui,sans-serif}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin-bottom:12px}
.card h2{margin:0 0 6px;font:600 13px system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase}
.sov h2{color:var(--sov)}.ger h2{color:var(--ger)}.card p{margin:0}.card p.ru{margin-top:8px;color:var(--mut);font-size:14px}
.meta{font:13px system-ui,sans-serif;color:var(--mut);margin-bottom:10px}
</style></head><body>
<header><h1>Prokhorovka, 10-14 July 1943 - turn briefings</h1><p>Each turn's briefing text for both sides, and the sketch the game draws on the operation map (F2). Turns without their own drawing reuse the last one.</p></header>
<div class="bar" id="bar"></div>
<main><figure><img id="img" alt="Operation map with the turn's briefing sketch"><figcaption id="cap"></figcaption></figure>
<section><div class="meta" id="meta"></div>
<div class="card sov"><h2>Soviet side</h2><p id="sov"></p><p class="ru" id="sovru"></p></div>
<div class="card ger"><h2>German side</h2><p id="ger"></p><p class="ru" id="gerru"></p></div></section></main>
<script>
const D=/*DATA*/;const bar=document.getElementById('bar');let cur=0;
const day=t=>['10 July','11 July','12 July','13 July','14 July'][Math.floor((t+3)/6)]||'';
D.turns.forEach((x,i)=>{const b=document.createElement('button');b.textContent=x.t;b.title='Turn '+x.t;b.onclick=()=>show(i);bar.appendChild(b)});
const sp=document.createElement('span');sp.className='sp';bar.appendChild(sp);
const prev=document.createElement('button');prev.textContent='←';prev.onclick=()=>show(Math.max(0,cur-1));bar.appendChild(prev);
const next=document.createElement('button');next.textContent='→';next.onclick=()=>show(Math.min(D.turns.length-1,cur+1));bar.appendChild(next);
function show(i){cur=i;const x=D.turns[i];[...bar.children].forEach((b,j)=>b.classList.toggle('on',j===i));
document.getElementById('img').src='data:image/jpeg;base64,'+D.shots[x.sketch];
document.getElementById('cap').textContent='Sketch: '+x.sketch.replace('brief_','turn ')+(x.sketch!=='brief_'+String(x.t).padStart(2,'0')?' (reused)':'');
document.getElementById('meta').textContent='Turn '+x.t+' of 24 · weather '+x.w0+' → '+x.w1;
for(const k of ['sov','ger'])document.getElementById(k).textContent=x[k];
document.getElementById('sovru').textContent=x.sov_ru;document.getElementById('gerru').textContent=x.ger_ru;
try{localStorage.setItem('turn',i)}catch(e){}}
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')next.click();if(e.key==='ArrowLeft')prev.click()});
let s=0;try{s=+localStorage.getItem('turn')||0}catch(e){}show(Math.min(s,D.turns.length-1));
</script></body></html>"""

if __name__ == '__main__':
    main()
