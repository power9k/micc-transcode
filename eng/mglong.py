# -*- coding: utf-8 -*-
"""Motion graphic DÀI cả video (chủ dặn 21/11) – 2 lớp tách riêng cho CapCut:
  • lớp ĐỐI TƯỢNG: chỉ các minh hoạ (số liệu, thẻ ý chính, mốc thời gian, so sánh, vị trí, trích dẫn) – nền trong suốt (ProRes 4444 alpha)
  • lớp NỀN: chính nền của motion graphic đó (tấm kính, quầng sáng, lưới mảnh, bụi sáng) – người dựng bật / tắt / chỉnh riêng
Đối tượng chỉ nằm trong khung 4:3 (1000×750) đặt TRÊN / GIỮA / DƯỚI khung 9:16 tuỳ đoạn (né mặt người nói). Mỗi video 1 phong cách + tông màu riêng: sang, ngầu, hiện đại."""
import os, json, html, random, shutil, subprocess

STYLES = [   # tên, nền1, nền2, nhấn1, nhấn2, chữ, chữ phụ
    ('Gold Noir', '#0b0d12', '#1a1d26', '#e9bf62', '#fff1c6', '#ffffff', '#c9cfdb'),
    ('Emerald Lux', '#05130f', '#0d2a22', '#3ddc97', '#c9f5e2', '#f2fff9', '#a7cfc0'),
    ('Ice Chrome', '#0a0f17', '#16202e', '#9fd3ff', '#ffffff', '#ffffff', '#b8c6d8'),
    ('Royal Violet', '#0e0918', '#21163a', '#b48cff', '#f0e6ff', '#ffffff', '#cbbfe6'),
    ('Crimson Carbon', '#0d0909', '#221313', '#ff5a5f', '#ffd1d2', '#ffffff', '#d6c3c3'),
    ('Teal Neon', '#041214', '#0b2a2e', '#2de2e6', '#d6fbfc', '#ffffff', '#a9cfd2'),
    ('Champagne Navy', '#0a1020', '#14223f', '#f3d9a4', '#ffffff', '#ffffff', '#c4ccdc'),
    ('Copper Slate', '#101214', '#1f2427', '#e08a4f', '#ffe1cc', '#ffffff', '#c9cdd0'),
]
POS = {'top': 170, 'mid': 585, 'bottom': 1000}   # mép trên khung 4:3 (cao 750) trong khung 1080×1920
KINDS = ('so', 'the', 'moc', 'sosanh', 'vitri', 'trich')

def pick_style(recent, rnd):
    names = [s[0] for s in STYLES]; c = [s for s in STYLES if s[0] not in (recent or [])[-4:]] or STYLES
    return rnd.choice(c)

def _e(t): return html.escape(str(t or ''), quote=True)

def _scene(i, sc, st):
    k = sc.get('kind') if sc.get('kind') in KINDS else 'the'; d = sc.get('data') or {}; y = POS.get(sc.get('pos'), POS['bottom']); cid = 'S%d' % i
    fg, bg = '', '<div class="pan" id="%sP" style="top:%dpx"><i class="gl"></i></div>' % (cid, y)
    tt = '<div class="tt">%s</div>' % _e(d.get('tieu_de') or '') if d.get('tieu_de') else ''
    if k == 'so':
        fg = '%s<div class="num"><b data-to="%s">0</b><u>%s</u></div><div class="lb">%s</div><div class="bar"><i></i></div>' % (tt, _e(d.get('so') or 0), _e(d.get('don_vi') or ''), _e(d.get('nhan') or ''))
    elif k == 'the':
        fg = tt + '<div class="ls">' + ''.join('<div class="it"><i></i><span>%s</span></div>' % _e(x) for x in (d.get('y') or [])[:4]) + '</div>'
    elif k == 'moc':
        ms = (d.get('moc') or [])[:4]
        fg = tt + '<div class="tl"><div class="ln"><i></i></div>' + ''.join('<div class="mk" style="left:%d%%"><i></i><b>%s</b><span>%s</span></div>' % (8 + j * 84 // max(1, len(ms) - 1), _e(m.get('nhan') if isinstance(m, dict) else m), _e(m.get('mo_ta') if isinstance(m, dict) else '')) for j, m in enumerate(ms)) + '</div>'
    elif k == 'sosanh':
        a, b = d.get('trai') or {}, d.get('phai') or {}
        fg = tt + '<div class="cp"><div class="cl"><b>%s</b><span>%s</span></div><div class="vs">VS</div><div class="cl hi"><b>%s</b><span>%s</span></div></div>' % (_e(a.get('nhan')), _e(a.get('gia_tri')), _e(b.get('nhan')), _e(b.get('gia_tri')))
    elif k == 'vitri':
        fg = tt + '<div class="loc"><div class="rg"><i></i><i></i><i></i></div><div class="pin"></div>' + ''.join('<div class="dl" style="transform:rotate(%ddeg) translateX(250px) rotate(%ddeg)"><b>%s</b><span>%s</span></div>' % (ang, -ang, _e(x.get('noi') if isinstance(x, dict) else x), _e(x.get('xa') if isinstance(x, dict) else '')) for ang, x in zip((-150, -30, 90, 210), (d.get('ket_noi') or [])[:4])) + '</div>'
    else:
        fg = '<div class="qt"><i>“</i><p>%s</p><span>%s</span></div>' % (_e(d.get('cau') or d.get('tieu_de') or ''), _e(d.get('nguon') or ''))
    return '<div class="sc k-%s" id="%s" style="top:%dpx">%s</div>' % (k, cid, y, fg), bg

def build(scenes, total, style, fontdir_url='F/'):
    n, bg1, bg2, a1, a2, tx, t2 = style
    css = ("@font-face{font-family:H;src:url(%sSVN-Nexa Rush Sans Black.ttf)}@font-face{font-family:S;src:url(%sSVN-Georgia Italic.ttf)}" % (fontdir_url, fontdir_url) +
           ":root{--a1:%s;--a2:%s;--tx:%s;--t2:%s;--b1:%s;--b2:%s}" % (a1, a2, tx, t2, bg1, bg2) + r"""
#root{font-family:'Segoe UI','Noto Sans','DejaVu Sans',Arial,sans-serif;color:var(--tx)}
.sc,.pan{position:absolute;left:40px;width:1000px;height:750px;opacity:0}
.pan{border-radius:44px;background:linear-gradient(160deg,color-mix(in srgb,var(--b2) 82%,transparent),color-mix(in srgb,var(--b1) 88%,transparent));box-shadow:0 0 0 2px color-mix(in srgb,var(--a1) 55%,transparent),0 40px 90px rgba(0,0,0,.55);overflow:hidden}
.pan .gl{position:absolute;inset:-40%;background:conic-gradient(from 0deg,transparent 0 70%,color-mix(in srgb,var(--a1) 30%,transparent) 80%,transparent 90%);animation:none}
.bgw{position:absolute;inset:0;background:radial-gradient(70% 45% at 30% 25%,color-mix(in srgb,var(--a1) 22%,transparent),transparent 70%),radial-gradient(60% 40% at 75% 80%,color-mix(in srgb,var(--a2) 14%,transparent),transparent 70%),linear-gradient(180deg,var(--b1),var(--b2))}
.grid{position:absolute;inset:-200px;background-image:linear-gradient(color-mix(in srgb,var(--a1) 9%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--a1) 9%,transparent) 1px,transparent 1px);background-size:90px 90px}
.dust{position:absolute;width:5px;height:5px;border-radius:50%;background:var(--a2);box-shadow:0 0 12px 4px color-mix(in srgb,var(--a1) 70%,transparent)}
.tt{position:absolute;left:60px;right:60px;top:52px;font:900 54px/1.08 H,sans-serif;letter-spacing:.01em;text-transform:uppercase;background:linear-gradient(180deg,var(--a2),var(--a1));-webkit-background-clip:text;background-clip:text;color:transparent}
.num{position:absolute;left:60px;top:190px;display:flex;align-items:baseline;gap:18px}.num b{font:900 230px/1 H,sans-serif;background:linear-gradient(180deg,var(--a2),var(--a1));-webkit-background-clip:text;background-clip:text;color:transparent}.num u{text-decoration:none;font:800 64px/1 H,sans-serif;color:var(--a1)}
.lb{position:absolute;left:64px;right:60px;top:470px;font:700 46px/1.25 'Segoe UI',Arial,sans-serif;color:var(--tx)}
.bar{position:absolute;left:64px;right:64px;bottom:70px;height:10px;border-radius:9px;background:color-mix(in srgb,var(--tx) 14%,transparent)}.bar i{position:absolute;inset:0;border-radius:9px;background:linear-gradient(90deg,var(--a1),var(--a2));transform-origin:0 50%;transform:scaleX(0)}
.ls{position:absolute;left:60px;right:60px;top:200px;display:flex;flex-direction:column;gap:30px}.it{display:flex;align-items:center;gap:26px;font:700 44px/1.2 'Segoe UI',Arial,sans-serif}.it i{flex:none;width:28px;height:28px;border-radius:8px;transform:rotate(45deg);background:linear-gradient(135deg,var(--a2),var(--a1));box-shadow:0 0 22px color-mix(in srgb,var(--a1) 70%,transparent)}
.tl{position:absolute;left:40px;right:40px;top:330px;height:300px}.tl .ln{position:absolute;left:8%;right:8%;top:40px;height:6px;border-radius:6px;background:color-mix(in srgb,var(--tx) 16%,transparent)}.tl .ln i{position:absolute;inset:0;background:linear-gradient(90deg,var(--a1),var(--a2));transform-origin:0 50%;transform:scaleX(0);border-radius:6px}
.mk{position:absolute;top:0;width:240px;margin-left:-120px;text-align:center}.mk i{display:block;margin:20px auto 22px;width:46px;height:46px;border-radius:50%;background:var(--b1);box-shadow:0 0 0 6px var(--a1),0 0 30px var(--a1)}.mk b{display:block;font:900 46px/1 H,sans-serif;color:var(--a2)}.mk span{display:block;margin-top:10px;font:600 30px/1.2 'Segoe UI',Arial,sans-serif;color:var(--t2)}
.cp{position:absolute;left:50px;right:50px;top:210px;display:flex;align-items:center;gap:26px}.cl{flex:1;height:420px;border-radius:30px;padding:40px 30px;background:color-mix(in srgb,var(--tx) 7%,transparent);box-shadow:inset 0 0 0 2px color-mix(in srgb,var(--tx) 14%,transparent)}.cl.hi{box-shadow:inset 0 0 0 3px var(--a1),0 0 40px color-mix(in srgb,var(--a1) 40%,transparent)}.cl b{display:block;font:800 40px/1.15 'Segoe UI',Arial,sans-serif;color:var(--t2)}.cl span{display:block;margin-top:40px;font:900 76px/1.05 H,sans-serif;color:var(--a2)}.vs{font:900 52px/1 H,sans-serif;color:var(--a1)}
.loc{position:absolute;left:0;right:0;top:110px;height:640px}.rg i{position:absolute;left:50%;top:50%;border-radius:50%;border:2px solid color-mix(in srgb,var(--a1) 60%,transparent);transform:translate(-50%,-50%)}.rg i:nth-child(1){width:180px;height:180px}.rg i:nth-child(2){width:360px;height:360px}.rg i:nth-child(3){width:540px;height:540px}
.pin{position:absolute;left:50%;top:50%;width:54px;height:54px;margin:-27px;border-radius:50%;background:var(--a1);box-shadow:0 0 0 14px color-mix(in srgb,var(--a1) 28%,transparent),0 0 60px 18px var(--a1)}
.dl{position:absolute;left:50%;top:50%;width:280px;margin:-40px -140px;text-align:center}.dl b{display:block;font:800 36px/1.1 'Segoe UI',Arial,sans-serif;color:var(--tx)}.dl span{display:block;margin-top:6px;font:900 32px/1 H,sans-serif;color:var(--a1)}
.qt{position:absolute;left:70px;right:70px;top:120px}.qt i{display:block;font:900 220px/.8 S,serif;font-style:normal;color:var(--a1)}.qt p{margin:0;font:400 62px/1.25 S,serif;color:var(--tx)}.qt span{display:block;margin-top:30px;font:700 34px/1 'Segoe UI',Arial,sans-serif;color:var(--a1);letter-spacing:.12em;text-transform:uppercase}
""")
    fgs, bgs = [], []
    for i, s in enumerate(scenes): f_, b_ = _scene(i, s, style); fgs.append(f_); bgs.append(b_)
    rnd = random.Random(n + str(total))
    dust = ''.join('<i class="dust" style="left:%dpx;top:%dpx;opacity:%.2f" data-v="%.2f"></i>' % (rnd.randint(0, 1080), rnd.randint(0, 1920), rnd.uniform(.25, .8), rnd.uniform(.4, 1.4)) for _ in range(46))
    body_fg = ''.join(fgs)
    body_bg = '<div class="bgw"></div><div class="grid" id="GRID"></div>' + dust + ''.join(bgs)
    js = "const S=%s;" % json.dumps([[round(float(s['s']), 3), round(float(s['e']), 3), s.get('kind') if s.get('kind') in KINDS else 'the'] for s in scenes]) + r"""
const q=(s)=>R.querySelector(s), qa=(s)=>Array.from(R.querySelectorAll(s));
if(q('#GRID')) tl.fromTo('#GRID',{x:0,y:0},{x:90,y:180,duration:D,ease:'none'},0);
qa('.dust').forEach((d,i)=>{const v=+d.dataset.v; tl.to(d,{y:'-='+(220*v),x:'+='+(Math.sin(i)*60),duration:D,ease:'none'},0); tl.to(d,{opacity:.1,duration:1.6,repeat:Math.max(1,Math.floor(D/1.6)),yoyo:true,ease:'sine.inOut'},i*0.07%1.6);});
S.forEach(([s,e,k],i)=>{const id='#S'+i, P=q(id+'P'), C=q(id), d=Math.max(.8,e-s), ti=Math.min(.6,d*.18), to=Math.min(.45,d*.14);
  if(P){tl.fromTo(P,{opacity:0,scale:.92,y:40,rotationX:18,transformPerspective:1200},{opacity:1,scale:1,y:0,rotationX:0,duration:ti,ease:'power3.out'},s);
        tl.to(P,{y:-10,duration:d/2,yoyo:true,repeat:1,ease:'sine.inOut'},s+ti); tl.to(P,{opacity:0,scale:.96,y:-30,duration:to,ease:'power2.in'},e-to);
        const g=P.querySelector('.gl'); if(g) tl.fromTo(g,{rotation:0},{rotation:240,duration:d,ease:'none'},s);}
  if(!C) return; tl.set(C,{opacity:1},s); tl.to(C,{opacity:0,y:-30,filter:'blur(8px)',duration:to,ease:'power2.in'},e-to);
  tl.to(C,{y:-10,duration:d/2,yoyo:true,repeat:1,ease:'sine.inOut'},s+ti);
  const T=C.querySelector('.tt'); if(T) tl.fromTo(T,{opacity:0,y:30,letterSpacing:'.2em'},{opacity:1,y:0,letterSpacing:'.01em',duration:ti+.2,ease:'power3.out'},s+.05);
  if(k==='so'){const b=C.querySelector('.num b'), to_=parseFloat(String(b.dataset.to).replace(',','.'))||0, dec=/[.,]/.test(b.dataset.to)?1:0, o={v:0};
    tl.fromTo(C.querySelector('.num'),{opacity:0,scale:.7},{opacity:1,scale:1,duration:ti+.15,ease:'back.out(1.6)'},s+.1);
    tl.to(o,{v:to_,duration:Math.min(1.4,d*.45),ease:'power2.out',onUpdate:()=>{b.textContent=o.v.toFixed(dec).replace('.',',');}},s+.15);
    tl.fromTo(C.querySelector('.lb'),{opacity:0,x:-40},{opacity:1,x:0,duration:.5,ease:'power3.out'},s+.35);
    tl.to(C.querySelector('.bar i'),{scaleX:1,duration:Math.min(1.6,d*.5),ease:'power2.inOut'},s+.3);}
  if(k==='the') tl.fromTo(C.querySelectorAll('.it'),{opacity:0,x:-60,filter:'blur(6px)'},{opacity:1,x:0,filter:'blur(0px)',duration:.5,stagger:Math.min(.45,(d*.5)/4),ease:'power3.out'},s+.25);
  if(k==='moc'){tl.to(C.querySelector('.ln i'),{scaleX:1,duration:Math.min(2,d*.6),ease:'power1.inOut'},s+.2); tl.fromTo(C.querySelectorAll('.mk'),{opacity:0,y:30},{opacity:1,y:0,duration:.45,stagger:Math.min(.5,(d*.6)/4),ease:'back.out(1.4)'},s+.3);}
  if(k==='sosanh'){const cl=C.querySelectorAll('.cl'); tl.fromTo(cl[0],{opacity:0,x:-80},{opacity:1,x:0,duration:.55,ease:'power3.out'},s+.2); tl.fromTo(cl[1],{opacity:0,x:80},{opacity:1,x:0,duration:.55,ease:'power3.out'},s+.45); tl.fromTo(C.querySelector('.vs'),{opacity:0,scale:2.4},{opacity:1,scale:1,duration:.4,ease:'expo.out'},s+.7);}
  if(k==='vitri'){tl.fromTo(C.querySelectorAll('.rg i'),{scale:.2,opacity:0},{scale:1,opacity:1,duration:.8,stagger:.18,ease:'expo.out'},s+.1); tl.fromTo(C.querySelector('.pin'),{scale:0},{scale:1,duration:.5,ease:'back.out(2)'},s+.2); tl.fromTo(C.querySelectorAll('.dl'),{opacity:0},{opacity:1,duration:.4,stagger:.22},s+.6);}
  if(k==='trich'){tl.fromTo(C.querySelector('.qt i'),{opacity:0,scale:.4},{opacity:1,scale:1,duration:.5,ease:'back.out(1.8)'},s+.1); tl.fromTo(C.querySelector('.qt p'),{opacity:0,y:30,filter:'blur(8px)'},{opacity:1,y:0,filter:'blur(0px)',duration:.8,ease:'power3.out'},s+.3); tl.fromTo(C.querySelector('.qt span'),{opacity:0},{opacity:1,duration:.5},s+.8);}
});
tl.to({}, {duration: D}, 0);
"""
    return css, body_fg, body_bg, js

def render(scenes, total, style, work, out_fg, out_bg, fontdir, log=print):
    import mg as MG
    MG.rm_setup(log); shutil.rmtree(work, ignore_errors=True); pub = os.path.join(work, 'public', 'F'); os.makedirs(pub)
    for f in os.listdir(fontdir):
        if f.lower().endswith(('.ttf', '.otf')): shutil.copy(os.path.join(fontdir, f), pub)
    css, bfg, bbg, js = build(scenes, total, style)
    res = {}
    for nm, body, alpha, out in (('fg', bfg, True, out_fg), ('bg', bbg, False, out_bg)):
        props = os.path.join(work, 'p_%s.json' % nm); json.dump(dict(css=css, body=body, js=js, dur=round(total, 2), alpha=alpha), open(props, 'w'))
        extra = ['--codec=prores', '--prores-profile=4444', '--pixel-format=yuva444p10le', '--image-format=png'] if alpha else ['--codec=h264', '--crf=18']
        r = subprocess.run(['npx', 'remotion', 'render', 'src/index.jsx', 'mgl', os.path.abspath(out), '--props=' + os.path.abspath(props), '--public-dir=' + os.path.join(work, 'public'), '--log=error', '--concurrency=50%'] + extra +
                           (['--browser-executable=' + os.environ['MG_BROWSER']] if os.environ.get('MG_BROWSER') else []), cwd=MG.RM_DIR, capture_output=True, text=True, timeout=3600)
        if not os.path.exists(out) or os.path.getsize(out) < 10000: raise RuntimeError('motion graphic dài (%s) lỗi: %s' % (nm, (r.stderr or r.stdout)[-400:]))
        if alpha:   # ProRes 4444 rất nặng → đổi sang MOV mã PNG (giữ kênh trong suốt, nhẹ ~6 lần)
            tmp = out + '.png.mov'; r2 = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', out, '-an', '-c:v', 'png', '-pix_fmt', 'rgba', tmp], capture_output=True, text=True, timeout=1800)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 10000: os.replace(tmp, out)
        res[nm] = out
    return res
