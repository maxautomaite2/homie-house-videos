"""Code-only soundtrack for a Homie episode: bouncy plucked music, sound effects and cartoon "mumble" speech.
No recorded or AI audio. Usage: python3 engine/synth_audio.py episodes/NNN-slug  (writes audio.m4a)
Cues come from episode.json: captions (mumble), overlays (pops, thuds, counters), events (clunk, furnace_on).
"""
import json, os, subprocess, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)

def tone(f, dur, shape='sine'):
    t = np.arange(int(SR * dur)) / SR
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape)) / SR
    if shape == 'sine': return np.sin(ph)
    if shape == 'tri': return 2 / np.pi * np.arcsin(np.sin(ph))
    return sum(np.sin(ph * k) / k for k in range(1, 9))   # saw-ish

def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)

def pluck(f, dur=0.6, bright=0.5):
    """Karplus-Strong string."""
    n = int(SR / f); buf = rng.uniform(-1, 1, n); out = np.empty(int(SR * dur))
    for i in range(len(out)):
        out[i] = buf[i % n]; buf[i % n] = (0.996 - 0.004 * (1 - bright)) * 0.5 * (buf[i % n] + buf[(i + 1) % n])
    return out * env(len(out), 0.002, dur * 0.5)

def noise(dur): return rng.uniform(-1, 1, int(SR * dur))

def lowpass(x, k=0.1):
    y = np.empty_like(x); a = 0.0
    for i in range(len(x)): a += k * (x[i] - a); y[i] = a
    return y

class Mix:
    def __init__(s, dur): s.b = np.zeros(int(SR * (dur + 1)))
    def add(s, t, x, g=1.0):
        i = int(t * SR)
        if i < 0 or i >= len(s.b): return
        x = x[:len(s.b) - i]; s.b[i:i + len(x)] += x * g

NOTE = lambda n: 440 * 2 ** ((n - 69) / 12)

def music(mx, total, mute):
    bpm = 116; beat = 60 / bpm
    chords = [(60, 64, 67), (57, 60, 64), (65, 69, 72), (67, 71, 74)]   # C Am F G
    cache = {}
    def pl(n, d=0.5, b=0.5):
        k = (n, d, b)
        if k not in cache: cache[k] = pluck(NOTE(n), d, b)
        return cache[k]
    i = 0; t = 0.0
    while t < total:
        if not any(a <= t < b for a, b in mute):
            ch = chords[(i // 4) % 4]; step = i % 4
            if step in (0, 2): mx.add(t, pl(ch[0] - 24, 0.5, 0.2), 0.34)            # pizz bass
            if step in (1, 3):
                for j, n in enumerate(ch): mx.add(t + j * 0.012, pl(n + 12, 0.4, 0.8), 0.13)   # uke chuck
            mel = [ch[2], ch[1], ch[2] + 2, ch[1]][step]
            if (i // 4) % 2 == 1 or step == 0: mx.add(t + beat / 2, pl(mel + 12, 0.35, 0.9), 0.10)
            mx.add(t, noise(0.03) * env(int(SR * 0.03), 0.001, 0.008), 0.035 if step % 2 else 0.02)   # shaker
        t += beat; i += 1

def sfx_pop(up=True):
    f = np.linspace(520, 980, int(SR * 0.07)) if up else np.linspace(900, 500, int(SR * 0.07))
    x = tone(f, 0.07); return x * env(len(x), 0.002, 0.03)
def sfx_thud():
    x = tone(np.linspace(150, 48, int(SR * 0.3)), 0.3) * env(int(SR * 0.3), 0.001, 0.09)
    c = noise(0.05) * env(int(SR * 0.05), 0.001, 0.012); x[:len(c)] += c * 0.6; return x
def sfx_clunk():
    x = sfx_thud() * 1.2; m = sum(tone(f, 0.5) for f in (212, 347, 533, 811)) * env(int(SR * 0.5), 0.001, 0.12) * 0.22
    out = np.zeros(int(SR * 0.9)); out[:len(x)] += x; out[:len(m)] += m
    hiss = lowpass(noise(0.8), 0.25) * np.linspace(1, 0, int(SR * 0.8)) ** 2 * 0.35; out[int(SR * .08):int(SR * .08) + len(hiss)] += hiss[:len(out) - int(SR * .08)]
    return out
def sfx_rattle(dur):
    t = np.arange(int(SR * dur)) / SR
    return lowpass(noise(dur), 0.3) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 27 * t))) * np.linspace(0.2, 1, len(t))
def sfx_ring():
    t = np.arange(int(SR * 0.42)) / SR; f = np.where(np.sin(2 * np.pi * 22 * t) > 0, 1480.0, 1860.0)
    return tone(f, 0.42) * np.minimum(1, t / 0.01) * np.minimum(1, (0.42 - t) / 0.03)
def sfx_ding(f=1318):
    x = (tone(f, 0.7) + 0.5 * tone(f * 2.01, 0.7) + 0.25 * tone(f * 3.02, 0.7)); return x * env(len(x), 0.002, 0.22)
def sfx_tick(): x = tone(2100, 0.02); return x * env(len(x), 0.001, 0.006)
def sfx_wah():
    f = np.linspace(520, 170, int(SR * 0.55)); x = tone(f, 0.55, 'saw'); t = np.arange(len(x)) / SR
    return lowpass(x, 0.12) * np.minimum(1, t / 0.02) * np.minimum(1, (0.55 - t) / 0.12) * (1 + 0.15 * np.sin(2 * np.pi * 9 * t))
def sfx_whoosh():
    n = noise(1.1); t = np.arange(len(n)) / SR
    return lowpass(n, 0.06) * np.sin(np.pi * t / 1.1) ** 2 + 0.25 * tone(np.linspace(60, 110, len(n)), 1.1) * np.minimum(1, t / 0.6)
def sfx_stinger():
    out = np.zeros(int(SR * 1.4))
    for k, n in enumerate((72, 76, 79, 84)):
        x = pluck(NOTE(n), 0.9, 0.9); i = int(k * 0.09 * SR); out[i:i + len(x)] += x[:len(out) - i] * 0.5
    return out

def mumble(text):
    """Cartoon gibberish: one short pitched blip per syllable-ish chunk, rising on questions."""
    letters = sum(ch.isalnum() for ch in text); n = max(2, round(letters / 3.0)); step = 0.092
    out = np.zeros(int(SR * (n * step + 0.2))); scale = [0, 2, 4, 7, 9, 12]
    base = 62 + (sum(map(ord, text)) % 5)
    for k in range(n):
        note = base + scale[(sum(map(ord, text[: k + 1])) + k * 3) % len(scale)]
        if text.rstrip().endswith('?') and k >= n - 2: note += 4 + 3 * (k - n + 2)
        if '!' in text: note += 3
        f0 = NOTE(note); d = 0.075; t = np.arange(int(SR * d)) / SR
        f = f0 * (1 + 0.04 * np.sin(2 * np.pi * 14 * t))
        x = tone(f, d, 'saw'); x = lowpass(x, 0.22 + 0.1 * ((k * 5) % 3))
        x *= np.minimum(1, t / 0.008) * np.minimum(1, (d - t) / 0.02)
        i = int(k * step * SR); out[i:i + len(x)] += x
    return out

def main():
    folder = sys.argv[1].rstrip('/'); ep = json.load(open(os.path.join(folder, 'episode.json')))
    A = ep['audio_end']; total = A + ep.get('end_card', {}).get('seconds', 2.2)
    ev = ep.get('events', {}); C = ev.get('clunk'); ON = ev.get('furnace_on'); ov = ep.get('overlays', [])
    stamps = [o['start'] for o in ov if o['type'] == 'stamp']
    mx = Mix(total)
    music(mx, total, [(s - 0.05, s + 1.3) for s in stamps[:1]])   # the band stops dead on the first stamp
    if C is not None:
        mx.add(C - 0.7, sfx_rattle(0.7), 0.16); mx.add(C, sfx_clunk(), 0.75)
    if ON is not None: mx.add(ON, sfx_whoosh(), 0.3); mx.add(ON + 0.6, sfx_ding(1568), 0.22)
    for o in ov:
        ty = o['type']; t = o.get('start', o.get('at', 0))
        if ty in ('tag', 'hook', 'price', 'versus', 'text'): mx.add(t, sfx_pop(), 0.3)
        elif ty == 'stamp': mx.add(t + 0.12, sfx_thud(), 0.8)
        elif ty == 'check': mx.add(t + 0.2, sfx_ding(), 0.28)
        elif ty == 'catchphrase': mx.add(t, sfx_stinger(), 0.5)
        elif ty == 'impact' and o.get('text') and 'CLUNK' not in o['text']: mx.add(t, sfx_wah(), 0.4)
        elif ty == 'counter':
            cs = o.get('count_secs', 1.6); mx.add(t, sfx_pop(), 0.3)
            for k in np.arange(t + 0.2, t + 0.2 + cs, 0.055): mx.add(float(k), sfx_tick(), 0.16)
            mx.add(t + 0.2 + cs, sfx_ding(1760), 0.3)
    for name, when in ev.items():
        if name.startswith('ring'): mx.add(when, sfx_ring(), 0.16)
    stop = ep.get('captions_stop', A)
    for t, text in ep.get('captions', []):
        if t < stop: mx.add(t + 0.03, mumble(text), 0.2)
    mx.add(A, sfx_stinger(), 0.4)
    b = mx.b[:int(total * SR)]; b = np.tanh(b * 1.5) * 0.8
    fade = int(SR * 0.4); b[-fade:] *= np.linspace(1, 0, fade)
    wav = os.path.join(folder, 'audio.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((b * 32767).astype('<i2').tobytes())
    dst = os.path.join(folder, 'audio.m4a')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-ac', '2', '-c:a', 'aac', '-b:a', '192k', dst], check=True)
    os.remove(wav); print(dst)

if __name__ == '__main__':
    main()
