"""Homie House episode renderer.

Usage:
  python3 engine/render.py episodes/001-the-drip            # full mp4
  python3 engine/render.py episodes/001-the-drip --stills 1 5.1 12   # preview PNGs + contact sheet

Reads <episode>/episode.json, the stills in <episode>/stills/, and <episode>/audio.m4a.
Writes <episode>/out/<slug>.mp4 (1080x1920, 30 fps, H.264 + AAC).
See PLAYBOOK.md for the episode.json format.
"""
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1080, 1920, 30

TEAL = (46, 138, 128); TEAL_D = (24, 92, 86); CREAM = (251, 243, 230); INK = (17, 17, 17)
YELLOW = (249, 200, 70); ORANGE = (242, 107, 58); RED = (214, 60, 52); BLUE = (70, 150, 230)
COLORS = dict(teal=TEAL, teal_dark=TEAL_D, cream=CREAM, ink=INK, yellow=YELLOW, orange=ORANGE, red=RED, blue=BLUE)

F = os.path.join(ROOT, 'engine/fonts/LilitaOne.woff')
FC = os.path.join(ROOT, 'engine/fonts/LuckiestGuy.woff')
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

# ---------- easing ----------
def clamp(x, a=0, b=1): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in_out(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def back_out(x, s=1.9):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def prog(t, a, d): return clamp((t - a) / d)
def fade(t, a, b, fin=0.0, fout=0.25):
    """1 inside [a, b], easing out over the last fout seconds."""
    return (1 - prog(t, b - fout, fout)) if fout else 1.0

# ---------- drawing helpers ----------
def text_size(d, s, f):
    b = d.textbbox((0, 0), s, font=f); return b[2] - b[0], b[3] - b[1], b[1]

def outlined(layer, xy, s, f, fill, stroke=INK, sw=10, anchor='mm'):
    ImageDraw.Draw(layer).text(xy, s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)

def paste_scaled(frame, layer, cx, cy, scale, rot=0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01: return
    l = layer
    if rot: l = l.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(scale - 1) > 0.001:
        l = l.resize((max(1, int(l.width * scale)), max(1, int(l.height * scale))), Image.BICUBIC)
    if alpha < 1:
        a = l.getchannel('A').point(lambda v: int(v * alpha)); l = l.copy(); l.putalpha(a)
    frame.alpha_composite(l, (int(cx - l.width / 2), int(cy - l.height / 2)))

def pill(text, f, bg, fg, padx=34, pady=18, outline=INK, ow=6):
    d = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    tw, th, top = text_size(d, text, f)
    w, h = tw + padx * 2, th + pady * 2
    l = Image.new('RGBA', (w + ow * 2, h + ow * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    d.rounded_rectangle((ow, ow, w + ow, h + ow), radius=h // 2, fill=bg, outline=outline, width=ow)
    d.text((ow + padx, ow + pady - top), text, font=f, fill=fg)
    return l

def card(lines, w=880, pad=40, bg=CREAM, border=INK, bw=8, radius=40):
    tmp = ImageDraw.Draw(Image.new('RGBA', (10, 10)))
    hs = [text_size(tmp, s, f)[1] + 18 for s, f, c in lines]
    h = sum(hs) + pad * 2
    l = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    d.rounded_rectangle((14, 16, w + 14, h + 16), radius=radius, fill=(0, 0, 0, 110))
    d.rounded_rectangle((0, 0, w, h), radius=radius, fill=bg, outline=border, width=bw)
    y = pad
    for (s, f, c), hh in zip(lines, hs):
        d.text((w // 2, y + hh // 2), s, font=f, fill=c, anchor='mm'); y += hh
    return l

def burst(text, r=230, n=14, fill=YELLOW):
    l = Image.new('RGBA', (r * 2 + 40, r * 2 + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    c = r + 20; pts = []
    for i in range(n * 2):
        a = math.pi * i / n; rr = r if i % 2 == 0 else r * 0.68
        pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
    d.polygon(pts, fill=fill, outline=INK, width=10)
    size = 104 if len(text) <= 7 else int(104 * 7 / len(text))
    d.text((c, c), text, font=font(FC, size), fill=RED, stroke_width=8, stroke_fill=INK, anchor='mm')
    return l

def drop_icon(size=110):
    l = Image.new('RGBA', (size, int(size * 1.35)), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    r = size * 0.42; cx = size / 2; cy = l.height - r - 8
    d.polygon([(cx, 6), (cx - r * 0.95, cy - r * 0.25), (cx + r * 0.95, cy - r * 0.25)], fill=BLUE, outline=INK, width=7)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLUE, outline=INK, width=7)
    d.polygon([(cx, 14), (cx - r * 0.8, cy - r * 0.3), (cx + r * 0.8, cy - r * 0.3)], fill=BLUE)
    d.ellipse((cx - r * 0.45, cy - r * 0.35, cx - r * 0.15, cy + r * 0.05), fill=(200, 230, 255))
    return l

def coin_icon(size=120):
    l = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    d.ellipse((6, 6, size - 6, size - 6), fill=YELLOW, outline=INK, width=7)
    d.text((size / 2, size / 2 + 4), '$', font=font(FC, int(size * 0.62)), fill=INK, anchor='mm')
    return l

ICONS = {'drop': drop_icon, 'coin': coin_icon}

def check_icon(p, size=150):
    l = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    d.ellipse((6, 6, size - 6, size - 6), fill=TEAL, outline=INK, width=8)
    pts = [(size * 0.27, size * 0.52), (size * 0.44, size * 0.68), (size * 0.75, size * 0.34)]
    for k, seg in enumerate([clamp(p * 2), clamp(p * 2 - 1)]):
        if seg > 0:
            a, b = pts[k], pts[k + 1]
            d.line([a, (a[0] + (b[0] - a[0]) * seg, a[1] + (b[1] - a[1]) * seg)], fill=CREAM, width=18, joint='curve')
    return l

def arrow_arc(p, size=170, clockwise=True):
    l = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    end = -90 + 300 * p
    d.arc((14, 14, size - 14, size - 14), -90, end, fill=INK, width=26)
    d.arc((14, 14, size - 14, size - 14), -90, end, fill=YELLOW, width=14)
    a = math.radians(end); r = size / 2 - 14; cx = cy = size / 2
    tip = (cx + r * math.cos(a), cy + r * math.sin(a))
    tang = (-math.sin(a), math.cos(a)); norm = (math.cos(a), math.sin(a))
    d.polygon([(tip[0] + tang[0] * 30, tip[1] + tang[1] * 30), (tip[0] + norm[0] * 24, tip[1] + norm[1] * 24),
               (tip[0] - norm[0] * 24, tip[1] - norm[1] * 24)], fill=YELLOW, outline=INK, width=5)
    return l if clockwise else l.transpose(Image.FLIP_LEFT_RIGHT)

# ---------- episode ----------
class Episode:
    def __init__(self, folder):
        self.dir = folder
        self.spec = json.load(open(os.path.join(folder, 'episode.json')))
        s = self.spec
        self.audio_end = s['audio_end']
        self.end_card_len = s.get('end_card', {}).get('seconds', 2.2)
        self.total = self.audio_end + self.end_card_len
        self.shots = s['shots']
        self.captions = [(c[0], c[1]) for c in s['captions']]
        self.caption_stop = s.get('captions_stop', None)
        self.overlays = s.get('overlays', [])
        self.imgs = {}
        self.cache = {}
        av = Image.open(os.path.join(ROOT, 'brand/avatar.png')).convert('RGBA').resize((420, 420), Image.LANCZOS)
        m = Image.new('L', av.size, 0); ImageDraw.Draw(m).ellipse((22, 22, 398, 398), fill=255); av.putalpha(m)
        self.avatar = av
        self.series = pill(s['series_label'], font(F, 54), TEAL, CREAM)
        random.seed(7)
        self.parts = [(random.uniform(-1, 1), random.uniform(0.6, 1.4), random.uniform(14, 34), random.uniform(0, 0.5)) for _ in range(40)]

    def base_img(self, fn):
        if fn not in self.imgs:
            im = Image.open(os.path.join(self.dir, 'stills', fn)).convert('RGB')
            sc = max(W / im.width, H / im.height)
            self.imgs[fn] = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
        return self.imgs[fn]

    # ----- effects drawn in image space -----
    def fx_geyser(self, sh, t):
        """Lever snaps off, water geyser arcs out of the faucet base. params: pop, hub [x,y], lever [x,y], arc."""
        e = sh['effect']; pop = e['pop']; hub = e['hub']; lever = e.get('lever', [hub[0] + 15, hub[1] - 110])
        arc = e.get('arc', -420)
        im = self.base_img(sh['still']).copy().convert('RGBA'); d = ImageDraw.Draw(im)
        if t < pop:
            k = prog(t, sh['start'], pop - sh['start'])
            for a in (-35, 0, 35):
                ang = math.radians(a - 90); r0, r1 = 120, 120 + 70 * k
                d.line([(lever[0] + r0 * math.cos(ang) * 0.8, lever[1] + r0 * math.sin(ang)),
                        (lever[0] + r1 * math.cos(ang) * 0.8, lever[1] + r1 * math.sin(ang))], fill=INK, width=12)
            return im.convert('RGB')
        tau = t - pop; LIGHT = (160, 210, 250); MID = (95, 170, 235)
        hgt = 1150 * ease_out(clamp(tau / 0.22)); x, yb = hub
        if hgt > 5:
            def cl(f): return (x + arc * f ** 1.6 + 18 * math.sin(f * 8 + tau * 40), yb - hgt * f)
            L, R = [], []
            for i in range(17):
                f = i / 16; cxp, cyp = cl(f); w = 70 + 170 * f
                L.append((cxp - w / 2, cyp)); R.append((cxp + w / 2, cyp))
            d.polygon(L + R[::-1], fill=LIGHT, outline=INK, width=9)
            for j in (-0.2, 0.15):
                d.line([(cl(f)[0] + j * 150 * (0.5 + f), cl(f)[1]) for f in [i / 12 for i in range(13)]], fill=(235, 246, 255), width=14)
            tx, top = cl(1.0)
            for k in range(7):
                ang = math.pi + math.pi * k / 6; r = 70 + 12 * math.sin(tau * 30 + k)
                cxk = tx + 160 * math.cos(ang); cyk = top + 50 * math.sin(ang) + 20
                d.ellipse((cxk - r, cyk - r, cxk + r, cyk + r), fill=LIGHT, outline=INK, width=8)
            d.ellipse((x - 120, yb - 40, x + 120, yb + 40), fill=MID, outline=INK, width=8)
            for vx, vy, r, delay in self.parts:
                s = tau - delay
                if s <= 0: continue
                px = tx + (vx * 600 - 250 * (1 if arc < 0 else -1)) * s; py = top + 60 - 900 * vy * s + 1900 * s * s
                if py < im.height: d.ellipse((px - r, py - r, px + r, py + r), fill=MID, outline=INK, width=5)
        hx = lever[0] - 950 * tau * (1 if arc < 0 else -1); hy = lever[1] - 2600 * tau + 3200 * tau * tau
        if hy < im.height + 200:
            if 'handle' not in self.cache:
                l = Image.new('RGBA', (90, 230), (0, 0, 0, 0)); dd = ImageDraw.Draw(l)
                dd.rounded_rectangle((18, 8, 72, 222), radius=26, fill=(196, 202, 208), outline=INK, width=8)
                dd.rounded_rectangle((30, 24, 42, 200), radius=6, fill=(240, 244, 248)); self.cache['handle'] = l
            spr = self.cache['handle'].rotate(-1100 * tau, resample=Image.BICUBIC, expand=True)
            im.alpha_composite(spr, (int(hx - spr.width / 2), int(hy - spr.height / 2)))
        return im.convert('RGB')

    def shot_frame(self, t):
        for i, sh in enumerate(self.shots):
            last = i == len(self.shots) - 1
            a, b = sh['start'], (self.total if last else sh['end'])
            if a <= t < b or (last and t >= a):
                z0, z1 = sh.get('zoom', [1.0, 1.06]); fx, fy = sh.get('focus', [0.5, 0.45])
                p = ease_in_out((t - a) / max(0.01, b - a))
                z = (z0 + (z1 - z0) * p) * (1 + 0.04 * (1 - ease_out((t - a) / 0.25)))
                eff = sh.get('effect', {}).get('type')
                im = self.fx_geyser(sh, t) if eff == 'geyser' else self.base_img(sh['still'])
                cw, ch = W / z, H / z
                cx = clamp(fx * im.width, cw / 2, im.width - cw / 2)
                cy = clamp(fy * im.height, ch / 2, im.height - ch / 2)
                return im.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
        return Image.new('RGB', (W, H), CREAM)

    # ----- overlays -----
    def layer(self, key, fn):
        if key not in self.cache: self.cache[key] = fn()
        return self.cache[key]

    def overlay(self, fr, o, t):
        ty = o['type']; a = o.get('start', o.get('at', 0)); b = o.get('end', a + o.get('dur', 1.0))
        if not (a <= t < b): return
        out = 1 - prog(t, b - 0.25, 0.25)
        key = json.dumps(o, sort_keys=True)
        if ty == 'hook':
            l = self.layer(key, lambda: self._hook(o['lines']))
            paste_scaled(fr, l, W / 2, o.get('y', 420), back_out(prog(t, a, 0.45)), alpha=out)
        elif ty == 'impact':
            l = self.layer(key, lambda: burst(o['text']))
            paste_scaled(fr, l, o.get('x', 300), o.get('y', 620), back_out(prog(t, a, 0.25)),
                         rot=-12 + 6 * math.sin(t * 20), alpha=out)
        elif ty == 'stamp':
            l = self.layer(key, lambda: pill(o['text'], font(FC, 120), COLORS[o.get('color', 'orange')], CREAM, padx=50, pady=26, ow=10))
            sp = prog(t, a, 0.18)
            paste_scaled(fr, l, o.get('x', W / 2), o.get('y', 520), 1.8 - 0.8 * ease_out(sp), rot=o.get('rot', -9), alpha=clamp(sp * 2) * out)
        elif ty == 'counter':
            cp = back_out(prog(t, a, 0.4))
            n = int(o['value'] * ease_out(prog(t, a + 0.2, o.get('count_secs', 1.6))))
            num = o.get('prefix', '') + f"{n:,}" + (o.get('suffix', '') if n >= o['value'] else '')
            sub = o['labels'][0][1]
            for st, lab in o['labels']:
                if t >= st: sub = lab
            c = card([(num, font(FC, 150), COLORS[o.get('color', 'blue')]), (sub, font(F, 62), INK)], w=760)
            y = o.get('y', 560)
            paste_scaled(fr, c, W / 2, y, cp, alpha=out)
            if o.get('icon') in ICONS:
                paste_scaled(fr, self.layer('icon_' + o['icon'], ICONS[o['icon']]), W / 2 - 395, y - 120, cp, rot=12, alpha=out)
        elif ty == 'step':
            l = self.layer(key, lambda: card([(f"STEP {o['n']}", font(F, 64), TEAL), (o['text'], font(F, 74), INK)]))
            sp = ease_out(prog(t, a + 0.1, 0.35)); sgn = -1 if o.get('from', 'left') == 'left' else 1
            paste_scaled(fr, l, W / 2 + sgn * 900 * (1 - sp), o.get('y', 470), 1, alpha=out)
        elif ty == 'tag':
            l = self.layer(key, lambda: pill(o['text'], font(F, 64), COLORS[o.get('color', 'yellow')], INK, padx=34, pady=18, ow=7))
            rp = back_out(prog(t, a, 0.3)); y = o.get('y', 760)
            paste_scaled(fr, l, o.get('x', W / 2 + 110), y, rp, rot=o.get('rot', -4), alpha=out)
            if o.get('arrow'):
                paste_scaled(fr, arrow_arc(ease_out(prog(t, a + 0.05, 0.6)), clockwise=o.get('clockwise', True)), W / 2 - 260, y, rp, alpha=out)
        elif ty == 'price':
            l = self.layer(key, lambda: pill(o['text'], font(FC, 96), YELLOW, INK, padx=46, pady=24, ow=9))
            paste_scaled(fr, l, o.get('x', W / 2 + 160), o.get('y', 560), back_out(prog(t, a + 0.05, 0.35)),
                         rot=8 + 3 * math.sin(t * 6), alpha=out)
        elif ty == 'check':
            l = self.layer(key, lambda: pill(o['text'], font(F, 76), CREAM, TEAL_D, padx=40, pady=22, ow=8))
            np_ = back_out(prog(t, a, 0.3)); y = o.get('y', 520)
            paste_scaled(fr, l, W / 2 + 70, y, np_, alpha=out)
            paste_scaled(fr, check_icon(prog(t, a + 0.1, 0.45)), W / 2 - 300, y, np_, alpha=out)
        elif ty == 'catchphrase':
            l = self.layer(key, lambda: self._catch(o['verb']))
            paste_scaled(fr, l, W / 2, o.get('y', 470) + 6 * math.sin((t - a) * 5), back_out(prog(t, a, 0.45)))
        elif ty == 'text':
            l = self.layer(key, lambda: self._text(o))
            paste_scaled(fr, l, o.get('x', W / 2), o.get('y', 520), back_out(prog(t, a, 0.3)), rot=o.get('rot', 0), alpha=out)

    def _hook(self, lines):
        l = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
        outlined(l, (W // 2, 120), lines[0], font(FC, 104 if len(lines[0]) <= 17 else int(104 * 17 / len(lines[0]))), CREAM, INK, 12)
        outlined(l, (W // 2, 270), lines[1], font(FC, 132 if len(lines[1]) <= 14 else int(132 * 14 / len(lines[1]))), YELLOW, INK, 13)
        return l

    def _catch(self, verb):
        # "IF HOMIE / CAN <VERB>, / SO CAN YOU."
        l = Image.new('RGBA', (W, 520), (0, 0, 0, 0))
        mid = f"CAN {verb.upper()},"; ms = 120 if len(mid) <= 11 else int(120 * 11 / len(mid))
        outlined(l, (W // 2, 110), "IF HOMIE", font(FC, 120), CREAM, INK, 13)
        outlined(l, (W // 2, 250), mid, font(FC, ms), CREAM, INK, 13)
        outlined(l, (W // 2, 400), "SO CAN YOU.", font(FC, 132), YELLOW, INK, 14)
        return l

    def _text(self, o):
        f = font(FC if o.get('comic', True) else F, o.get('size', 96))
        d = ImageDraw.Draw(Image.new('RGBA', (10, 10))); tw, th, _ = text_size(d, o['text'], f)
        l = Image.new('RGBA', (tw + 60, th + 60), (0, 0, 0, 0))
        outlined(l, (l.width // 2, l.height // 2), o['text'], f, COLORS[o.get('color', 'cream')], INK, 11)
        return l

    def caption(self, fr, t):
        if self.caption_stop is not None and t >= self.caption_stop: return
        cur = None
        for st, s in self.captions:
            if st <= t: cur = (st, s)
        if not cur or not cur[1]: return
        st, s = cur
        def mk():
            f = font(F, 92); d = ImageDraw.Draw(Image.new('RGBA', (10, 10))); tw, th, _ = text_size(d, s, f)
            l = Image.new('RGBA', (tw + 60, th + 60), (0, 0, 0, 0))
            outlined(l, (l.width // 2, l.height // 2), s, f, CREAM, INK, 11); return l
        paste_scaled(fr, self.layer('cap_' + s, mk), W / 2, 1500, 0.75 + 0.25 * back_out(prog(t, st, 0.18)))

    def end_card(self, t):
        ec = self.spec.get('end_card', {}); A = self.audio_end
        l = Image.new('RGBA', (W, H), CREAM + (255,)); d = ImageDraw.Draw(l)
        for i in range(-H, W + H, 120): d.line([(i, 0), (i + H, H)], fill=(238, 228, 210), width=40)
        a_sc = back_out(prog(t, A + 0.1, 0.45))
        paste_scaled(l, self.avatar, W / 2, 640, 0.6 + 0.4 * a_sc, alpha=clamp(a_sc * 1.5))
        o = prog(t, A + 0.35, 0.3)
        if o > 0:
            tl = Image.new('RGBA', (W, 520), (0, 0, 0, 0))
            outlined(tl, (W // 2, 90), ec.get('line1', 'SAVE THIS.'), font(FC, 104), TEAL, INK, 10)
            outlined(tl, (W // 2, 220), ec.get('line2', 'YOUR HOUSE IS NEXT.'), font(FC, 82), ORANGE, INK, 9)
            paste_scaled(l, tl, W / 2, 1180 + 40 * (1 - ease_out(o)), 1, alpha=o)
            handle = self.layer('handle_pill', lambda: pill(ec.get('handle', '@homiethehouseguy'), font(F, 62), TEAL, CREAM))
            paste_scaled(l, handle, W / 2, 1500, 0.8 + 0.2 * back_out(prog(t, A + 0.6, 0.35)), alpha=prog(t, A + 0.6, 0.2))
        return l

    def render(self, t):
        base = self.shot_frame(t)
        for imp in [o for o in self.overlays if o['type'] == 'impact']:
            at = imp['at']
            if at <= t < at + 0.5:
                k = (at + 0.5 - t) / 0.5; dx = int(math.sin(t * 90) * 26 * k); dy = int(math.cos(t * 77) * 20 * k)
                base = base.transform(base.size, Image.AFFINE, (1, 0, dx, 0, 1, dy), resample=Image.BILINEAR)
        fr = base.convert('RGBA')
        for imp in [o for o in self.overlays if o['type'] == 'impact']:
            if imp['at'] <= t < imp['at'] + 0.12:
                fr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(200 * (1 - (t - imp['at']) / 0.12)))))
        if t < self.audio_end:
            paste_scaled(fr, self.series, W / 2, 150, back_out(prog(t, 0.1, 0.4)))
        for o in self.overlays: self.overlay(fr, o, t)
        self.caption(fr, t)
        if t >= self.audio_end - 0.3:
            ec = self.end_card(t)
            r = int(1300 * ease_in_out(prog(t, self.audio_end - 0.3, 0.45)))
            m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).ellipse((W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r), fill=255)
            fr.paste(ec, (0, 0), m)
        return fr.convert('RGB')

def main():
    folder = sys.argv[1]; ep = Episode(folder)
    out = os.path.join(folder, 'out'); os.makedirs(out, exist_ok=True)
    if '--stills' in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index('--stills') + 1:]]
        ims = [ep.render(t).resize((360, 640)) for t in ts]
        sheet = Image.new('RGB', (360 * min(6, len(ims)), 640 * ((len(ims) + 5) // 6)), 'white')
        for i, im in enumerate(ims): sheet.paste(im, ((i % 6) * 360, (i // 6) * 640))
        sheet.save(os.path.join(out, 'preview.jpg'), quality=88); print(os.path.join(out, 'preview.jpg')); return
    dst = os.path.join(out, ep.spec['slug'] + '.mp4'); n = int(ep.total * FPS)
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-i', os.path.join(folder, 'audio.m4a'),
                           '-filter_complex', f'[1:a]apad=whole_dur={ep.total}[a]', '-map', '0:v', '-map', '[a]',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '192k', '-t', f'{ep.total}', '-movflags', '+faststart', dst], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(ep.render(i / FPS).tobytes())
    ff.stdin.close(); ff.wait(); print(dst)

if __name__ == '__main__':
    main()
