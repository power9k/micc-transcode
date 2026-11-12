#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kịch bản 2 v3 CapCut draft builder (extends kb2_build.py):
V1 = one continuous picture track (official 4K film b-roll filling 9:16 + presenter only on her own-audio lines + outro),
camera keys per clip (scale / position / ROTATION -> dolly push/pull, orbit, lateral slide, jerky punch-ins),
team transitions on V1 cuts, team video effects on an effect track, title-behind-presenter sandwich (matting),
keyword titles with same-colour glow, speech track (presenter takes + approved VO), music with volume keys, SFX.
usage: kb3_build.py plan_kb3.json"""
import json, copy, uuid, time, os, sys, math, unicodedata, re
ENG = os.path.dirname(os.path.abspath(__file__))
V3 = ENG
sys.path.insert(0, ENG)
import insert_block as ib
from fontTools.ttLib import TTFont
from PIL import ImageFont
PL = json.load(open(sys.argv[1]))
TPL = json.load(open(ENG + '/kb1_draft_info.json'))
MEDIA = {k: dict(v) for k, v in PL['media'].items()}
exec(open(ENG + '/acad_lib.py', encoding='utf-8').read())
PROJECT = PL['project']; OD = PL['out_dir'] + '/' + PROJECT; os.makedirs(OD, exist_ok=True)
AD = PL['asset_dir']
FD = ENG + '/fonts/'
FONTS = {}
for key, fn in (('BIG', 'SVN-Nexa Rush Sans Black.ttf'), ('ITA', 'SVN-Georgia Italic.ttf'), ('SCR', 'SVN-Dancing script.ttf'), ('BEB', 'UTM Bebas.ttf')):
    t = TTFont(FD + fn); o = t['OS/2']
    FONTS[key] = dict(file=fn, path=(PL.get('font_dir') or AD) + '/' + fn, typo=(o.sTypoAscender - o.sTypoDescender) / t['head'].unitsPerEm,
                      cap=(getattr(o, 'sCapHeight', 0) or 0.7 * t['head'].unitsPerEm) / t['head'].unitsPerEm, pf=ImageFont.truetype(FD + fn, 200))
REP, E = [], []

# ------------------------------------------------------------------ camera keys -> CapCut clip keyframes
def cover(rot_deg, portrait_src):
    a = math.radians(abs(rot_deg))
    if portrait_src:    # 9:16 source on 9:16 canvas: both directions tight
        return max(math.cos(a) + (W / H) * math.sin(a), math.cos(a) + (H / W) * math.sin(a))
    return math.cos(a) + (W / H) * math.sin(a)   # 16:9 fill-by-height: only the vertical is tight
def key2clip(mk, m, u, v, rot):
    md = MEDIA[mk]; S0 = md['S0']; wide = md['w'] > md['h']
    Sw = S0 if wide else 1.0                  # displayed width / canvas width at m = 1
    Sh = 1.0                                   # displayed height / canvas height at m = 1 (both fill the height)
    X = -(u - 0.5) * 2 * Sw * m; Y = (v - 0.5) * 2 * Sh * m
    c = cover(rot, not wide)
    if m < c - 1e-4: E.append('%s: scale %.3f does not cover rotation %.2f' % (mk, m, rot))
    lx = Sw * m - c; ly = Sh * m - c
    X = max(-lx, min(lx, X)); Y = max(-ly, min(ly, Y))
    return round(S0 * m, 5), round(X, 5), round(Y, 5), round(rot, 3)
def interp5(keys, t):
    if t <= keys[0][0]: return keys[0][1:]
    if t >= keys[-1][0]: return keys[-1][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            f = 0.0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * f for i in range(1, 5))
def window(keys, t0, t1):
    out = [(t0,) + tuple(interp5(keys, t0))] + [tuple(k) for k in keys if t0 + 1e-4 < k[0] < t1 - 1e-4] + [(t1,) + tuple(interp5(keys, t1))]
    return out
def apply_motion(sg, mk, keys, t0, src0):
    cl = [(t,) + key2clip(mk, m, u, v, r) for t, m, u, v, r in keys]
    off = lambda t: int(round((src0 + (t - t0)) * S))
    sg['clip']['scale'] = {'x': cl[0][1], 'y': cl[0][1]}; sg['clip']['transform'] = {'x': cl[0][2], 'y': cl[0][3]}; sg['clip']['rotation'] = cl[0][4]
    sg['common_keyframes'] = []
    if len(cl) > 1 and any(abs(a - b) > 1e-5 for k in cl[1:] for a, b in zip(k[1:], cl[0][1:])):
        kl = [ib.kf_track('KFTypeScaleX', [(off(k[0]), k[1]) for k in cl]), ib.kf_track('KFTypePositionX', [(off(k[0]), k[2]) for k in cl]),
              ib.kf_track('KFTypePositionY', [(off(k[0]), k[3]) for k in cl])]
        if any(abs(k[4]) > 1e-4 for k in cl): kl.append(ib.kf_track('KFTypeRotation', [(off(k[0]), k[4]) for k in cl]))
        ib.add_keyframes(sg, kl)
        sg['clip']['rotation'] = cl[0][4]
    return cl

def vanim(sg, name, aid, typ, dur):
    a = {'id': U(), 'type': 'sticker_animation', 'animations': [{'anim_adjust_params': None, 'platform': 'all', 'panel': 'video', 'material_type': 'video',
         'name': name, 'id': aid, 'type': typ, 'resource_id': aid, 'start': 0, 'duration': us(dur), 'path': '', 'request_id': '', 'category_id': '', 'category_name': ''}],
         'multi_language_current': 'none'}
    OM.setdefault('material_animations', []).append(a); sg['extra_material_refs'].append(a['id'])

# ------------------------------------------------------------------ picture tracks
# bản nhiều lớp (chủ dặn 11/11): V1 = A-roll liền mạch có tiếng gốc · trên = cảnh phụ (B-roll) + hoạt ảnh vào/ra + chuyển cảnh
#   · trên nữa = lớp điều chỉnh màu từng cảnh · chữ · hiệu ứng · nhạc nền · SFX
LAYER = bool(PL.get('ashots'))
def grade_mats(md):
    out = []
    for gt, gv in (md.get('grade') or {}).items():   # Điều chỉnh của CapCut: sáng, tương phản, nhiệt độ…
        if abs(gv) < 0.01: continue
        pf = V3 + '/presets/effect_effects_%s.json' % gt
        gm = copy.deepcopy(ib.load(pf if os.path.exists(pf) else V3 + '/presets/effect_effects_brightness.json')['materials']['effects'][0]); gm['type'] = gt   # bão hòa: cùng bộ Điều chỉnh, khác loại
        gm['id'] = U(); gm['value'] = float(gv); gm['path'] = ''; gm['request_id'] = ''
        if 'lumi_hub_path' in gm: gm['lumi_hub_path'] = ''
        OM.setdefault('effects', []).append(gm); out.append(gm['id'])
    return out
def shot_seg(sh, vol=0.0, grade=True):
    mk = sh['media']; md = MEDIA[mk]
    sg = vseg(mk, sh['src'], sh['t0'], sh['t1'], vol, [(sh['t0'], 1.0, 0.0, 0.0)], fades=(0.03, 0.06))
    cl = apply_motion(sg, mk, [tuple(k) for k in sh['keys']], sh['t0'], sh['src'])
    spd = sh.get('spd', 1.0)
    if spd < 0.999:
        sg['speed'] = spd; sg['source_timerange']['duration'] = int(round(sg['target_timerange']['duration'] * spd))
        s0 = sg['source_timerange']['start']
        for ck in sg.get('common_keyframes', []):
            for kf in ck['keyframe_list']: kf['time_offset'] = int(round(s0 + (kf['time_offset'] - s0) * spd))
        for mid in sg['extra_material_refs']:
            for m in OM.get('speeds', []):
                if m['id'] == mid: m['speed'] = spd
    if sh['src'] + (sh['t1'] - sh['t0']) * sh.get('spd', 1.0) > md['dur'] + 1e-3: E.append('past end %s %.2f' % (mk, sh['src'] + sh['t1'] - sh['t0']))
    if grade and md.get('grade'):
        sg['extra_material_refs'] += grade_mats(md)
        for fl in ('enable_adjust', 'enable_color_wheels', 'enable_color_curves'): sg[fl] = True
    return sg, cl
V1 = []; SHOTREC = []; BSEGS = []; ADJ = []
BASE = PL['ashots'] if LAYER else PL['shots']
for sh in BASE:
    sg, cl = shot_seg(sh, 1.0 if LAYER else 0.0, grade=not LAYER)
    V1.append(sg); SHOTREC.append(dict(sh, clip=cl))
if BASE[0]['t0'] > 1e-6: E.append('V1 does not start at 0')
for a, b in zip(BASE, BASE[1:]):
    if abs(a['t1'] - b['t0']) > 1e-6: E.append('V1 gap/overlap %.3f %.3f' % (a['t1'], b['t0']))
B_IN = [('Zoom 1', '6740868384637850120', .4), ('Stretched In', '7548882779841285377', .45), ('Fade In', '6798320778182922760', .25), ('Zoom Out', '6798332584276267527', .4)]
B_OUT = [('Fade Out', '6798320902548230669', .25), ('Slide Down', '6798333787986989576', .35)]
if LAYER:
    prev_end, nb = None, 0
    for sh in PL['bshots']:
        sg, cl = shot_seg(sh, 0.0, grade=False)
        if prev_end is None or abs(prev_end - sh['t0']) > 1e-3:   # cảnh phụ vào từ người nói → hoạt ảnh vào (đổi kiểu liên tục)
            nm, aid, d = B_IN[nb % len(B_IN)]; vanim(sg, nm, aid, 'in', min(d, (sh['t1'] - sh['t0']) / 3)); nb += 1
        BSEGS.append(sg); SHOTREC.append(dict(sh, clip=cl)); prev_end = sh['t1']
    # ra khỏi cảnh phụ (về người nói): xen kẽ hoạt ảnh ra
    for k, sh in enumerate(PL['bshots']):
        nxt = PL['bshots'][k + 1] if k + 1 < len(PL['bshots']) else None
        if (nxt is None or abs(nxt['t0'] - sh['t1']) > 1e-3) and k % 2 == 1:
            nm, aid, d = B_OUT[k // 2 % len(B_OUT)]; vanim(BSEGS[k], nm, aid, 'out', min(d, (sh['t1'] - sh['t0']) / 3))
    # lớp điều chỉnh màu: 1 lớp / cảnh (theo màu gốc của cảnh đang hiện) → cả video đồng màu
    ADJ_T = copy.deepcopy(next(s for t in TPL['tracks'] if t['type'] == 'adjust' for s in t['segments']))
    for k, sh in enumerate(PL['shots']):
        md = MEDIA[sh['media']]; refs = grade_mats(md)
        if not refs: continue
        ph = {'id': U(), 'name': 'Màu cảnh %d' % (k + 1), 'type': 'adjust', 'material_resource_id': ''}
        OM.setdefault('placeholders', []).append(ph)
        sg = copy.deepcopy(ADJ_T); sg['id'] = U(); sg['material_id'] = ph['id']; sg['extra_material_refs'] = refs
        sg['target_timerange'] = {'start': us(sh['t0']), 'duration': us(sh['t1'] - sh['t0'])}; sg['source_timerange'] = None
        sg['common_keyframes'] = []; sg['keyframe_refs'] = []; sg['group_id'] = ''; sg['raw_segment_id'] = ''
        ADJ.append(sg)

# khung nổi (PIP): người nói thu nhỏ ở góc trong lúc cảnh phụ chiếu toàn màn hình – keys [t, cỡ, X, Y, xoay] theo khung 9:16 (không ép phủ kín)
PIPS = []
for k, p in enumerate(PL.get('pips') or []):
    md = MEDIA[p['media']]
    sg = vseg(p['media'], p['src'], p['t0'], p['t1'], 0.0, [(p['t0'], 1.0, 0.0, 0.0)])
    off = lambda t: int(round((p['src'] + (t - p['t0'])) * S))
    cl = [(t, round(md['S0'] * m, 5), x, y, r) for t, m, x, y, r in p['keys']]
    sg['clip']['scale'] = {'x': cl[0][1], 'y': cl[0][1]}; sg['clip']['transform'] = {'x': cl[0][2], 'y': cl[0][3]}; sg['clip']['rotation'] = cl[0][4]
    ib.add_keyframes(sg, [ib.kf_track('KFTypeScaleX', [(off(c[0]), c[1]) for c in cl]), ib.kf_track('KFTypePositionX', [(off(c[0]), c[2]) for c in cl]),
                          ib.kf_track('KFTypePositionY', [(off(c[0]), c[3]) for c in cl]), ib.kf_track('KFTypeRotation', [(off(c[0]), c[4]) for c in cl])])
    nm, aid, d = B_IN[k % len(B_IN)]; vanim(sg, nm, aid, 'in', min(.35, (p['t1'] - p['t0']) / 3))
    vanim(sg, 'Fade Out', '6798320902548230669', 'out', min(.25, (p['t1'] - p['t0']) / 4))
    PIPS.append(sg)

# transitions (team presets; non-overlap types need no handles)
TRANS_PRESET = {'6952697917563998722': 'transition_glare_ii.json', '6724226861666144779': 'transition_pull_in.json',
                '6724226338418332167': 'transition_pull_out.json', '6987208055511323137': 'transition_flash.json'}
TR_DONE = []
for tr in PL['transitions']:
    blk = ib.load(V3 + '/presets/' + TRANS_PRESET[tr['effect_id']])
    if blk['materials']['transitions'][0].get('is_overlap'): E.append('overlap transition used without handle check'); continue
    i = next((k for k, s in enumerate(BASE) if abs(s['t1'] - tr['at']) < 0.002), None)
    if i is not None and i + 1 < len(BASE):
        m = ib.attach_transition(OUT, V1[i], blk, duration_us=us(tr['dur_s'])); m['path'] = ''; m['request_id'] = ''
        TR_DONE.append(dict(tr, on='A', name=m['name'])); continue
    if LAYER:   # giữa 2 cảnh phụ liền nhau
        j = next((k for k, s in enumerate(PL['bshots'][:-1]) if abs(s['t1'] - tr['at']) < 0.002 and abs(PL['bshots'][k + 1]['t0'] - tr['at']) < 0.002), None)
        if j is not None:
            m = ib.attach_transition(OUT, BSEGS[j], blk, duration_us=us(tr['dur_s'])); m['path'] = ''; m['request_id'] = ''
            TR_DONE.append(dict(tr, on='B', name=m['name'])); continue
        if any(abs(s['t0'] - tr['at']) < 0.002 for s in PL['bshots']): TR_DONE.append(dict(tr, on='B-in (hoạt ảnh vào)')); continue
    E.append('transition %s at %.2f: no cut' % (tr['name'], tr['at']))

# title-behind-presenter sandwich: base V1 / title / matte copy (Xóa nền) of the same clip
MATTE_SEGS, BEHIND = [], []
for mt in PL.get('matte', []):
    i = next(k for k, s in enumerate(PL['shots']) if s['t0'] - 1e-3 <= mt['t0'] and mt['t1'] <= s['t1'] + 1e-3)
    sh = PL['shots'][i]; ks = window([tuple(k) for k in sh['keys']], mt['t0'], mt['t1'])
    src = sh['src'] + (mt['t0'] - sh['t0'])
    sg = vseg(sh['media'], src, mt['t0'], mt['t1'], 0.0, [(mt['t0'], 1.0, 0.0, 0.0)], label='Người dẫn (Xóa nền) - chữ sau người', matting=True)
    apply_motion(sg, sh['media'], ks, mt['t0'], src)
    vanim(sg, 'Fade In', '6798320778182922760', 'in', 0.01)
    MATTE_SEGS.append(sg); BEHIND.append(mt)

# ------------------------------------------------------------------ titles
ANIM_IN = {'BIG': [('6923135604519604737', 'Blur in'), ('6763470111253729803', 'Slide up'), ('7563492973011307793', 'Bubble pop'), ('7314651687149376001', 'Bounce left'),
                   ('7233110260204966402', 'Throw'), ('7594783879685328145', 'Blurry entrance'), ('6724921985282871816', 'Slide down'), ('7576415866514885889', 'Billboard up'),
                   ('7594777244699086081', 'One by one'), ('7509716469614136593', 'Wiping in')],
           'SCR': [('7591713637883071745', 'Plain Fade-In'), ('7145435525799744002', 'Typewriter'), ('7509716469614136593', 'Wiping in')],
           'BEB': [('7563492973011307793', 'Bubble pop'), ('6763470111253729803', 'Slide up'), ('6923135604519604737', 'Blur in'), ('7314651687149376001', 'Bounce left'),
                   ('7576415866514885889', 'Billboard up'), ('7594783879685328145', 'Blurry entrance'), ('7233110260204966402', 'Throw')],
           'ITA': [('7591713637883071745', 'Plain Fade-In'), ('7145435525799744002', 'Typewriter'), ('7594777244699086081', 'One by one'), ('6763470111253729803', 'Slide up')]}
ANIM_OUT = ('6724919382104871427', 'Fade Out')
def add_anim(sg, key, d, k):
    aid, name = ANIM_IN[key][k % len(ANIM_IN[key])]
    din = min(0.4, d * 0.3); dout = min(0.25, d * 0.15)
    a = {'id': U(), 'type': 'sticker_animation', 'multi_language_current': 'none', 'animations': [
        {'anim_adjust_params': None, 'platform': 'all', 'panel': '', 'material_type': 'sticker', 'name': name, 'id': aid, 'type': 'in', 'resource_id': aid,
         'start': 0, 'duration': us(din), 'path': '', 'request_id': '', 'category_id': '', 'category_name': ''},
        {'anim_adjust_params': None, 'platform': 'all', 'panel': '', 'material_type': 'sticker', 'name': ANIM_OUT[1], 'id': ANIM_OUT[0], 'type': 'out',
         'resource_id': ANIM_OUT[0], 'start': us(d - dout), 'duration': us(dout), 'path': '', 'request_id': '', 'category_id': '', 'category_name': ''}]}
    OM.setdefault('material_animations', []).append(a); sg['extra_material_refs'].append(a['id'])

def tmat(text, key, size, fill, shadow):
    text = unicodedata.normalize('NFC', text); f = FONTS[key]
    m = copy.deepcopy(TXT_T); m['id'] = U()
    m.update({'font_path': f['path'], 'font_resource_id': '', 'font_source_platform': 0, 'font_id': '', 'font_name': f['file'][:-4], 'font_title': 'none'})
    rgb, _ = hex2rgba(fill)
    st = {'fill': {'content': {'render_type': 'solid', 'solid': {'color': rgb}}}, 'font': {'path': f['path'], 'id': ''},
          'size': size, 'range': [0, u16(text)], 'useLetterColor': True}
    flag = 7; m.update({'border_color': '', 'border_width': 0.08})
    if shadow:
        col = shadow['color']
        st['shadows'] = [{'thickness_projection_distance': 0, 'diffuse': shadow['diffuse'], 'angle': -45.0, 'thickness_projection_enable': False,
                          'content': {'solid': {'color': col}, 'render_type': 'solid'}, 'distance': shadow['distance'],
                          'thickness_projection_angle': -45, 'alpha': shadow['alpha']}]
        a = math.radians(-45.0)
        m.update({'has_shadow': True, 'shadow_color': '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in col), 'shadow_alpha': shadow['alpha'],
                  'shadow_distance': shadow['distance'], 'shadow_angle': -45.0, 'shadow_smoothing': shadow['diffuse'],
                  'shadow_point': {'x': round(0.6 * math.cos(a), 4), 'y': round(0.6 * math.sin(a), 4)}}); flag |= 32
    m['content'] = json.dumps({'text': text, 'styles': [st]}, ensure_ascii=False, separators=(',', ':'))
    m.update({'text_color': '#' + fill.lstrip('#')[:6].upper(), 'font_size': float(size), 'check_flag': flag, 'global_alpha': 1.0,
              'alignment': 1, 'typesetting': 0, 'line_max_width': 0.82, 'base_content': '', 'letter_spacing': 0.0, 'line_spacing': 0.02,
              'words': {'start_time': [], 'end_time': [], 'text': []}, 'current_words': {'start_time': [], 'end_time': [], 'text': []}})
    OM['texts'].append(m); return m['id']

def line_seg(text, key, cap_pct, cx_pct, cy_pct, t0, t1, fill, shadow, k):
    f = FONTS[key]; em = cap_pct / 100 * H / f['cap']
    bb = f['pf'].getbbox(text); adv = (bb[2] - bb[0]) / 200 * em
    if adv > 0.74 * W: em *= 0.74 * W / adv; adv = 0.74 * W   # safe zone: <= ~69% of width
    size = 15.0
    while adv * (6.02 * size / f['typo']) / em > 0.70 * W and size > 4: size -= 0.5
    scale = round(0.93 * em * f['typo'] / (6.02 * size), 4)
    sg = copy.deepcopy(SEG_T); sg['id'] = U(); sg['material_id'] = tmat(text, key, size, fill, shadow)
    sg['source_timerange'] = None; sg['target_timerange'] = {'start': us(t0), 'duration': us(t1 - t0)}
    sg['clip'] = {'scale': {'x': scale, 'y': scale}, 'rotation': 0.0, 'transform': {'x': round(cx_pct / 50 - 1, 4), 'y': round(1 - cy_pct / 50, 4)},
                  'flip': {'vertical': False, 'horizontal': False}, 'alpha': 1.0}
    sg['extra_material_refs'] = []; sg['keyframe_refs'] = []; sg['common_keyframes'] = []
    add_anim(sg, key, t1 - t0, k)
    return sg, dict(text=text, key=key, x=cx_pct, y=cy_pct, w=adv / W * 100 * 0.93, h=em * f['cap'] / H * 100, fill=fill, t0=t0, t1=t1, shadow=bool(shadow))

def glow(fill):     # owner: keyword glow visible but tasteful -> shadow colour = text colour, alpha 0.5, diffuse 0.3
    rgb, _ = hex2rgba(fill); return {'color': rgb, 'alpha': 0.5, 'diffuse': 0.3, 'distance': 0.0}
SOFT = {'color': [0, 0, 0], 'alpha': 0.32, 'diffuse': 0.18, 'distance': 1.2}
TXs, TREC = [], []
def place_group(lines, t0, t1, cy, k, bright=False):
    gap = 0.07
    hs = [ln[2] / 100 * H / FONTS[ln[1]]['cap'] for ln in lines]
    tot = sum(h * 0.82 for h in hs) + sum(min(a, b) * gap for a, b in zip(hs, hs[1:]))
    y = cy / 100 * H - tot / 2; out = []
    for i, (text, key, cap, fill) in enumerate(lines):
        h = hs[i] * 0.82; yc = (y + h / 2) / H * 100; y += h + (min(hs[i], hs[i + 1]) * gap if i + 1 < len(hs) else 0)
        dark = fill.upper() in ('#0E2F6B', '#C8102E')
        sh = None if dark else (glow(fill) if key in ('BIG', 'BEB') and not bright else SOFT)
        sg, rec = line_seg(text, key, cap, 47.0, yc, t0 + (0.12 * i if i else 0.0), t1, fill, sh, k)
        out.append((sg, rec))
    return out
for k, ti in enumerate(PL['titles']):
    for sg, rec in place_group(ti['lines'], ti['t0'], ti['t1'], ti['y_pct'], ti.get('anim', k), ti.get('bright', False)):
        if ti.get('trk'):   # text rides with the camera move (sits "in" the scene)
            st = sg['target_timerange']['start']; du = sg['target_timerange']['duration']
            x0 = sg['clip']['transform']['x']; y0 = sg['clip']['transform']['y']; s0 = sg['clip']['scale']['x']
            pts = [(max(0, min(du, int(round(t * 1e6)) - st)), dx, dy, sc) for t, dx, dy, sc in ti['trk']]
            ib.add_keyframes(sg, [ib.kf_track('KFTypePositionX', [(o, round(x0 + 2 * dx, 5)) for o, dx, dy, sc in pts]),
                                  ib.kf_track('KFTypePositionY', [(o, round(y0 - 2 * dy, 5)) for o, dx, dy, sc in pts]),
                                  ib.kf_track('KFTypeScaleX', [(o, round(s0 * sc, 5)) for o, dx, dy, sc in pts])])
        TXs.append(sg); TREC.append(dict(rec, line=ti['line']))
BEH_SEGS = []
for mt in BEHIND:
    for sg, rec in place_group([(mt['text'], 'BIG', mt['cap'], mt['fill'])], mt['t0'], mt['t1'], mt['y'], 1):
        BEH_SEGS.append(sg); TREC.append(dict(rec, line='matte'))

# ------------------------------------------------------------------ audio
SPEECH = []
for sp in ([] if LAYER else PL['speech']):
    md = MEDIA[sp['media']]
    mid = amat(md['path'], md['dur'], md['name'])
    SPEECH.append(aseg(mid, sp['src_in'], sp['t0'], sp['t1'] - sp['t0'], sp['vol'], fades=(0.03, 0.06)))
def lin(db): return round(10 ** (db / 20), 4)
SP_IV = [(sp['t0'], sp['t1']) for sp in PL['speech']]
def mus_keys(t0, t1, under, up):
    pts = []
    tt = t0
    while tt <= t1 + 1e-6:
        talking = any(a - 0.15 <= tt <= b + 0.15 for a, b in SP_IV)
        pts.append((round(tt, 3), under if talking else up)); tt += 0.25
    ded = [pts[0]]
    for i in range(1, len(pts)):
        if pts[i][1] != ded[-1][1] or i == len(pts) - 1:
            if pts[i][1] != ded[-1][1]: ded.append((round(pts[i][0] - 0.2, 3), ded[-1][1]))
            ded.append(pts[i])
    return [p for p in ded if t0 <= p[0] <= t1]
MUs = []
for i, mu in enumerate(PL['music']):
    mid = amat(mu['file'] if re.match(r'^[A-Za-z]:/', mu['file']) else AD + '/' + mu['file'], mu['dur'], os.path.basename(mu['file']))   # nhạc AI nằm trong thư mục project (đường dẫn đầy đủ)
    if mu['src_in'] + mu['t1'] - mu['t0'] > mu['dur'] + 1e-3: E.append('music past end %s' % mu['file'])
    MUs.append(aseg(mid, mu['src_in'], mu['t0'], mu['t1'] - mu['t0'], lin(-13), fades=(mu['fi'], mu['fo'])))   # chủ dặn 12/11: nhạc nền LUÔN -13 dB
SFs = []
for sx in PL['sfx']:
    mid = amat(AD + '/' + sx['file'], sx['dur'], sx['file'])
    si = sx.get('src_in', 0.0); d = min(sx['dur'] - si, PL['total'] - sx['t'])
    SFs.append(aseg(mid, si, sx['t'], d, 1.0))   # chủ dặn 11/11: SFX 0 dB

# ------------------------------------------------------------------ effects (team effect ids, global effect track)
FX_SEG_T = ib.load(V3 + '/presets/effect_kb1_bling_aura.json')['segment']
FXs = []
def _clean(o):
    if isinstance(o, dict):
        for k_, v_ in o.items():
            if k_ == 'path' and isinstance(v_, str): o[k_] = ''
            else: _clean(v_)
    elif isinstance(o, list):
        for v_ in o: _clean(v_)
for fx in PL['effects']:
    blk = ib.load(V3 + '/presets/' + fx['preset'])
    m = copy.deepcopy(blk['materials']['video_effects'][0]); m['id'] = U(); m['request_id'] = ''; m['apply_target_type'] = 2; _clean(m)
    OM.setdefault('video_effects', []).append(m)
    sg = copy.deepcopy(FX_SEG_T); sg['id'] = U(); sg['material_id'] = m['id']
    sg['target_timerange'] = {'start': us(fx['t0']), 'duration': us(fx['dur_s'])}
    sg['extra_material_refs'] = []; sg['common_keyframes'] = []; sg['keyframe_refs'] = []; sg['clip'] = None
    FXs.append(sg); fx['name'] = m['name']; fx['effect_id'] = m['effect_id']

# ------------------------------------------------------------------ assemble
def nonover(segs):
    lanes = []
    for s in sorted(segs, key=lambda s: s['target_timerange']['start']):
        st = s['target_timerange']['start']
        for ln in lanes:
            if ln[-1]['target_timerange']['start'] + ln[-1]['target_timerange']['duration'] <= st: ln.append(s); break
        else: lanes.append([s])
    return lanes
TOTAL = PL['total']
tr = [track('video', V1, name='A-roll (người nói, tiếng gốc)' if LAYER else 'V1 hình chính (phim dự án 4K + người dẫn)')]
for k, lane in enumerate(nonover(BSEGS)): tr.append(track('video', lane, flag=2, name='B-roll %d' % (k + 1)))
for lane in nonover(PIPS): tr.append(track('video', lane, flag=2, name='Khung nổi người nói'))
for lane in nonover(ADJ): tr.append(track('adjust', lane, name='Màu từng cảnh'))
for lane in nonover(BEH_SEGS): tr.append(track('text', lane, name='Chữ SAU người dẫn'))
tr.append(track('video', MATTE_SEGS, flag=2, name='Người dẫn bản sao - Xóa nền'))
for k, lane in enumerate(nonover(TXs)): tr.append(track('text', lane, name='Chữ %d' % (k + 1)))
tr.append(track('effect', FXs, name='Hiệu ứng video'))
for lane in nonover(SPEECH): tr.append(track('audio', lane, name='Giọng (người dẫn + VO duyệt)'))
for lane in nonover(MUs): tr.append(track('audio', lane, name='Nhạc nền'))
for lane in nonover(SFs): tr.append(track('audio', lane, name='SFX'))
OUT['tracks'] = tr
for i, t in enumerate(OUT['tracks']):
    for s in t['segments']:
        s['track_render_index'] = i; s['render_index'] = 11000 + i if t['type'] == 'effect' else (14000 + i if t['type'] == 'text' else i)
DRAFT_ID = U(); now = int(time.time())
OUT.update({'id': DRAFT_ID, 'name': PROJECT, 'duration': us(TOTAL), 'create_time': now, 'update_time': now, 'fps': 30.0})
OUT['canvas_config'] = {'ratio': '9:16', 'width': 1080, 'height': 1920, 'background': None}
OUT['platform'] = dict(TPL['platform'], os='windows', os_version='10.0.22631'); OUT['last_modified_platform'] = dict(OUT['platform'])

# ------------------------------------------------------------------ validation
for t in OUT['tracks']:
    segs = sorted(t['segments'], key=lambda s: s['target_timerange']['start'])
    for a, b in zip(segs, segs[1:]):
        if a['target_timerange']['start'] + a['target_timerange']['duration'] > b['target_timerange']['start'] + 1: E.append('overlap on %s' % t['name'])
    for s in segs:
        if s['target_timerange']['start'] + s['target_timerange']['duration'] > us(TOTAL) + 1: E.append('past total on %s' % t['name'])
IDS = {x['id']: x for v in OM.values() if isinstance(v, list) for x in v if isinstance(x, dict) and 'id' in x}
for t in OUT['tracks']:
    for s in t['segments']:
        mat = IDS.get(s['material_id'])
        if mat is None: E.append('missing material %s' % s['material_id']); continue
        for r in s.get('extra_material_refs', []):
            if r not in IDS: E.append('dangling ref')
        if s.get('source_timerange') and mat.get('duration'):
            if s['source_timerange']['start'] + s['source_timerange']['duration'] > mat['duration'] + 2000: E.append('source past media end %s' % mat.get('path', '')[-40:])
            if s['source_timerange']['start'] < 0: E.append('negative source')
PATHS = sorted({m['path'] for k in ('videos', 'audios') for m in OM[k]} | {m['font_path'] for m in OM['texts']})
for p in PATHS:
    if not p.startswith(('C:/Users/Public/MICC Drive/', 'G:/Drive của tôi/PHÒNG TRUYỀN THÔNG MICC/')): E.append('bad path %s' % p)
# text safe area and in-group overlap
for r in TREC:
    x0, x1 = r['x'] - r['w'] / 2, r['x'] + r['w'] / 2; y0, y1 = r['y'] - r['h'] / 2, r['y'] + r['h'] / 2
    if x0 < 6 or x1 > 94 or y0 < 12 or y1 > 78: REP.append('text near edge %s (%.0f-%.0f, %.0f-%.0f)' % (r['text'], x0, x1, y0, y1))
js = json.dumps(OUT, ensure_ascii=False); json.loads(js)
open(OD + '/draft_content.json', 'w', encoding='utf-8').write(js); open(OD + '/draft_info.json', 'w', encoding='utf-8').write(js)
nowus = int(time.time() * S)
meta = {'draft_cover': 'draft_cover.jpg' if PL.get('cover') else '', 'draft_fold_path': '', 'draft_id': DRAFT_ID, 'draft_name': PROJECT, 'draft_root_path': '',
        'draft_removable_storage_device': '', 'draft_new_version': '', 'draft_is_invisible': False, 'draft_timeline_materials_size_': 0,
        'draft_materials': [{'type': i, 'value': []} for i in (0, 1, 2, 3, 6, 7, 8)], 'tm_draft_create': nowus, 'tm_draft_modified': nowus,
        'tm_draft_removed': 0, 'tm_duration': us(TOTAL)}
open(OD + '/draft_meta_info.json', 'w', encoding='utf-8').write(json.dumps(meta, ensure_ascii=False))
json.dump(dict(shots=SHOTREC, texts=TREC, transitions=TR_DONE, effects=PL['effects'], paths=PATHS, errors=E, notes=REP),
          open(PL['out_dir'] + '/build_report.json', 'w'), ensure_ascii=False, indent=1)
print('built', PROJECT, 'dur %.2f' % TOTAL, 'V1', len(V1), 'B', len(BSEGS), 'adjust', len(ADJ), 'matte', len(MATTE_SEGS), 'texts', len(TXs) + len(BEH_SEGS), 'fx', len(FXs), 'trans', len(TR_DONE),
      'speech', len(SPEECH), 'music', len(MUs), 'sfx', len(SFs))
print('paths:'); [print('  ', p) for p in PATHS]
print('ERRORS', E); print('notes', REP)
