"""Homie House, code-only renderer: no AI stills, no AI voice.

Homie and the set are drawn with code (Pillow), the soundtrack comes from engine/synth_audio.py.
Overlays, captions, end card and cover come from engine/render.py, so the look matches the other episodes.

Usage:
  python3 engine/vector.py episodes/NNN-slug                 # full mp4
  python3 engine/vector.py episodes/NNN-slug --stills 1 5 9  # contact sheet
  python3 engine/vector.py episodes/NNN-slug --cover         # cover.jpg

episode.json extras: "poses": [[t, name], ...], "events": {"clunk": t, "furnace_on": t}
"""
import json, math, os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
from render import W, H, FPS, TEAL, CREAM, INK, RED, ORANGE, YELLOW, clamp, ease_out, ease_in_out, back_out, prog
from PIL import Image, ImageDraw, ImageFilter, ImageChops

SS = 2; O = 7
SKIN = (250, 212, 160); HAIR = (74, 50, 44); NAVY = (40, 52, 96); SHOE = (142, 86, 54)
SW = TEAL; SW_D = (30, 108, 100); SCARF_R = (196, 58, 62); SCARF_N = (44, 52, 100)
cos = lambda a: math.cos(math.radians(a)); sin = lambda a: math.sin(math.radians(a))


class Cv:
    """Supersampled canvas: draw in 1x coordinates, get an antialiased 1x RGBA layer."""
    def __init__(s, w, h):
        s.im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.im); s.w = w; s.h = h
    def line(s, pts, w, fill):
        p2 = [(x * SS, y * SS) for x, y in pts]; s.d.line(p2, fill=fill, width=int(w * SS), joint='curve'); r = w * SS / 2
        for x, y in p2: s.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
    def limb(s, pts, w, fill, o=O):
        s.line(pts, w + 2 * o, INK); s.line(pts, w, fill)
    def ell(s, cx, cy, rx, ry, fill, o=O):
        if o: s.d.ellipse(((cx - rx - o) * SS, (cy - ry - o) * SS, (cx + rx + o) * SS, (cy + ry + o) * SS), fill=INK)
        s.d.ellipse(((cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS), fill=fill)
    def rrect(s, x0, y0, x1, y1, r, fill, o=O):
        if o: s.d.rounded_rectangle(((x0 - o) * SS, (y0 - o) * SS, (x1 + o) * SS, (y1 + o) * SS), radius=(r + o) * SS, fill=INK)
        s.d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), radius=r * SS, fill=fill)
    def poly(s, pts, fill, o=O):
        p2 = [(x * SS, y * SS) for x, y in pts]
        if o: s.d.polygon(p2, fill=INK); s.d.line(p2 + [p2[0]], fill=INK, width=int(2 * o * SS), joint='curve')
        s.d.polygon(p2, fill=fill)
    def arc(s, cx, cy, rx, ry, a0, a1, w=7, fill=INK):
        s.d.arc(((cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS), a0, a1, fill=fill, width=int(w * SS))
    def out(s): return s.im.resize((s.w, s.h), Image.LANCZOS)


# ---------------- poses ----------------
POSES = {
    'shiver': dict(la=(100, -25), ra=(80, 205), eyes='dot', brows='worried', mouth='chatter', shiver=1),
    'phone':  dict(la=(190, 315), ra=(25, -20), eyes='closed', brows='raised', mouth='smile', lprop='phone', rprop='thumb'),
    'hello':  dict(la=(190, 315), ra=(60, 40), eyes='dot', brows='raised', mouth='talk', lprop='phone'),
    'shock':  dict(la=(235, 310), ra=(20, -35), eyes='wide', brows='none', mouth='open', rprop='phone', spike=1, dy=-14),
    'teach':  dict(la=(115, 50), ra=(60, -70), eyes='dot', brows='raised', mouth='smile', rprop='finger'),
    'sad':    dict(la=(97, 92), ra=(83, 88), eyes='dot', brows='worried', mouth='frown', dy=10, hdy=12, shiver=0.5),
    'broke':  dict(la=(97, 92), ra=(83, 88), eyes='dot', brows='worried', mouth='frown', dy=10, hdy=12, sweat=1),
    'ouch':   dict(la=(110, 60), ra=(70, 120), eyes='wince', brows='none', mouth='chatter', dy=16, hdy=14, sweat=1),
    'happy':  dict(la=(115, 50), ra=(55, -60), eyes='closed', brows='raised', mouth='grin', rprop='thumb'),
    'wink':   dict(la=(115, 50), ra=(55, -60), eyes='wink', brows='raised', mouth='grin', rprop='thumb'),
    'explain': dict(la=(115, 50), ra=(60, -70), eyes='dot', brows='raised', mouth='talk', rprop='finger'),
}
NUM = ('dy', 'hdy', 'spike', 'shiver', 'sweat')


def draw_homie(p, t=0.0, scarf=True):
    """Homie on a 1000x1560 layer; feet at (420, 1500)."""
    c = Cv(1000, 1560); fy = 1500
    shx = p.get('shiver', 0) * 5 * math.sin(t * 46); cx = 420 + shx
    dy = p.get('dy', 0) + 3 * math.sin(t * 2.3)
    ty = fy - 1010 + dy; hy = fy - 565 + dy; hipy = fy - 600 + dy
    # legs and shoes
    for sg in (-1, 1):
        c.limb([(cx + sg * 52, hipy), (420 + sg * 80, fy - 48)], 64, NAVY)
    for sg in (-1, 1):
        fx = 420 + sg * 96
        c.rrect(fx - 80, fy - 66, fx + 80, fy + 2, 30, (246, 241, 233))
        c.rrect(fx - 80, fy - 74, fx + 80, fy - 24, 30, SHOE, o=0)
        c.line([(fx - 76, fy - 24), (fx + 76, fy - 24)], 5, INK)
    c.rrect(cx - 108, hipy - 30, cx + 108, hipy + 44, 30, NAVY)
    # sweater
    c.rrect(cx - 132, ty, cx + 132, hy, 58, SW)
    c.rrect(cx - 137, hy - 50, cx + 137, hy, 18, SW_D)
    for k in range(-5, 6): c.line([(cx + k * 24, hy - 40), (cx + k * 24, hy - 10)], 3, (20, 80, 74))
    hx0, hy0 = cx + 64, ty + 150   # house logo
    c.poly([(hx0 - 26, hy0), (hx0, hy0 - 24), (hx0 + 26, hy0)], CREAM, o=0)
    c.d.rectangle(((hx0 - 17) * SS, hy0 * SS, (hx0 + 17) * SS, (hy0 + 22) * SS), fill=CREAM)
    c.d.rectangle(((hx0 - 5) * SS, (hy0 + 8) * SS, (hx0 + 5) * SS, (hy0 + 22) * SS), fill=SW)
    # neck + head position
    hx = cx + p.get('hdx', 0); hty = ty + p.get('hdy', 0) + 2 * math.sin(t * 2.3 + 1)
    c.rrect(cx - 30, ty - 44, cx + 30, ty + 24, 10, SKIN)
    if scarf:
        sway = 6 * math.sin(t * 3.1) + shx * 1.5
        c.poly([(cx - 78, ty + 10), (cx - 14, ty + 10), (cx - 10 + sway, ty + 300), (cx - 74 + sway, ty + 300)], SCARF_R)
        for k in range(4):
            y0 = ty + 62 + k * 62; f = (y0 - ty - 10) / 290
            c.poly([(cx - 78 + 4 * f + sway * f, y0), (cx - 14 + 4 * f + sway * f, y0), (cx - 13 + sway * (f + .1), y0 + 30), (cx - 77 + sway * (f + .1), y0 + 30)], SCARF_N, o=0)
        for k in range(5): c.line([(cx - 68 + k * 13 + sway, ty + 304), (cx - 68 + k * 13 + sway, ty + 330)], 5, INK)
        c.rrect(cx - 108, ty - 40, cx + 108, ty + 36, 36, SCARF_R)
        for k in (-2, 0, 2): c.rrect(cx + k * 34 - 15, ty - 40, cx + k * 34 + 15, ty + 36, 4, SCARF_N, o=0)
        c.line([(cx - 100, ty - 43), (cx + 100, ty - 43)], 7, INK); c.line([(cx - 100, ty + 39), (cx + 100, ty + 39)], 7, INK)
    else:
        c.ell(cx, ty + 4, 72, 20, SW_D)
    # head
    for sg in (-1, 1): c.ell(hx + sg * 90, hty - 185, 32, 37, SKIN)
    c.rrect(hx - 84, hty - 368, hx + 84, hty - 34, 80, SKIN)
    sp = p.get('spike', 0)
    puffs = [(-106, -292, 50), (-86, -352, 62), (-36, -400, 70), (34, -406, 70), (90, -358, 62), (110, -294, 50), (0, -374, 66)]
    spikes = []
    if sp > 0.05:
        for a in range(200, 350, 28):
            L = 120 + 95 * sp * (1 + 0.25 * math.sin(a * 7.3)); bx, by = hx, hty - 340
            spikes.append([(bx + 80 * cos(a - 20), by + 70 * sin(a - 20)), (bx + L * cos(a), by + L * sin(a)), (bx + 80 * cos(a + 20), by + 70 * sin(a + 20))])
    for tri in spikes: c.poly(tri, HAIR)
    for dx, dy_, r in puffs: c.ell(hx + dx, hty + dy_, r + O, r + O, INK, o=0)
    for dx, dy_, r in puffs: c.ell(hx + dx, hty + dy_, r, r, HAIR, o=0)
    for tri in spikes: c.poly(tri, HAIR, o=0)
    # face
    ey = hty - 236; exs = (hx - 32, hx + 40); eyes = p.get('eyes', 'dot')
    if p.get('blink') and eyes == 'dot': eyes = 'blink'
    for i, ex in enumerate(exs):
        e = eyes if eyes != 'wink' else ('dot' if i == 0 else 'closed')
        if e == 'dot': c.ell(ex, ey, 12, 19, INK, o=0)
        elif e == 'blink': c.line([(ex - 14, ey + 4), (ex + 14, ey + 4)], 7, INK)
        elif e == 'closed': c.arc(ex, ey + 12, 20, 18, 200, 340, 8)
        elif e == 'wide':
            c.ell(ex + (-6 if i == 0 else 6), ey - 4, 30, 34, (255, 255, 255), o=6); c.ell(ex + 6, ey - 2, 9, 11, INK, o=0)
        elif e == 'wince':
            sg = 1 if i == 0 else -1
            c.line([(ex - 14 * sg, ey - 12), (ex + 12 * sg, ey), (ex - 14 * sg, ey + 12)], 7, INK)
    b = p.get('brows', 'none')
    if b != 'none' and eyes != 'wide':
        for i, ex in enumerate(exs):
            inner = 1 if i == 0 else -1; by = ey - 44 - (10 if b == 'raised' else 0)
            k = 12 if b == 'worried' else 0
            c.line([(ex - 20 * inner, by + k), (ex + 20 * inner, by - k)], 7, INK)
    c.ell(hx + 6, hty - 172, 40, 30, SKIN)
    mx, my = hx + 4, hty - 94; m = p.get('mouth', 'smile')
    if m == 'talk': m = 'talk_o' if math.sin(t * 22) > -0.2 else 'smile'
    if m == 'smile': c.arc(mx, my - 22, 46, 30, 25, 155, 8)
    elif m == 'frown': c.arc(mx, my + 12, 38, 26, 205, 335, 8)
    elif m == 'grin':
        c.d.chord(((mx - 56) * SS, (my - 52) * SS, (mx + 56) * SS, (my + 34) * SS), 0, 180, fill=(255, 255, 255), outline=INK, width=7 * SS)
        c.line([(mx - 52, my - 9), (mx + 52, my - 9)], 7, INK)
    elif m == 'open':
        c.ell(mx, my - 6, 34, 44, (118, 30, 40), o=6); c.ell(mx, my + 18, 20, 13, (232, 112, 122), o=0)
        c.d.rectangle(((mx - 22) * SS, (my - 48) * SS, (mx + 22) * SS, (my - 36) * SS), fill=(255, 255, 255))
    elif m == 'talk_o': c.ell(mx, my - 4, 20, 24, (118, 30, 40), o=6)
    elif m == 'chatter':
        j = 3 * math.sin(t * 60)
        c.rrect(mx - 44, my - 24 + j, mx + 44, my + 14 + j, 10, (255, 255, 255), o=6)
        c.line([(mx - 40, my - 5 + j), (mx + 40, my - 5 + j)], 4, INK)
        for k in (-22, 0, 22): c.line([(mx + k, my - 22 + j), (mx + k, my + 12 + j)], 4, INK)
    if p.get('sweat', 0) > 0.3:
        sx, sy = hx + 66, hty - 262 + 16 * ((t * 0.9) % 1)
        c.poly([(sx, sy - 26), (sx + 13, sy + 2), (sx - 13, sy + 2)], (120, 190, 240), o=5); c.ell(sx, sy + 4, 14, 14, (120, 190, 240), o=0)
        c.arc(sx, sy + 4, 19, 19, 20, 160, 5)
    # arms (drawn last: they pass in front of the body and head)
    for side, key, propk in ((-1, 'la', 'lprop'), (1, 'ra', 'rprop')):
        a1, a2 = p[key]; a1 += 2 * math.sin(t * 2 + side); a2 += 3 * math.sin(t * 2.6 + side)
        sh = (cx + side * 118, ty + 54)
        e = (sh[0] + 185 * cos(a1), sh[1] + 185 * sin(a1)); h = (e[0] + 175 * cos(a2), e[1] + 175 * sin(a2))
        w = (e[0] + 140 * cos(a2), e[1] + 140 * sin(a2)); prop = p.get(propk)
        if prop == 'phone':
            c.limb([(h[0] - 10 * side, h[1] - 6), (h[0] - 26 * side, h[1] - 104)], 52, (52, 60, 78))
            c.line([(h[0] - 13 * side, h[1] - 22), (h[0] - 23 * side, h[1] - 90)], 32, (126, 150, 176))
        elif prop == 'thumb': c.limb([h, (h[0] + 6, h[1] - 66)], 27, SKIN)
        elif prop == 'finger': c.limb([h, (h[0] + 4, h[1] - 84)], 23, SKIN)
        c.limb([sh, e, w], 58, SW)
        c.line([(e[0] + 122 * cos(a2), e[1] + 122 * sin(a2)), w], 58, SW_D)
        c.ell(h[0], h[1], 40, 40, SKIN)
    return c.out()


def pose_at(t, keys):
    """keys: [[t, name]]; eases numeric fields over 0.3 s after each key, with a little overshoot."""
    cur = keys[0]; prev = keys[0]
    for i, k in enumerate(keys):
        if k[0] <= t: cur = k; prev = keys[i - 1] if i else k
    A = POSES[prev[1]]; B = POSES[cur[1]]; f = back_out(prog(t, cur[0], 0.3), 1.4); p = dict(B)
    for key in ('la', 'ra'):
        p[key] = tuple(A[key][i] + (B[key][i] - A[key][i]) * f for i in (0, 1))
    for key in NUM:
        p[key] = A.get(key, 0) + (B.get(key, 0) - A.get(key, 0)) * clamp(f)
    if f < 0.45:  # props and face switch mid-move
        for key in ('lprop', 'rprop'): p[key] = A.get(key) if A.get(key) == B.get(key) else None
    p['blink'] = (t % 2.9) < 0.11
    return p


# ---------------- set ----------------
def lerp(a, b, f): return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))

def make_bg():
    im = Image.new('RGB', (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        col = lerp((204, 184, 156), (176, 154, 128), clamp((y - 300) / 960)) if y < 1262 else lerp((166, 150, 130), (126, 112, 98), (y - 1262) / 658)
        d.line([(0, y), (W, y)], fill=col)
    for y in range(520, 1262, 150): d.line([(0, y), (W, y)], fill=(188, 168, 142), width=3)
    # ceiling with joists
    d.rectangle((0, 0, W, 300), fill=(62, 40, 26))
    for i in range(10):
        xb = -160 + i * 150; xt = xb * 1.35 - 190
        d.polygon([(xt, 0), (xt + 70, 0), (xb + 52, 300), (xb, 300)], fill=(168, 112, 66))
        d.polygon([(xt + 70, 0), (xt + 100, 0), (xb + 74, 300), (xb + 52, 300)], fill=(112, 72, 42))
    d.rectangle((0, 286, W, 330), fill=(124, 80, 46)); d.rectangle((0, 326, W, 334), fill=(84, 54, 32))
    # shelves, left
    d.rectangle((0, 640, 176, 1250), fill=(92, 70, 52))
    for k, y in enumerate((760, 900, 1040, 1180)):
        d.rectangle((0, y, 176, y + 16), fill=(132, 100, 72))
        for j, x in enumerate((8, 66, 118)):
            hh = 46 + ((k * 7 + j * 13) % 40)
            d.rectangle((x, y - hh, x + 44, y), fill=[(196, 170, 130), (150, 162, 170), (184, 120, 92), (214, 204, 186)][(k + j) % 4])
    # stairs
    d.polygon([(170, 1262), (250, 1262), (640, 560), (640, 480)], fill=(120, 82, 50))
    for i in range(9):
        x0 = 230 + i * 44; y0 = 1196 - i * 76
        d.rectangle((x0, y0, x0 + 150, y0 + 20), fill=(196, 140, 86)); d.rectangle((x0 + 8, y0 + 20, x0 + 150, y0 + 76), fill=(140, 96, 58))
    # ducts and pipes
    d.rectangle((360, 372, W, 486), fill=(170, 176, 182)); d.rectangle((360, 372, W, 398), fill=(206, 212, 216)); d.rectangle((360, 464, W, 486), fill=(128, 134, 140))
    for x in range(420, W, 170): d.line([(x, 372), (x, 486)], fill=(140, 146, 152), width=4)
    d.rectangle((640, 486, 900, 1010), fill=(158, 164, 170)); d.rectangle((640, 486, 690, 1010), fill=(190, 196, 200)); d.rectangle((860, 486, 900, 1010), fill=(124, 130, 136))
    d.line([(640, 760), (900, 760)], fill=(130, 136, 142), width=4)
    d.rectangle((930, 330, 990, 1010), fill=(196, 200, 204)); d.rectangle((930, 330, 946, 1010), fill=(226, 230, 232))
    for y in (520, 700, 880): d.rectangle((924, y, 996, y + 14), fill=(150, 156, 160))
    d.line([(1030, 330), (1030, 1560)], fill=(186, 112, 70), width=14); d.line([(1030, 700), (W, 700)], fill=(186, 112, 70), width=14)
    # water heater, right edge
    d.rounded_rectangle((968, 900, 1180, 1660), radius=40, fill=(218, 218, 214)); d.rectangle((968, 940, 1000, 1620), fill=(238, 238, 234))
    d.rectangle((1010, 1240, 1080, 1420), fill=(244, 238, 226)); d.rectangle((1010, 1240, 1080, 1270), fill=(226, 120, 60))
    d.ellipse((930, 1630, 1200, 1690), fill=(92, 82, 72))
    # floor line, furnace + Homie contact shadows
    d.rectangle((0, 1256, W, 1268), fill=(120, 104, 88))
    sh = Image.new('L', (W, H), 0); sd = ImageDraw.Draw(sh)
    sd.ellipse((90, 1650, 520, 1750), fill=120); sd.ellipse((540, 1630, 1040, 1730), fill=130)
    im.paste((40, 30, 24), (0, 0), sh.filter(ImageFilter.GaussianBlur(22)))
    im = im.filter(ImageFilter.GaussianBlur(2.2))
    # warm bulb glow + vignette + grain
    g = Image.new('L', (W, H), 0); gd = ImageDraw.Draw(g)
    for r in range(900, 0, -20): gd.ellipse((540 - r, 60 - r, 540 + r, 60 + r), fill=int(120 * (1 - r / 900) ** 2))
    im = ImageChops.screen(im, Image.merge('RGB', [g.point(lambda v: int(v * k)) for k in (1.0, 0.82, 0.5)]))
    b = Image.new('L', (W, H), 0); ImageDraw.Draw(b).ellipse((496, 22, 584, 110), fill=255)
    im.paste((255, 248, 220), (0, 0), b.filter(ImageFilter.GaussianBlur(10)))
    v = Image.new('L', (W, H), 0); vd = ImageDraw.Draw(v)
    for r in range(0, 60): vd.rectangle((r * 9, r * 14, W - r * 9, H - r * 14), fill=int(255 * min(1, 0.62 + r / 60 * 0.5)))
    im = ImageChops.multiply(im, Image.merge('RGB', [v.filter(ImageFilter.GaussianBlur(60))] * 3))
    noise = Image.effect_noise((W, H), 22).convert('RGB')
    return Image.blend(im, ImageChops.overlay(im, noise), 0.35)


def make_furnace(glow):
    """Furnace sprite 380x720 (body 330x660 inside a 25 px margin)."""
    c = Cv(380, 720); x0, y0, x1, y1 = 25, 30, 355, 690
    c.rrect(x0, y0, x1, y1, 10, (134, 138, 142), o=5)
    c.d.rectangle((x0 * SS, y0 * SS, (x0 + 46) * SS, y1 * SS), fill=(160, 164, 168))
    c.d.rectangle(((x1 - 34) * SS, y0 * SS, x1 * SS, y1 * SS), fill=(106, 110, 114))
    c.rrect(x0 + 34, y0 + 30, x1 - 34, y0 + 300, 8, (150, 154, 158), o=4)
    c.rrect(x0 + 34, y0 + 330, x1 - 34, y1 - 40, 8, (142, 146, 150), o=4)
    for gx in range(3):
        for gy in range(5):
            xx = x0 + 62 + gx * 74; yy = y0 + 62 + gy * 22
            c.rrect(xx, yy, xx + 54, yy + 10, 5, (255, 150, 60) if glow else (58, 60, 64), o=0)
    c.rrect(x0 + 110, y0 + 232, x1 - 110, y0 + 262, 6, (96, 100, 104), o=3)
    c.rrect(x0 + 96, y0 + 440, x0 + 176, y0 + 560, 4, (244, 238, 226), o=3)
    c.d.rectangle(((x0 + 96) * SS, (y0 + 440) * SS, (x0 + 176) * SS, (y0 + 462) * SS), fill=(226, 120, 60))
    for k in range(4): c.line([(x0 + 106, y0 + 480 + k * 18), (x0 + 166, y0 + 480 + k * 18)], 3, (150, 140, 128))
    c.ell(x1 - 70, y0 + 380, 12, 12, (60, 62, 66), o=3)
    for (rx, ry, rr) in ((x0 + 60, y1 - 60, 16), (x1 - 80, y1 - 90, 12), (x0 + 220, y0 + 316, 9)): c.ell(rx, ry, rr, rr * .7, (150, 104, 76), o=0)
    im = c.out()
    if glow:
        halo = Image.new('RGBA', im.size, (0, 0, 0, 0)); hd = ImageDraw.Draw(halo)
        hd.ellipse((30, 20, 350, 260), fill=(255, 140, 50, 130))
        halo = halo.filter(ImageFilter.GaussianBlur(40)); out = Image.new('RGBA', im.size, (0, 0, 0, 0))
        out.alpha_composite(im); out.alpha_composite(halo); return out
    return im


class VectorEpisode(R.Episode):
    HX, HY = 300 - 420, 1700 - 1500   # Homie layer origin on the frame
    FX, FY = 540, 797                 # furnace sprite origin (sprite scaled 1.28x)

    def __init__(self, folder):
        super().__init__(folder)
        self.keys = self.spec['poses']; ev = self.spec.get('events', {})
        self.t_clunk = ev.get('clunk', 1.25); self.t_on = ev.get('furnace_on', 25.6)
        self.bg = make_bg(); k = lambda im: im.resize((486, 922), Image.LANCZOS)
        self.furn = k(make_furnace(False)); self.furn_on = k(make_furnace(True))
        # end-card avatar drawn by the same rig
        hl = draw_homie(dict(POSES['wink']), 0.4, scarf=False)
        av = Image.new('RGBA', (420, 420), TEAL + (255,)); head = hl.crop((150, 20, 690, 560)).resize((420, 420), Image.LANCZOS)
        av.alpha_composite(head); m = Image.new('L', (420, 420), 0); ImageDraw.Draw(m).ellipse((22, 22, 398, 398), fill=255); av.putalpha(m)
        ring = ImageDraw.Draw(av); ring.ellipse((22, 22, 398, 398), outline=INK, width=10)
        self.avatar = av

    def scene(self, t):
        fr = self.bg.copy().convert('RGBA'); C = self.t_clunk
        # furnace: rattles, clunks, later glows
        dx = dy = 0
        if C - 0.7 < t < C: dx = 5 * math.sin(t * 75) * prog(t, C - 0.7, 0.7)
        elif C <= t < C + 0.5: dy = 14 * math.exp(-(t - C) * 9) * math.cos((t - C) * 40)
        g = ease_in_out(prog(t, self.t_on, 0.9))
        f = self.furn if g <= 0 else (self.furn_on if g >= 1 else Image.blend(self.furn, self.furn_on, g))
        if g > 0: dx += 1.5 * math.sin(t * 50)
        fr.alpha_composite(f, (int(self.FX + dx), int(self.FY + dy)))
        fx = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fx)
        if C <= t < C + 3.2:   # smoke puffs
            rnd = random.Random(5)
            for k in range(7):
                st = C + k * 0.16; a = t - st
                if a <= 0: continue
                x = self.FX + 243 + rnd.uniform(-90, 90) + 30 * math.sin(a * 2 + k); y = self.FY + 40 - a * 150
                r = 34 + a * 46; al = int(190 * clamp(1 - a / 2.4))
                if al > 0: d.ellipse((x - r, y - r, x + r, y + r), fill=(70, 66, 64, al))
        if g > 0.5:            # heat waves once it runs again
            for k in range(3):
                ph = (t * 0.7 + k / 3) % 1; x = self.FX + 140 + k * 100; y0 = self.FY + 40 - ph * 190
                pts = [(x + 14 * math.sin((y0 + j * 12) / 22 + t * 4), y0 + j * 12) for j in range(7)]
                d.line(pts, fill=(255, 170, 80, int(170 * math.sin(ph * math.pi))), width=9, joint='curve')
        p = pose_at(t, self.keys)
        if t < self.t_on and p.get('mouth') in ('chatter', 'frown', 'talk', 'smile'):   # cold breath
            ph = (t * 0.8) % 1; bx = 300 + 110 + ph * 90; by = 1700 - 1090 - ph * 60; r = 16 + ph * 30
            d.ellipse((bx - r, by - r, bx + r, by + r), fill=(255, 255, 255, int(110 * math.sin(ph * math.pi))))
        fr.alpha_composite(fx.filter(ImageFilter.GaussianBlur(5)))
        fr.alpha_composite(draw_homie(p, t), (self.HX, self.HY))
        return fr.convert('RGB')

    def shot_frame(self, t):
        im = self.scene(t)
        for i, sh in enumerate(self.shots):
            last = i == len(self.shots) - 1; a, b = sh['start'], (self.total if last else sh['end'])
            if a <= t < b or (last and t >= a):
                z0, z1 = sh.get('zoom', [1.0, 1.06]); fx, fy = sh.get('focus', [0.5, 0.45])
                pp = ease_in_out((t - a) / max(0.01, b - a))
                z = (z0 + (z1 - z0) * pp) * (1 + 0.04 * (1 - ease_out((t - a) / 0.25)))
                cw, ch = W / z, H / z
                cx = clamp(fx * W, cw / 2, W - cw / 2); cy = clamp(fy * H, ch / 2, H - ch / 2)
                return im.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
        return im


def main():
    folder = sys.argv[1].rstrip('/'); ep = VectorEpisode(folder)
    out = os.path.join(folder, 'out'); os.makedirs(out, exist_ok=True)
    if '--cover' in sys.argv:
        c = ep.spec['cover']; os.makedirs(os.path.join(folder, 'stills'), exist_ok=True)
        ep.scene(c.get('t', 9.7)).save(os.path.join(folder, 'stills', c['still']), quality=95)
        dst = os.path.join(out, 'cover.jpg'); R.render_cover(ep).save(dst, quality=92); print(dst); return
    if '--stills' in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index('--stills') + 1:]]
        sc = 0.5 if '--big' in sys.argv else 1 / 3
        w, h = int(W * sc), int(H * sc); ims = [ep.render(t).resize((w, h), Image.LANCZOS) for t in ts]
        n = min(6, len(ims)); sheet = Image.new('RGB', (w * n, h * ((len(ims) + n - 1) // n)), 'white')
        for i, im in enumerate(ims): sheet.paste(im, ((i % n) * w, (i // n) * h))
        sheet.save(os.path.join(out, 'preview.jpg'), quality=88); print(os.path.join(out, 'preview.jpg')); return
    dst = os.path.join(out, ep.spec['slug'] + '.mp4'); tmp = dst.replace('.mp4', '.part.mp4'); n = int(ep.total * FPS)
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-i', os.path.join(folder, 'audio.m4a'),
                           '-filter_complex', f'[1:a]apad=whole_dur={ep.total}[a]', '-map', '0:v', '-map', '[a]',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '192k', '-t', f'{ep.total}', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    for i in range(n): ff.stdin.write(ep.render(i / FPS).tobytes())
    ff.stdin.close()
    if ff.wait() == 0: os.replace(tmp, dst); print(dst)
    else: sys.exit('ffmpeg failed')


if __name__ == '__main__':
    main()
