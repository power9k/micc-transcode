# Dựng HOÀN TOÀN bằng HyperFrames (không qua CapCut) – bản thử chủ yêu cầu 12/11:
#  cảnh quay gốc (A-roll + cảnh phụ + motion graphic) theo đúng kế hoạch dựng, chữ 3 lớp theo bộ skill (dòng dẫn mềm, cụm khóa đậm glow cùng tông,
#  không viền cứng, bóng mềm 2 lớp), chuyển động chậm mượt, lóe sáng / vệt sáng phim / bụi bokeh, rung nhẹ ở cú nhấn, zoom nhẹ bay bổng.
#  Hình dựng bằng HyperFrames (im lặng) → ghép tiếng gốc + nhạc nền (-13 dB, fade ≥ 3 s) bằng ffmpeg.
import json, os, re, shutil, subprocess, random, html

FK = {'BIG': 'SVN-Nexa Rush Sans Black.ttf', 'BEB': 'UTM Bebas.ttf', 'SCR': 'SVN-Dancing script.ttf', 'ITA': 'SVN-Georgia Italic.ttf'}

def _run(a, timeout=900):
    r = subprocess.run(a, capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError(' '.join(a[:3]) + ': ' + (r.stderr or r.stdout)[-400:])
    return r

def _shot_keys(sh, iw, ih, W, H, s0):   # keyframe (t, m, u, v, r) → (t, scale, x, y) cho thẻ <video> kích thước iw*s0 × ih*s0, gốc 0 0
    out = []
    for k in sh['keys']:
        t, m, u, v = float(k[0]), float(k[1]), float(k[2]), float(k[3])
        dw, dh = iw * s0 * m, ih * s0 * m
        x = min(0.0, max(W - dw, W / 2 - u * dw)); y = min(0.0, max(H - dh, H / 2 - v * dh))
        out.append((round(t - sh['t0'], 3), round(m, 4), round(x, 1), round(y, 1)))
    return out

def render(pl, media_files, music, out, tvc=False, fontdir=None, work=None, log=print, seed='x'):
    """pl = kế hoạch dựng; media_files = {mã media: file video trên máy (đã cắt sẵn theo cảnh: (mã, t0) → file)}; music = [(file, t0, t1, src_in, fi, fo)]"""
    W, H = pl.get('canvas') or (1080, 1920); W, H = int(W), int(H)
    r = random.Random(seed); D = round(float(pl['total']), 2)
    work = work or out + '.d'; shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    here = os.path.dirname(os.path.abspath(__file__)); shutil.copy(os.path.join(here, 'gsap.min.js'), work)
    fd = fontdir or os.path.join(here, 'fonts'); fonts_css = ''
    for k, fn in FK.items():
        p = os.path.join(fd, fn)
        if os.path.exists(p): shutil.copy(p, os.path.join(work, 'f_%s.ttf' % k)); fonts_css += "@font-face{font-family:'F%s';src:url('f_%s.ttf')}" % (k, k)
    lay_a = sorted(pl['shots'], key=lambda s: s['t0'])   # lớp nền = toàn bộ dòng thời gian (cả cảnh phụ ở chỗ lặng / LANG)
    seen_ = {(s['media'], round(s['t0'], 3)) for s in lay_a}
    lay_b = [s for s in (pl.get('bshots') or []) if (s['media'], round(s['t0'], 3)) not in seen_]
    body, js = [], []
    def clip_html(sh, z, idx, kind):
        f = media_files.get((sh['media'], round(sh['t0'], 3)))
        if not f or not os.path.exists(f): return
        md = pl['media'][sh['media']]; iw, ih = float(md.get('w') or W), float(md.get('h') or H)
        try:   # kích thước thật của file đã cắt
            pr = json.loads(_run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', f]).stdout)['streams'][0]
            iw, ih = float(pr['width']), float(pr['height'])
        except Exception: pass
        s0 = max(W / iw, H / ih); nm = 'c%03d.mp4' % idx; shutil.copy(f, os.path.join(work, nm))
        d = round(sh['t1'] - sh['t0'], 3); t0 = round(sh['t0'], 3); ks = _shot_keys(sh, iw, ih, W, H, s0)
        if tvc or kind == 'B':   # chuyển động trôi chậm, bay bổng (thêm 3–5 % zoom nhẹ suốt cảnh)
            m_ = 1.0 + (.05 if tvc else .03); ks = [(t, round(m * (1 + (m_ - 1) * t / max(d, .1)), 4), x, y) for t, m, x, y in ks]
        cid = 'w%03d' % idx
        g = md.get('grade') or {}; gf = lambda k_: float(g.get(k_) or 0)
        filt = 'brightness(%.3f) contrast(%.3f) saturate(%.3f)%s' % (1 + gf('brightness') * .6 + gf('shadow') * .15 + (.05 if tvc else 0), 1 + gf('contrast') * .7, 1 + gf('saturation') * 1.2,
                                                                (' sepia(%.3f)' % min(.25, gf('temperature') * .8)) if gf('temperature') > 0 else '') if g else 'none'
        body.append('<div id="%s" class="cl" style="z-index:%d"><video id="v%s" src="%s" muted playsinline data-start="%.3f" data-duration="%.3f" '
                    'style="position:absolute;left:0;top:0;width:%dpx;height:%dpx;transform-origin:0 0;filter:%s"></video></div>' % (cid, z, cid, nm, t0, d, round(iw * s0), round(ih * s0), filt))
        js.append("tl.set('#%s',{autoAlpha:0},0);" % cid)
        fin = .9 if tvc else (.35 if kind == 'B' else 0)
        if fin and t0 > .05: js.append("tl.fromTo('#%s',{autoAlpha:0,scale:1.04},{autoAlpha:1,scale:1,duration:%.2f,ease:'sine.out'},%.3f);" % (cid, min(fin, d / 3), t0))
        else: js.append("tl.set('#%s',{autoAlpha:1},%.3f);" % (cid, t0))
        js.append("tl.set('#%s',{autoAlpha:0},%.3f);" % (cid, t0 + d + (fin if kind == 'A' else 0)))
        k0 = ks[0]; js.append("tl.set('#v%s',{scale:%s,x:%s,y:%s},%.3f);" % (cid, k0[1], k0[2], k0[3], t0))
        for p, q in zip(ks, ks[1:]):
            dt = q[0] - p[0]
            if dt <= .001: continue
            ease = 'power2.out' if dt < .35 else 'sine.inOut'   # cú giật zoom ngắn → nhanh mà mượt; còn lại trôi chậm
            js.append("tl.to('#v%s',{scale:%s,x:%s,y:%s,duration:%.3f,ease:'%s'},%.3f);" % (cid, q[1], q[2], q[3], dt, ease, t0 + p[0]))
            if dt < .35 and q[1] > p[1] * 1.03:   # cú nhấn → rung nhẹ + lóe sáng mảnh
                js.append("for(let k=0;k<3;k++)tl.to('#%s',{x:(k%%2?5:-5),y:(k%%2?-3:3),duration:.05,yoyo:true,repeat:1,ease:'none'},%.3f+k*.1);" % (cid, t0 + p[0]))
                js.append("tl.fromTo('#flash',{opacity:0},{opacity:.35,duration:.08,yoyo:true,repeat:1,ease:'power1.out'},%.3f);" % (t0 + p[0]))
    i = 0
    for sh in lay_a: clip_html(sh, 1, i, 'A'); i += 1
    for sh in lay_b or []: clip_html(sh, 3, i, 'B'); i += 1
    # lớp chữ
    for j, ti in enumerate(pl.get('titles') or []):
        y = H * float(ti.get('y_pct') or 70) / 100; n = len(ti['lines']); rows = []
        for k, ln in enumerate(ti['lines']):
            tx, fk, cap, col = ln[0], ln[1], float(ln[2] or 5), (ln[3] or '#FFFFFF')
            key = (k == n - 1 and n > 1) or n == 1
            sz = H * cap / 100 * (.95 if W > H else .8)
            glow = '0 0 %dpx %s99, 0 0 %dpx %s55' % (sz * .35, col, sz * .9, col) if (key and not ti.get('bright')) else ''
            sh2 = '0 %dpx %dpx rgba(0,0,0,.45), 0 %dpx %dpx rgba(0,0,0,.25)' % (max(2, sz * .04), max(4, sz * .12), max(4, sz * .1), max(10, sz * .35))
            style = "font-family:'F%s';font-size:%dpx;color:%s;text-shadow:%s;letter-spacing:%s" % (fk, sz, col, ', '.join(x for x in (sh2, glow) if x), '.04em' if fk in ('BIG', 'BEB') else '.01em')
            if key and fk in ('BIG', 'BEB'):   # cụm khóa: chữ gradient cùng tông + vệt sáng quét qua
                style = re.sub(r'text-shadow:[^;]*;', '', style) + ";background:linear-gradient(100deg,%s 0%%,%s 42%%,#FFFFFF 50%%,%s 58%%,%s 100%%);background-size:250%% 100%%;-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;filter:drop-shadow(0 4px 10px rgba(0,0,0,.45))" % (col, col, col, col)
            rows.append('<div class="lw"><span class="ln" style="%s">%s</span></div>' % (style, html.escape(tx)))
        tid = 't%03d' % j; t0, t1 = float(ti['t0']), float(ti['t1'])
        c0 = (ti['lines'][-1][3] or '#FFFFFF').lstrip('#'); lum = sum(int(c0[i_:i_ + 2], 16) * w_ for i_, w_ in ((0, .299), (2, .587), (4, .114))) if len(c0) == 6 else 255
        bdc = 'rgba(255,250,245,.55)' if lum < 110 else 'rgba(0,0,0,%s)' % ('.22' if tvc else '.3')   # chữ tối → nền sáng mềm phía sau; chữ sáng → nền tối mềm
        body.append('<div id="%s" class="tt" style="top:%dpx;--bd:%s">%s</div>' % (tid, y, bdc, ''.join(rows)))
        dur_in = .9 if tvc else .45; slide = 22 if tvc else 14
        js.append("tl.set('#%s',{autoAlpha:0},0);tl.set('#%s',{autoAlpha:1},%.3f);" % (tid, tid, t0))
        js.append("tl.fromTo('#%s .lw',{opacity:0,y:%d,filter:'blur(10px)'},{opacity:1,y:0,filter:'blur(0px)',duration:%.2f,stagger:%.2f,ease:'power2.out'},%.3f);" % (tid, slide, dur_in, .18 if tvc else .1, t0))
        js.append("tl.fromTo('#%s .ln',{backgroundPosition:'100%% 0'},{backgroundPosition:'-50%% 0',duration:%.2f,ease:'sine.inOut'},%.3f);" % (tid, 1.6 if tvc else 1.0, t0 + dur_in * .6))
        if tvc: js.append("tl.fromTo('#%s',{scale:1},{scale:1.035,duration:%.2f,ease:'none'},%.3f);" % (tid, max(.3, t1 - t0), t0))
        js.append("tl.to('#%s',{autoAlpha:0,y:-8,filter:'blur(6px)',duration:%.2f,ease:'power1.in'},%.3f);" % (tid, .5 if tvc else .25, max(t0 + .3, t1 - (.5 if tvc else .25))))
    # lóe sáng / vệt sáng phim ở các chỗ đổi ý (cảnh phụ vào), bụi bokeh cho TVC
    cuts = sorted({round(s['t0'], 2) for s in (lay_b or []) if s['t0'] > .5})
    for c in cuts[::2 if tvc else 3][:14]:
        js.append("tl.fromTo('#leak',{opacity:0,x:%d},{opacity:%.2f,x:%d,duration:.9,ease:'sine.inOut'},%.2f);tl.to('#leak',{opacity:0,duration:.8,ease:'sine.inOut'},%.2f);" % (r.choice([-300, 300]), .75 if tvc else .55, r.choice([-60, 60]), max(0, c - .45), c + .45))
        js.append("tl.fromTo('#flare',{opacity:0,x:-%d},{opacity:.9,x:%d,duration:1.0,ease:'sine.inOut'},%.2f);tl.to('#flare',{opacity:0,duration:.4},%.2f);" % (W, W, max(0, c - .5), c + .5))
    bk = ''
    if tvc:
        bk = ''.join('<div class="bk" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;filter:blur(%dpx)"></div>' % (r.randint(0, W), r.randint(0, H), d, d, d // 3) for d in [r.randint(90, 220) for _ in range(7)])
        js.append("tl.fromTo('.bk',{opacity:0,y:40},{opacity:.28,y:-80,duration:%.2f,stagger:{each:.6,repeat:0},ease:'sine.inOut'},0);" % max(4, D * .6))
    warm = 'rgba(255,214,170,.7)' if tvc else 'rgba(255,190,120,.6)'
    doc = '''<!doctype html><html><head><meta charset="utf-8"><script src="gsap.min.js"></script><style>%(fonts)s
html,body{margin:0;background:#000}#root{position:relative;width:%(W)dpx;height:%(H)dpx;overflow:hidden;background:#000}
.cl{position:absolute;inset:0;overflow:hidden}.tt{position:absolute;left:%(gut)dpx;right:%(gut)dpx;z-index:20;text-align:center;transform:translateY(-50%%);line-height:1.12}
.ln{display:inline-block;white-space:pre-wrap;padding:0 .1em}
.tt::before{content:'';position:absolute;left:10%%;right:10%%;top:-30%%;bottom:-30%%;z-index:-1;background:radial-gradient(ellipse at center,var(--bd),transparent 70%%)}
#leak{position:absolute;inset:-25%%;z-index:15;pointer-events:none;mix-blend-mode:screen;opacity:0;background:radial-gradient(ellipse at 25%% 35%%,%(warm)s,transparent 45%%),radial-gradient(ellipse at 80%% 70%%,rgba(255,170,200,.45),transparent 50%%)}
#flare{position:absolute;left:-10%%;top:%(fy)dpx;width:120%%;height:%(fh)dpx;z-index:16;pointer-events:none;mix-blend-mode:screen;opacity:0;filter:blur(8px);background:linear-gradient(90deg,transparent,rgba(255,255,255,.85),rgba(255,226,190,.6),transparent)}
#flash{position:absolute;inset:0;z-index:17;background:#fff;opacity:0;pointer-events:none;mix-blend-mode:screen}
.bk{position:absolute;z-index:14;border-radius:50%%;pointer-events:none;mix-blend-mode:screen;background:radial-gradient(circle,rgba(255,240,225,.9),transparent 70%%);opacity:0}
#tone{position:absolute;inset:0;z-index:13;pointer-events:none;%(tone)s}
</style></head><body>
<div id="root" data-composition-id="root" data-width="%(W)d" data-height="%(H)d" data-fps="30" data-duration="%(D).2f">
%(body)s<div id="tone"></div>%(bk)s<div id="leak"></div><div id="flare"></div><div id="flash"></div>
</div><script>
const tl=gsap.timeline({paused:true});
%(js)s
tl.to('#root',{opacity:1,duration:.01},%(D1).2f);
window.__timelines=window.__timelines||{};window.__timelines['root']=tl;
</script></body></html>''' % dict(fonts=fonts_css, W=W, H=H, D=D, D1=max(0, D - .02), body='\n'.join(body), bd='.22' if tvc else '.3', js='\n'.join(js), bk=bk, warm=warm,
                                  gut=int(W * .06), fy=int(H * r.uniform(.25, .6)), fh=max(10, H // 90),
                                  tone=('background:linear-gradient(180deg,rgba(255,236,220,.10),rgba(255,255,255,0) 40%%,rgba(255,220,230,.08));mix-blend-mode:soft-light' if tvc else
                                        'background:radial-gradient(ellipse at 50%% 50%%,transparent 60%%,rgba(0,0,0,.28))'))
    open(os.path.join(work, 'index.html'), 'w').write(doc)
    silent = out + '.v.mp4'
    log('  HyperFrames: đang dựng %d cảnh, %d chữ, %.0f s…' % (i, len(pl.get('titles') or []), D))
    subprocess.run(['npx', '--yes', 'hyperframes@0.9.34', 'render', '-q', 'looks', '-o', os.path.abspath(silent)], cwd=work, capture_output=True, text=True, timeout=5400)
    if not os.path.exists(silent) or os.path.getsize(silent) < 20000: raise RuntimeError('HyperFrames dựng lỗi')
    # tiếng: lời gốc (theo kế hoạch) + nhạc nền -13 dB, fade ≥ 3 s
    ins, fl, lab = ['-i', silent], [], []
    for k, sp in enumerate(pl.get('speech') or []):
        f = media_files.get(('aud', sp['media'], round(sp['t0'], 3)))
        if not f: continue
        ins += ['-i', f]; n_ = len(ins) // 2 - 1
        fl.append('[%d:a]volume=%.2f,afade=t=in:d=0.02,adelay=%d|%d[s%d]' % (n_, float(sp.get('vol') or 1), sp['t0'] * 1000, sp['t0'] * 1000, k)); lab.append('[s%d]' % k)
    for k, (f, t0, t1, si, fi, fo) in enumerate(music or []):
        ins += ['-i', f]; n_ = len(ins) // 2 - 1; d = t1 - t0
        fl.append('[%d:a]atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,volume=-13dB,afade=t=in:d=%.2f,afade=t=out:st=%.3f:d=%.2f,adelay=%d|%d[m%d]' % (n_, si, si + d, max(.05, fi), max(0, d - max(.05, fo)), max(.05, fo), t0 * 1000, t0 * 1000, k)); lab.append('[m%d]' % k)
    if lab:
        fl.append('%samix=inputs=%d:normalize=0:duration=longest,atrim=0:%.3f[a]' % (''.join(lab), len(lab), D))
        _run(['ffmpeg', '-y', '-v', 'error'] + ins + ['-filter_complex', ';'.join(fl), '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', out], timeout=1800)
    else: shutil.move(silent, out)
    shutil.rmtree(work, ignore_errors=True)
    try: os.remove(silent)
    except Exception: pass
    return out
