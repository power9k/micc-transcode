# Motion graphic (HyperFrames) cho bản dựng CapCut – chủ dặn 11–12/11:
#  - đồ họa sinh động KHÔNG CHỮ (chữ làm trên CapCut); KẾT HỢP cảnh quay gốc: cảnh được cắt bằng MẶT NẠ (tròn, lục giác, vòm, chéo,
#    tách đôi, dải phim…) và bố trí hài hòa với đồ họa
#  - giữ tông màu web MICC (nền xanh than, vàng kim) nhưng họa tiết / bố cục / chuyển động PHẢI KHÁC NHAU giữa các clip (mỗi clip
#    phối ngẫu nhiên: nền × mặt nạ × bố cục × kiểu xuất hiện × chi tiết trang trí)
#  - mỗi clip lưu trong CHÍNH thư mục project
import json, os, shutil, subprocess, hashlib, random

W, H = 1080, 1920
K = ['#050914', '#090e1c', '#0d1426', '#131c32', '#1a2744']   # nền web --k0..k3 (+1 sáng hơn)
G = {'g1': '#d6b262', 'g2': '#f0d08a', 'g3': '#f4e2b4', 'g4': '#967632', 'g5': '#b08c3e', 'g6': '#f7e8c4'}
LOAI = {
    'ban_do': 'bản đồ / vị trí / kết nối: lưới bản đồ, ghim rơi, sóng lan, đường đi vẽ dần qua nhiều điểm, cảnh dự án trong mặt nạ',
    'khu_3d': 'khu nhà / tòa tháp 3D mọc lên trên sàn xoay (quy mô, siêu dự án, mật độ, số tòa)',
    'tang_truong': 'biểu đồ cột / đường tăng + mũi tên lên, đồng xu (giá tăng, sinh lời, lãi, tiềm năng)',
    'giam': 'biểu đồ giảm dần + mũi tên xuống (lãi suất, rủi ro, chi phí giảm, hàng còn ít)',
    'luoi_can': 'lưới ô căn hộ sáng dần hoặc tắt dần (số căn, bán hết, còn lại bao nhiêu, giỏ hàng)',
    'dien_thoai': 'điện thoại chứa cảnh, thẻ kết quả trượt ra (app, AI, tìm căn, mạng xã hội, công nghệ)',
    'dem_nguoc': 'vòng đếm ngược / đồng hồ quét quanh cảnh trong mặt nạ tròn (thời gian, 3 giây, 30 giây, hạn chót, nhanh)',
    'phieu_loc': 'phễu lọc: nhiều thẻ rơi vào phễu, ra 1 cảnh sáng (lọc nhu cầu, chọn đúng, sàng lọc)',
    'so_sanh': 'chia đôi màn hình 2 cảnh trong 2 mặt nạ, vạch phân cách vàng quét qua (so sánh trước/sau, A với B, nội thành vs ngoại thành)',
    'mat_bang': 'bản vẽ mặt bằng kiến trúc tự vẽ nét (sơ đồ căn, thiết kế, công năng, diện tích)',
    'tien': 'chồng tiền / đồng xu dâng lên + vòng sáng (giá, vốn, tỷ đồng, thanh toán, chiết khấu)',
    'vong_so': 'vòng phần trăm chạy quanh cảnh trong mặt nạ tròn (tỷ lệ %, hỗ trợ vay, cam kết, lấp đầy)',
    'khung_hinh': 'cảnh quay tràn màn hình hiện ra qua mặt nạ quét + khung hình học vàng, tia sáng (minh họa sang trọng, mở đầu, cao trào)',
    'the_anh': 'cảnh đẹp trong thẻ 3D xoay vào, bụi sáng (minh họa chung)',
}

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><script src="gsap.min.js"></script><style>
html,body{margin:0;background:#000}#root{position:relative;width:1080px;height:1920px;overflow:hidden;background:%(k0)s}
.bg{position:absolute;inset:-200px;background:%(bgfill)s}
.pat{position:absolute;inset:-300px;opacity:%(patop)s;background:%(pat)s}
.mask{position:absolute;overflow:hidden;background:%(k3)s}.mask video{width:100%%;height:100%%;object-fit:cover;display:block}
.frame{position:absolute;pointer-events:none}
.spark{position:absolute;width:9px;height:9px;border-radius:50%%;background:%(g6)s;box-shadow:0 0 16px 6px %(g1)s}
.bar{position:absolute;width:118px;border-radius:16px 16px 0 0;background:linear-gradient(%(g3)s,%(g5)s);transform-origin:50%% 100%%}
.coin{position:absolute;width:150px;height:44px;border-radius:50%%;background:linear-gradient(%(g6)s,%(g1)s 60%%,%(g4)s);box-shadow:0 0 0 5px %(g5)s inset,0 10px 24px rgba(0,0,0,.45)}
.stage{position:absolute;left:0;top:0;width:1080px;height:1920px;perspective:2200px}
.floor{position:absolute;left:60px;top:780px;width:960px;height:960px;transform-style:preserve-3d;transform:rotateX(62deg) rotateZ(-35deg);background:linear-gradient(rgba(240,208,138,.2) 2px,transparent 2px) 0 0/90px 90px,linear-gradient(90deg,rgba(240,208,138,.2) 2px,transparent 2px) 0 0/90px 90px,radial-gradient(%(k4)s,%(k0)s)}
.bld{position:absolute;transform-style:preserve-3d}.bld i{position:absolute;display:block;backface-visibility:hidden}
.cell{position:absolute;border-radius:14px;background:%(k3)s;box-shadow:0 0 0 3px rgba(214,178,98,.35) inset}.cell i{position:absolute;inset:0;border-radius:14px;background:linear-gradient(%(g3)s,%(g1)s);box-shadow:0 0 24px %(g1)s;opacity:0}
.phone{position:absolute;width:560px;height:1140px;border-radius:78px;background:%(k1)s;box-shadow:0 0 0 14px %(g4)s,0 0 0 20px %(g1)s,0 60px 140px rgba(0,0,0,.7)}
.phone .mask{left:26px;top:26px;right:26px;bottom:26px;border-radius:56px}
.res{position:absolute;width:470px;height:140px;border-radius:28px;background:linear-gradient(90deg,%(k3)s,%(k4)s);box-shadow:0 0 0 4px %(g1)s,0 20px 50px rgba(0,0,0,.5)}
.res b{position:absolute;left:22px;top:20px;width:100px;height:100px;border-radius:20px;background:linear-gradient(%(g3)s,%(g5)s)}
.res u{position:absolute;left:146px;height:16px;border-radius:8px;background:rgba(244,226,180,.55)}
</style></head><body>
<div id="root" data-composition-id="root" data-width="1080" data-height="1920" data-fps="30" data-duration="%(dur)s">
<div class="bg"></div><div class="pat" id="pat"></div>
%(body)s
</div>
<script>
const D=%(dur)s, tl=gsap.timeline({paused:true}), R=document.getElementById('root');
tl.to('#pat',%(patmove)s,0);
function sparks(n,y0,h){for(let i=0;i<n;i++){const s=document.createElement('div');s.className='spark';s.style.left=(60+((i*137)%%960))+'px';s.style.top=(y0+((i*71)%%(h||300)))+'px';R.appendChild(s)}
 tl.fromTo('.spark',{y:0,opacity:0,scale:.4},{y:-700,opacity:1,scale:1,duration:Math.max(1.5,D-.8),stagger:.05,ease:'power1.out'},.3)}
%(enter)s
%(js)s
tl.to('#root',{opacity:1,duration:.01},D-.01);
window.__timelines=window.__timelines||{};window.__timelines['root']=tl;
</script></body></html>'''

# ---- nền (họa tiết khác nhau, cùng tông web)
def _bg(r):
    c = r.choice([
        ('radial-gradient(ellipse at 50%% 30%%,%s 0%%,%s 45%%,%s 100%%)' % (K[4], K[2], K[0]),
         'repeating-radial-gradient(circle at 30%% 40%%,transparent 0 38px,%s 39px 41px,transparent 42px 80px),repeating-radial-gradient(circle at 75%% 70%%,transparent 0 52px,%s 53px 55px,transparent 56px 110px)' % (G['g2'], G['g2']), .13),
        ('linear-gradient(160deg,%s,%s 55%%,%s)' % (K[3], K[1], K[0]),
         'repeating-linear-gradient(45deg,transparent 0 46px,%s 46px 48px)' % G['g4'], .22),
        ('radial-gradient(circle at 80%% 20%%,%s,%s 60%%)' % (K[4], K[0]),
         'radial-gradient(%s 3px,transparent 4px) 0 0/48px 48px' % G['g5'], .35),
        ('linear-gradient(%s,%s)' % (K[2], K[0]),
         'linear-gradient(%s 1px,transparent 1px) 0 0/60px 60px,linear-gradient(90deg,%s 1px,transparent 1px) 0 0/60px 60px,linear-gradient(%s 2px,transparent 2px) 0 0/300px 300px,linear-gradient(90deg,%s 2px,transparent 2px) 0 0/300px 300px' % (('rgba(240,208,138,.18)',) * 2 + ('rgba(240,208,138,.35)',) * 2), 1),
        ('radial-gradient(ellipse at 50%% 100%%,%s,%s 70%%)' % (K[4], K[0]),
         'repeating-conic-gradient(from 0deg at 50%% 110%%,transparent 0 6deg,%s 6deg 7deg)' % G['g4'], .25),
        ('linear-gradient(200deg,%s,%s)' % (K[1], K[0]),
         'radial-gradient(circle at 20%% 30%%,rgba(214,178,98,.35),transparent 30%%),radial-gradient(circle at 80%% 70%%,rgba(240,208,138,.25),transparent 35%%),radial-gradient(circle at 60%% 10%%,rgba(150,118,50,.3),transparent 25%%)', 1),
    ])
    mv = r.choice(['{x:120,y:-160,rotation:6,duration:D,ease:"none"}', '{x:-140,y:90,duration:D,ease:"none"}', '{scale:1.15,rotation:-4,duration:D,ease:"none"}', '{y:-220,duration:D,ease:"none"}'])
    return c[0], c[1], c[2], mv

# ---- mặt nạ cắt cảnh quay (hình dạng + khung trang trí)
MASKS = ['round', 'circle', 'hex', 'arch', 'diag', 'blob', 'pill', 'film']
def _mask(shape, x, y, w, h, vid, mid='m1'):
    clip = {'round': 'inset(0 round 46px)', 'circle': 'circle(50% at 50% 50%)', 'hex': 'polygon(25% 3%,75% 3%,100% 50%,75% 97%,25% 97%,0 50%)',
            'arch': 'inset(0 round 50% 50% 28px 28px)', 'diag': 'polygon(0 8%,100% 0,100% 92%,0 100%)',
            'blob': 'polygon(8% 18%,30% 2%,62% 6%,92% 20%,98% 52%,86% 84%,56% 98%,22% 92%,4% 66%)', 'pill': 'inset(0 round 999px)',
            'film': 'inset(0 round 10px)'}[shape]
    out = '<div class="mask" id="%s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;clip-path:%s">%s</div>' % (mid, x, y, w, h, clip, vid)
    # khung vàng bám theo hình mặt nạ (SVG)
    if shape in ('circle',):
        out += '<svg class="frame" id="%sf" style="left:%dpx;top:%dpx" width="%d" height="%d"><circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="8"/><circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="3" stroke-dasharray="6 18" opacity=".8"/></svg>' % (
            mid, x - 30, y - 30, w + 60, h + 60, w / 2 + 30, h / 2 + 30, min(w, h) / 2 + 4, G['g1'], w / 2 + 30, h / 2 + 30, min(w, h) / 2 + 24, G['g2'])
    elif shape == 'hex':
        pts = ' '.join('%d,%d' % (30 + px * w / 100, 30 + py * h / 100) for px, py in ((25, 3), (75, 3), (100, 50), (75, 97), (25, 97), (0, 50)))
        out += '<svg class="frame" id="%sf" style="left:%dpx;top:%dpx" width="%d" height="%d"><polygon points="%s" fill="none" stroke="%s" stroke-width="8" stroke-linejoin="round"/></svg>' % (mid, x - 30, y - 30, w + 60, h + 60, pts, G['g1'])
    elif shape == 'film':
        holes = ''.join('<rect x="%d" y="%d" width="26" height="18" rx="4" fill="%s"/><rect x="%d" y="%d" width="26" height="18" rx="4" fill="%s"/>' % (14 + i * 56, 10, K[0], 14 + i * 56, h + 42, K[0]) for i in range(int(w / 56) + 1))
        out = '<svg class="frame" id="%sb" style="left:%dpx;top:%dpx" width="%d" height="%d"><rect x="0" y="0" width="%d" height="%d" rx="14" fill="%s"/>%s</svg>' % (mid, x, y - 40, w, h + 80, w, h + 80, G['g5'], holes) + out
    else:
        rr = {'round': 46, 'arch': 28, 'diag': 0, 'blob': 0, 'pill': min(w, h) / 2}.get(shape, 40)
        if shape in ('round', 'arch', 'pill'):
            out += '<div class="frame" id="%sf" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:%s;box-shadow:0 0 0 6px %s,0 0 70px rgba(214,178,98,.45)"></div>' % (
                mid, x, y, w, h, ('%dpx' % rr) if shape != 'arch' else '%dpx %dpx 28px 28px' % (w / 2, w / 2), G['g1'])
        else:   # chéo / khối hữu cơ: 2 vạch vàng chạy dọc mép
            out += '<svg class="frame" id="%sf" style="left:%dpx;top:%dpx" width="%d" height="%d"><line x1="0" y1="%d" x2="%d" y2="0" stroke="%s" stroke-width="10"/><line x1="0" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="4"/></svg>' % (
                mid, x, y - 20, w, h + 40, h * .08 + 20, w, G['g2'], h + 20, w, h * .92 + 20, G['g1'])
    return out

def _decor(r):   # lớp chi tiết tỉ mỉ (2–4 chi tiết ngẫu nhiên / clip): thước đo, góc khung, vòng mảnh, chấm sáng, đường quét, tia sáng
    out, js = '', ''
    pick = r.sample(['ruler', 'corners', 'rings', 'dots', 'sweep', 'rays', 'hud', 'orbits'], r.randint(2, 4))
    if 'ruler' in pick:
        x = r.choice([28, 1030])
        out += '<svg class="frame dc" id="dc_r" style="left:%dpx;top:200px" width="24" height="1520">%s</svg>' % (x, ''.join('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2" opacity=".7"/>' % (i * 20, 24 if i % 5 == 0 else 10, i * 20, G['g2']) for i in range(77)))
        js += "tl.fromTo('#dc_r',{scaleY:0,transformOrigin:'50% 0'},{scaleY:1,duration:1.2,ease:'power2.out'},.1);"
    if 'corners' in pick:
        out += ''.join('<div class="frame dc_c" style="left:%dpx;top:%dpx;width:70px;height:70px;border-%s:4px solid %s;border-%s:4px solid %s;opacity:.8"></div>' % (x, y, a, G['g2'], b, G['g2']) for x, y, a, b in ((24, 24, 'top', 'left'), (986, 24, 'top', 'right'), (24, 1826, 'bottom', 'left'), (986, 1826, 'bottom', 'right')))
        js += "tl.fromTo('.dc_c',{scale:1.6,opacity:0},{scale:1,opacity:.8,duration:.6,stagger:.06,ease:'power3.out'},.2);"
    if 'rings' in pick:
        cx, cy = r.choice([(160, 300), (920, 360), (180, 1600), (900, 1650)])
        out += '<svg class="frame" id="dc_g" style="left:%dpx;top:%dpx" width="300" height="300"><circle cx="150" cy="150" r="140" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="4 10"/><circle cx="150" cy="150" r="100" fill="none" stroke="%s" stroke-width="1.5"/><circle cx="150" cy="150" r="60" fill="none" stroke="%s" stroke-width="3" stroke-dasharray="40 20"/></svg>' % (cx - 150, cy - 150, G['g2'], G['g4'], G['g1'])
        js += "tl.fromTo('#dc_g',{rotation:0,opacity:0},{rotation:%d,opacity:.9,duration:D,ease:'none'},0);" % r.choice([90, -90, 180])
    if 'dots' in pick:
        out += ''.join('<div class="frame dc_d" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;border-radius:50%%;background:%s;opacity:.0"></div>' % (r.randint(40, 1040), r.randint(80, 1860), sz, sz, G['g3']) for sz in [r.choice([4, 6, 8]) for _ in range(26)])
        js += "tl.to('.dc_d',{opacity:.7,duration:.4,stagger:{each:.04,repeat:-1,yoyo:true}},.2);"
    if 'sweep' in pick:
        out += '<div class="frame" id="dc_s" style="left:-200px;top:0;width:180px;height:1920px;background:linear-gradient(90deg,transparent,rgba(247,232,196,.16),transparent);transform:skewX(-14deg)"></div>'
        js += "tl.fromTo('#dc_s',{x:0},{x:1500,duration:1.4,ease:'power2.inOut'},%.2f);" % r.uniform(.6, 1.6)
    if 'rays' in pick:
        out += '<div class="frame" id="dc_y" style="left:-460px;top:%dpx;width:2000px;height:2000px;background:repeating-conic-gradient(from 0deg,rgba(240,208,138,.08) 0 3deg,transparent 3deg 14deg)"></div>' % r.choice([-1400, 700])
        js += "tl.fromTo('#dc_y',{rotation:0},{rotation:%d,duration:D,ease:'none'},0);" % r.choice([25, -25])
    if 'hud' in pick:
        y = r.choice([120, 1760])
        out += '<svg class="frame" id="dc_h" style="left:60px;top:%dpx" width="960" height="40"><line x1="0" y1="20" x2="960" y2="20" stroke="%s" stroke-width="2" opacity=".6"/>%s</svg>' % (y, G['g2'], ''.join('<rect x="%d" y="12" width="%d" height="16" rx="3" fill="%s" opacity=".85"/>' % (x, w, G['g1']) for x, w in ((r.randint(0, 200), 60), (r.randint(380, 560), 30), (r.randint(760, 900), 50))))
        js += "tl.fromTo('#dc_h',{scaleX:0,transformOrigin:'0 50%'},{scaleX:1,duration:.9,ease:'power3.out'},.3);"
    if 'orbits' in pick:
        out += '<svg class="frame" id="dc_o" style="left:90px;top:%dpx" width="900" height="900"><ellipse cx="450" cy="450" rx="430" ry="150" fill="none" stroke="%s" stroke-width="2" opacity=".5"/><circle id="dc_ob" cx="880" cy="450" r="12" fill="%s"/></svg>' % (r.choice([300, 900]), G['g2'], G['g6'])
        js += "tl.fromTo('#dc_o',{rotation:-20,opacity:0},{rotation:15,opacity:1,duration:D,ease:'none',svgOrigin:'450 450'},0);"
    return out, js

def _enter(r, sel):   # kiểu xuất hiện của khối chính (mặt nạ / thẻ)
    return r.choice([
        "tl.fromTo('%s',{rotationY:-70,rotationX:12,scale:.6,opacity:0,y:200},{rotationY:0,rotationX:0,scale:1,opacity:1,y:0,duration:1,ease:'power3.out'},0);" % sel,
        "tl.fromTo('%s',{clipPath:'inset(50%% 50%% 50%% 50%% round 40px)'},{clipPath:'inset(0%% 0%% 0%% 0%% round 40px)',duration:.9,ease:'power3.inOut'},0);" % sel,
        "tl.fromTo('%s',{x:-1200,rotation:-6},{x:0,rotation:0,duration:.9,ease:'expo.out'},0);" % sel,
        "tl.fromTo('%s',{x:1200,rotation:6},{x:0,rotation:0,duration:.9,ease:'expo.out'},0);" % sel,
        "tl.fromTo('%s',{scale:0,opacity:0},{scale:1,opacity:1,duration:.8,ease:'back.out(1.7)'},0);" % sel,
        "tl.fromTo('%s',{y:1500},{y:0,duration:1,ease:'power4.out'},0);" % sel,
    ])

def _vid(clip, dur):
    if not clip: return ''
    if clip.lower().endswith('.jpg'): return '<img id="v1" src="clip.jpg" style="width:100%;height:100%;object-fit:cover;display:block">'   # ảnh tĩnh (video bị chặn tải) – vẫn trôi / zoom
    return '<video id="v1" src="clip.mp4" muted playsinline data-start="0" data-duration="%s"></video>' % dur

def scene(loai, dur, clip, n, r):
    v = _vid(clip, dur); js = ''; body = ''
    shape = r.choice(MASKS)
    lay = r.choice(['top', 'center', 'left', 'right'])
    def box(wh_w, wh_h, ytop=None):
        if lay == 'left': return 40, ytop if ytop is not None else 300, wh_w, wh_h
        if lay == 'right': return 1080 - 40 - wh_w, ytop if ytop is not None else 300, wh_w, wh_h
        return (1080 - wh_w) // 2, ytop if ytop is not None else (180 if lay == 'top' else 420), wh_w, wh_h
    spin = "tl.to('#m1f',{rotation:%d,duration:D,ease:'none',transformOrigin:'50%% 50%%'},0);" % r.choice([20, -20, 40, -40]) if shape in ('circle', 'hex') else ''
    drift = "tl.to('#v1',{scale:1.18,duration:D,ease:'none'},0);"
    if loai == 'ban_do':
        x, y, w, h = box(660 if shape in ('circle', 'hex') else 760, 660 if shape in ('circle', 'hex') else 880, 160)
        pins = [(r.randint(160, 920), r.randint(1180, 1700)) for _ in range(3)]
        path = 'M%d %d ' % (x + w // 2, y + h - 40) + ' '.join('Q %d %d %d %d' % ((px + x + w // 2) // 2 + r.randint(-140, 140), (py + y + h) // 2, px, py) for px, py in pins)
        body = ('<div class="frame" style="left:0;top:1080px;width:1080px;height:840px;background:linear-gradient(rgba(240,208,138,.14) 2px,transparent 2px) 0 0/80px 80px,linear-gradient(90deg,rgba(240,208,138,.14) 2px,transparent 2px) 0 0/80px 80px;transform:perspective(900px) rotateX(48deg);transform-origin:50% 0"></div>'
                + _mask(shape, x, y, w, h, v) + '<svg class="frame" style="left:0;top:0" width="1080" height="1920"><path id="route" d="%s" fill="none" stroke="%s" stroke-width="10" stroke-dasharray="24 18" stroke-linecap="round"/>' % (path, G['g2'])
                + ''.join('<g id="p%d"><circle cx="%d" cy="%d" r="26" fill="%s"/><circle cx="%d" cy="%d" r="11" fill="%s"/></g><circle id="w%d" cx="%d" cy="%d" r="30" fill="none" stroke="%s" stroke-width="5"/>' % (i, px, py, G['g1'], px, py, K[1], i, px, py, G['g2']) for i, (px, py) in enumerate(pins)) + '</svg>')
        js = (_enter(r, '#m1') + "tl.fromTo('#m1f',{opacity:0},{opacity:1,duration:.5},.5);" + spin + drift +
              "const rt=document.getElementById('route'),L=rt.getTotalLength();tl.fromTo('#route',{strokeDashoffset:L},{strokeDashoffset:0,duration:Math.max(1,D-1.6),ease:'power1.inOut'},.9);" +
              ''.join("tl.fromTo('#p%d',{scale:0,transformOrigin:'50%% 50%%'},{scale:1,duration:.35,ease:'back.out(2.5)'},%s);tl.fromTo('#w%d',{scale:.3,opacity:1,transformOrigin:'50%% 50%%'},{scale:3,opacity:0,duration:1},%s);" % (i, '%.2f' % (1.0 + i * (dur - 1.8) / 3), i, '%.2f' % (1.1 + i * (dur - 1.8) / 3)) for i in range(3)))
    elif loai == 'khu_3d':
        body = '<div class="stage"><div class="floor" id="floor"></div></div>'
        if clip: x, y, w, h = box(560, 420 if shape not in ('circle', 'hex') else 520, 140); body += _mask(shape, x, y, w, h, v)
        rows = [[r.randint(1, 7), r.randint(1, 7), r.randint(2, 8)] for _ in range(r.randint(8, 13))]
        js = ("const fl=document.getElementById('floor');const B=%s,C=['%s','%s','%s','%s','#e7c77e'];const bl=[];"
              "B.forEach(([gx,gy,h],k)=>{const w=%d,Hh=h*70,d=document.createElement('div');d.className='bld';d.style.cssText=`left:${gx*95}px;top:${gy*95}px;width:${w}px;height:${w}px;`;const c=C[k%%5];"
              "const sh=f=>`linear-gradient(rgba(0,0,0,${f}),rgba(0,0,0,${f})),repeating-linear-gradient(90deg,transparent 0 22px,rgba(9,14,28,.45) 22px 34px),repeating-linear-gradient(transparent 0 26px,rgba(255,255,255,.25) 26px 30px),${c}`;"
              "[[`width:${w}px;height:${Hh}px;transform:rotateX(-90deg) translateY(${-Hh}px);transform-origin:0 0;`,.05],[`width:${w}px;height:${Hh}px;transform:translateY(${w}px) rotateX(-90deg) translateY(${-Hh}px);transform-origin:0 0;`,.18],[`width:${Hh}px;height:${w}px;transform:rotateY(90deg);transform-origin:0 0;`,.3],[`width:${Hh}px;height:${w}px;transform:translateX(${w}px) rotateY(90deg);transform-origin:0 0;`,.12]].forEach(([css,f])=>{const i=document.createElement('i');i.style.cssText=css+`background:${sh(f)}`;d.appendChild(i)});"
              "const rf=document.createElement('i');rf.style.cssText=`width:${w}px;height:${w}px;transform:translateZ(${Hh}px);background:%s;box-shadow:0 0 30px %s`;d.appendChild(rf);fl.appendChild(d);bl.push(d)});"
              "tl.fromTo('#floor',{rotationZ:%d,scale:.7},{rotationZ:%d,scale:1.05,duration:D,ease:'power1.inOut'},0);bl.forEach((b,k)=>tl.fromTo(b.children,{scaleY:0,opacity:0},{scaleY:1,opacity:1,duration:.6,ease:'back.out(1.6)'},.3+k*Math.min(.16,(D-1.2)/B.length)));sparks(20,1450,350);"
              % (json.dumps(rows), G['g3'], G['g2'], G['g6'], G['g1'], r.choice([120, 140, 160]), G['g6'], G['g2'], r.choice([-60, 20]), r.choice([-15, 50]))) + (_enter(r, '#m1') + drift if clip else '')
    elif loai in ('tang_truong', 'giam'):
        up = loai == 'tang_truong'; nb = r.choice([4, 5, 6]); base = r.choice([380, 420])
        hs = sorted(r.sample(range(160, 680, 40), nb), reverse=not up)
        bw = 760 // nb; xs = [160 + i * bw for i in range(nb)]
        if clip: x, y, w, h = box(820 if lay in ('top', 'center') else 560, 560, 130); body += _mask(shape, x, y, w, h, v)
        style = r.choice(['bars', 'line', 'both'])
        if style in ('bars', 'both'): body += ''.join('<div class="bar" id="b%d" style="left:%dpx;bottom:%dpx;width:%dpx;height:%dpx"></div>' % (i, xs[i], base, bw - 34, h_) for i, h_ in enumerate(hs))
        pts = [(xs[i] + (bw - 34) // 2, 1920 - base - hs[i] - 30) for i in range(nb)]
        body += '<svg class="frame" style="left:0;top:0" width="1080" height="1920"><path id="arrow" d="M%s" fill="none" stroke="%s" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>%s</svg>' % (
            ' L'.join('%d %d' % p for p in pts), G['g6'], ''.join('<circle id="d%d" cx="%d" cy="%d" r="16" fill="%s"/>' % (i, px, py, G['g2']) for i, (px, py) in enumerate(pts)))
        body += ''.join('<div class="coin" id="k%d" style="left:%dpx;top:%dpx"></div>' % (i, r.choice([60, 870]), 1700 - i * 38) for i in range(r.randint(3, 6)))
        js = ((_enter(r, '#m1') + drift) if clip else '') + (
            "for(let k=0;k<%d;k++)tl.fromTo('#b'+k,{scaleY:0},{scaleY:1,duration:.55,ease:'back.out(1.4)'},.4+k*.12);" % nb if style in ('bars', 'both') else '') + (
            "const ar=document.getElementById('arrow'),L=ar.getTotalLength();ar.style.strokeDasharray=L;tl.fromTo('#arrow',{strokeDashoffset:L},{strokeDashoffset:0,duration:1.2,ease:'power2.inOut'},.9);"
            "for(let k=0;k<%d;k++)tl.fromTo('#d'+k,{scale:0,transformOrigin:'50%% 50%%'},{scale:1,duration:.3,ease:'back.out(3)'},.9+k*1.2/%d);" % (nb, nb) +
            "tl.fromTo('.coin',{y:400,opacity:0},{y:0,opacity:1,duration:.5,stagger:.08,ease:'back.out(1.6)'},1.2);")
    elif loai == 'luoi_can':
        cols = r.choice([5, 6, 7]); rows = r.choice([6, 7, 8]); cw = (960 - (cols - 1) * 18) // cols; ch = int(cw * r.choice([.7, .9, 1.0]))
        down = int(n or 0) < 0; y0 = 1880 - rows * (ch + 18)
        if clip: x, y, w, h = box(760 if lay in ('top', 'center') else 520, max(300, y0 - 260), 120); body += _mask(shape, x, y, w, h, v)
        body += ''.join('<div class="cell" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><i></i></div>' % (60 + c * (cw + 18), y0 + rr * (ch + 18), cw, ch) for rr in range(rows) for c in range(cols))
        order = r.choice(['rand', 'wave', 'spiral'])
        js = ((_enter(r, '#m1') + drift) if clip else '') + (
            "const q=[...document.querySelectorAll('.cell')];let ord=q.map((e,i)=>[e,%s]).sort((a,b)=>a[1]-b[1]).map(x=>x[0]);"
            % {'rand': '(i*37)%q.length', 'wave': '(i%%%d)+Math.floor(i/%d)' % (cols, cols), 'spiral': 'Math.abs((i%%%d)-%d)+Math.abs(Math.floor(i/%d)-%d)' % (cols, cols // 2, cols, rows // 2)}[order] +
            "tl.fromTo('.cell',{scale:0,opacity:0},{scale:1,opacity:1,duration:.35,stagger:.01,ease:'back.out(2)'},.2);" +
            ("ord.forEach((e,i)=>tl.to(e.firstChild,{opacity:1,duration:.15},1.0+i*(D-1.6)/ord.length));" if not down else
             "tl.set('.cell i',{opacity:1},0);ord.forEach((e,i)=>tl.to(e.firstChild,{opacity:0,duration:.15},1.0+i*(D-1.6)/ord.length*.9));"))
    elif loai == 'dien_thoai':
        px = 260 if lay in ('top', 'center') else (60 if lay == 'left' else 460)
        body = '<div class="phone" id="ph" style="left:%dpx;top:240px"><div class="mask" style="left:26px;top:26px;right:26px;bottom:26px;border-radius:56px">%s</div></div>' % (px, v)
        rx = 1080 - 40 - 470 if px < 400 else 40
        body += ''.join('<div class="res" id="r%d" style="left:%dpx;top:%dpx"><b></b><u style="top:32px;width:250px"></u><u style="top:66px;width:180px"></u><u style="top:98px;width:110px"></u></div>' % (i, rx, 900 + i * 165) for i in range(r.choice([3, 4])))
        body += '<div class="frame" id="scan" style="left:%dpx;top:270px;width:508px;height:8px;background:linear-gradient(90deg,transparent,%s,transparent);box-shadow:0 0 30px %s"></div>' % (px + 26, G['g2'], G['g1'])
        js = ("tl.fromTo('#ph',{y:1500,rotation:%d},{y:0,rotation:0,duration:.9,ease:'power3.out'},0);tl.to('#ph',{scale:1.03,duration:Math.max(.5,D-1),ease:'none'},.9);" % r.choice([-10, 10]) +
              "tl.fromTo('#scan',{y:0,opacity:0},{y:1080,opacity:1,duration:1.2,ease:'none',repeat:1,yoyo:true},.9);" + drift +
              "for(let k=0;k<4;k++)if(document.getElementById('r'+k))tl.fromTo('#r'+k,{x:%d,opacity:0},{x:0,opacity:1,duration:.5,ease:'back.out(1.6)'},1.0+k*.3);sparks(12,1500,300);" % (900 if px < 400 else -900))
    elif loai in ('dem_nguoc', 'vong_so'):
        cx, cy, rad = 540, r.choice([700, 820, 960]), r.choice([300, 340])
        body = _mask('circle', cx - rad + 40, cy - rad + 40, 2 * rad - 80, 2 * rad - 80, v) if clip else ''
        ticks = ''.join('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%d" transform="rotate(%d %d %d)"/>' % (cx, cy - rad - 70, cx, cy - rad - (40 if i % 5 else 25), G['g2'], 4 if i % 5 else 8, i * 6, cx, cy) for i in range(60))
        body += ('<svg class="frame" style="left:0;top:0" width="1080" height="1920">%s<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="10" opacity=".25"/>'
                 '<circle id="sw" cx="%d" cy="%d" r="%d" fill="none" stroke="%s" stroke-width="34" stroke-linecap="round" transform="rotate(-90 %d %d)"/>%s</svg>') % (
            ticks if loai == 'dem_nguoc' else '', cx, cy, rad, G['g2'], cx, cy, rad, G['g1'], cx, cy,
            '<line id="hand" x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="14" stroke-linecap="round"/><circle cx="%d" cy="%d" r="24" fill="%s"/>' % (cx, cy, cx, cy - rad + 60, G['g6'], cx, cy, G['g2']) if (loai == 'dem_nguoc' and not clip) else '')
        pct = max(.15, min(1.0, abs(int(n or 0)) / 100.0)) if loai == 'vong_so' and abs(int(n or 0)) > 1 else (r.choice([.7, .85, 1.0]) if loai == 'vong_so' else 1.0)
        js = (("tl.fromTo('#m1',{scale:.2,opacity:0},{scale:1,opacity:1,duration:.8,ease:'back.out(1.5)'},0);tl.fromTo('#m1f',{rotation:-90,opacity:0,transformOrigin:'50% 50%'},{rotation:0,opacity:1,duration:1},.2);tl.to('#m1f',{rotation:90,duration:D,ease:'none'},1.2);" + drift) if clip else '') + (
            "const c=document.getElementById('sw'),L=2*Math.PI*%d;c.style.strokeDasharray=L;tl.fromTo('#sw',{strokeDashoffset:%s},{strokeDashoffset:%s,duration:Math.max(1,D-.8),ease:'%s'},.4);" % (
                rad, 'L' if loai == 'vong_so' else '0', 'L*%.2f' % (1 - pct) if loai == 'vong_so' else 'L', 'power2.out' if loai == 'vong_so' else 'none')) + (
            "tl.fromTo('#hand',{rotation:0,svgOrigin:'%d %d'},{rotation:360,svgOrigin:'%d %d',duration:Math.max(1,D-.6),ease:'none'},.3);" % (cx, cy, cx, cy) if (loai == 'dem_nguoc' and not clip) else '') + "sparks(14,%d,300);" % (cy + rad + 60)
    elif loai == 'phieu_loc':
        body = ('<svg class="frame" style="left:0;top:0" width="1080" height="1920"><path id="fun" d="M120 700 L960 700 L640 1180 L640 1420 L440 1420 L440 1180 Z" fill="%s" stroke="%s" stroke-width="10" stroke-linejoin="round"/>'
                '<path d="M200 760 L880 760" stroke="%s" stroke-width="4" stroke-dasharray="10 14"/></svg>' % (K[3], G['g1'], G['g2'])
                + ''.join('<div class="res" id="f%d" style="left:%dpx;top:220px;width:210px;height:140px"><b></b></div>' % (i, 60 + (i % 4) * 245) for i in range(8))
                + _mask(r.choice(['circle', 'hex', 'round', 'pill']), 300, 1420, 480, 440, v))
        js = ("tl.fromTo('#fun',{opacity:0,scale:.8,transformOrigin:'50% 50%'},{opacity:1,scale:1,duration:.5},0);"
              "for(let k=0;k<8;k++)tl.fromTo('#f'+k,{y:-500,opacity:0,rotation:(k%2?12:-12)},{y:600+(k%3)*40,x:(440-(60+(k%4)*245))*.8,opacity:0,rotation:0,scale:.4,duration:1.1,ease:'power2.in'},.3+k*.12);"
              "tl.fromTo('#m1',{scale:0,opacity:0},{scale:1,opacity:1,duration:.7,ease:'back.out(1.8)'},Math.min(1.6,D-1.3));" + drift + "sparks(12,1500,300);")
    elif loai == 'so_sanh':
        vert = r.random() < .5
        if vert:
            body = _mask('diag', 0, 0, 1080, 980, v, 'm1') + _mask('diag', 0, 940, 1080, 980, v.replace('id="v1"', 'id="v2"'), 'm2')
            body += '<div class="frame" id="sep" style="left:-40px;top:930px;width:1160px;height:16px;background:%s;box-shadow:0 0 40px %s;transform:rotate(-4deg)"></div>' % (G['g1'], G['g2'])
            js = "tl.fromTo('#m1',{x:-1100},{x:0,duration:.8,ease:'expo.out'},0);tl.fromTo('#m2',{x:1100},{x:0,duration:.8,ease:'expo.out'},.15);tl.fromTo('#sep',{scaleX:0},{scaleX:1,duration:.6,ease:'power2.out'},.6);"
        else:
            body = _mask('round', 30, 260, 500, 1400, v, 'm1') + _mask('round', 550, 260, 500, 1400, v.replace('id="v1"', 'id="v2"'), 'm2')
            body += '<div class="frame" id="sep" style="left:532px;top:200px;width:16px;height:1520px;background:%s;box-shadow:0 0 40px %s"></div>' % (G['g1'], G['g2'])
            js = "tl.fromTo('#m1',{y:-1700},{y:0,duration:.8,ease:'expo.out'},0);tl.fromTo('#m2',{y:1700},{y:0,duration:.8,ease:'expo.out'},.15);tl.fromTo('#sep',{scaleY:0},{scaleY:1,duration:.6,ease:'power2.out'},.6);"
        js += "tl.to('#v1',{scale:1.15,duration:D,ease:'none'},0);tl.fromTo('#v2',{scale:1.25,x:-80},{scale:1.25,x:80,duration:D,ease:'none'},0);" + "sparks(10,880,120);"
    elif loai == 'mat_bang':
        lines = []; x0, y0 = 150, 520
        for _ in range(r.randint(9, 14)):
            if r.random() < .5: x1 = r.choice(range(150, 930, 60)); lines.append((x1, r.choice(range(520, 1500, 60)), x1, r.choice(range(520, 1500, 60))))
            else: y1 = r.choice(range(520, 1500, 60)); lines.append((r.choice(range(150, 930, 60)), y1, r.choice(range(150, 930, 60)), y1))
        body = ('<svg class="frame" style="left:0;top:0" width="1080" height="1920"><rect id="ol" x="150" y="520" width="780" height="980" fill="none" stroke="%s" stroke-width="14"/>' % G['g1']
                + ''.join('<line class="wl" x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="7" stroke-linecap="round"/>' % (a, b, c, d, G['g2']) for a, b, c, d in lines)
                + ''.join('<path class="dr" d="M%d %d A 70 70 0 0 1 %d %d" fill="none" stroke="%s" stroke-width="3" stroke-dasharray="6 8"/>' % (x, y, x + 70, y + 70, G['g3']) for x, y in ((r.choice(range(200, 850, 60)), r.choice(range(560, 1400, 60))) for _ in range(4)))
                + '</svg>')
        if clip: x, y, w, h = box(420, 300, 140); body += _mask(r.choice(['round', 'circle', 'hex']), 1080 - 470 if lay != 'right' else 50, 1560, 420, 300, v)
        js = ("const o=document.getElementById('ol'),Lo=o.getTotalLength();o.style.strokeDasharray=Lo;tl.fromTo('#ol',{strokeDashoffset:Lo},{strokeDashoffset:0,duration:1,ease:'power2.inOut'},0);"
              "document.querySelectorAll('.wl').forEach((e,i)=>{const L=e.getTotalLength()||1;e.style.strokeDasharray=L;tl.fromTo(e,{strokeDashoffset:L},{strokeDashoffset:0,duration:.4,ease:'power1.out'},.8+i*Math.min(.15,(D-1.8)/14))});"
              "tl.fromTo('.dr',{opacity:0},{opacity:1,duration:.4,stagger:.15},1.6);" + ("tl.fromTo('#m1',{y:500,opacity:0},{y:0,opacity:1,duration:.7,ease:'back.out(1.5)'},1.0);" + drift if clip else ''))
    elif loai == 'tien':
        nst = r.choice([3, 4, 5]); body = ''
        if clip: x, y, w, h = box(700 if lay in ('top', 'center') else 520, 600, 140); body += _mask(shape, x, y, w, h, v)
        for s_ in range(nst):
            for c_ in range(r.randint(5, 11)):
                body += '<div class="coin cs%d" style="left:%dpx;top:%dpx"></div>' % (s_, 120 + s_ * (840 // nst), 1760 - c_ * 34)
        body += '<div class="frame" id="glow" style="left:240px;top:1100px;width:600px;height:600px;border-radius:50%%;background:radial-gradient(rgba(240,208,138,.5),transparent 65%%)"></div>'
        js = ((_enter(r, '#m1') + drift) if clip else '') + "tl.fromTo('#glow',{scale:.3,opacity:0},{scale:1.4,opacity:1,duration:D,ease:'power1.out'},0);" + ''.join(
            "tl.fromTo('.cs%d',{y:-900,opacity:0},{y:0,opacity:1,duration:.45,stagger:{each:.06,from:'end'},ease:'bounce.out'},%.2f);" % (s_, .4 + s_ * .25) for s_ in range(nst)) + "sparks(16,1400,300);"
    elif loai == 'khung_hinh':
        body = '<div class="mask" id="m1" style="left:0;top:0;width:1080px;height:1920px">%s</div>' % v
        body += '<div class="frame" style="left:0;top:0;width:1080px;height:1920px;background:linear-gradient(transparent 55%%,rgba(5,9,20,.75))"></div>'
        geo = r.choice(['brackets', 'diamond', 'rays'])
        if geo == 'brackets':
            body += ''.join('<div class="frame br" style="left:%dpx;top:%dpx;width:150px;height:150px;border-%s:10px solid %s;border-%s:10px solid %s"></div>' % (x, y, a, G['g1'], b, G['g1'], ) for x, y, a, b in ((70, 220, 'top', 'left'), (860, 220, 'top', 'right'), (70, 1550, 'bottom', 'left'), (860, 1550, 'bottom', 'right')))
            js2 = "tl.fromTo('.br',{scale:2,opacity:0},{scale:1,opacity:1,duration:.6,stagger:.08,ease:'power3.out'},.5);"
        elif geo == 'diamond':
            body += '<svg class="frame" style="left:0;top:0" width="1080" height="1920"><rect id="dm" x="290" y="710" width="500" height="500" fill="none" stroke="%s" stroke-width="8" transform="rotate(45 540 960)"/><rect id="dm2" x="240" y="660" width="600" height="600" fill="none" stroke="%s" stroke-width="3" transform="rotate(45 540 960)"/></svg>' % (G['g1'], G['g2'])
            js2 = "tl.fromTo('#dm',{scale:0,svgOrigin:'540 960'},{scale:1,rotation:90,svgOrigin:'540 960',duration:D,ease:'power2.out'},.3);tl.fromTo('#dm2',{scale:1.6,opacity:0,svgOrigin:'540 960'},{scale:1,opacity:1,rotation:-45,svgOrigin:'540 960',duration:D,ease:'power2.out'},.4);"
        else:
            body += '<div class="frame" id="rays" style="left:-460px;top:-560px;width:2000px;height:2000px;background:repeating-conic-gradient(from 0deg,rgba(240,208,138,.18) 0 4deg,transparent 4deg 16deg);mix-blend-mode:screen"></div>'
            js2 = "tl.fromTo('#rays',{rotation:0,opacity:0},{rotation:40,opacity:1,duration:D,ease:'none'},0);"
        rv = r.choice(["{clipPath:'circle(0% at 50% 50%)'},{clipPath:'circle(75% at 50% 50%)'", "{clipPath:'inset(0 100% 0 0)'},{clipPath:'inset(0 0% 0 0)'", "{clipPath:'polygon(0 0,0 0,0 100%,0 100%)'},{clipPath:'polygon(0 0,100% 0,100% 100%,0 100%)'"])
        js = "tl.fromTo('#m1',%s,duration:1,ease:'power3.inOut'},0);" % rv + "tl.fromTo('#v1',{scale:1.25},{scale:1.05,duration:D,ease:'power1.out'},0);" + js2 + "sparks(14,1500,300);"
    else:   # the_anh
        x, y, w, h = box(860 if lay in ('top', 'center') else 620, 1080 if shape not in ('circle', 'hex') else 760, 300)
        body = '<div class="stage">' + _mask(shape, x, y, w, h, v) + '</div>'
        js = _enter(r, '#m1') + spin + drift + "sparks(22,1450,300);"
    return body, js

def render(loai, out, dur, clip=None, n=0, work=None, log=print, seed=None, tz=False):
    loai = loai if loai in LOAI else 'the_anh'
    if not clip and loai in ('dien_thoai', 'phieu_loc', 'the_anh', 'ban_do', 'so_sanh', 'khung_hinh'): loai = 'khu_3d' if loai in ('the_anh', 'ban_do', 'khung_hinh') else 'tang_truong'
    r = random.Random(int(hashlib.md5(('%s|%s|%s' % (seed or out, loai, dur)).encode()).hexdigest()[:8], 16))
    work = work or out + '.d'; shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gsap.min.js'), work)
    if clip: shutil.copy(clip, os.path.join(work, 'clip.jpg' if clip.lower().endswith('.jpg') else 'clip.mp4'))
    bgfill, pat, patop, patmove = _bg(r)
    body, js = scene(loai, round(dur, 2), clip, n, r)
    if tz:   # có chữ CapCut → khối chính thu gọn xuống dưới, chừa vùng chữ phía trên (y 0–30 %) + dải nền tối mềm cho chữ nổi
        body = ('<div class="frame" style="left:0;top:0;width:1080px;height:640px;background:linear-gradient(rgba(5,9,20,.85),rgba(5,9,20,.55) 70%,transparent)"></div>'
                '<div style="position:absolute;left:0;top:0;width:1080px;height:1920px;transform:translateY(420px) scale(.78);transform-origin:50% 0">' + body + '</div>'
                '<div class="frame" id="tzl" style="left:140px;top:430px;width:800px;height:4px;background:linear-gradient(90deg,transparent,%s,transparent)"></div>' % G['g1'])
        js += "tl.fromTo('#tzl',{scaleX:0},{scaleX:1,duration:.7,ease:'power2.out'},.2);"
    dbody, djs = _decor(r); body = dbody + body; js = djs + js   # chi tiết trang trí nằm dưới khối chính
    d = dict(dur=round(dur, 2), body=body, js=js, enter='', bgfill=bgfill, pat=pat, patop=patop, patmove=patmove,
             k0=K[0], k1=K[1], k2=K[2], k3=K[3], k4=K[4], **G)
    open(os.path.join(work, 'index.html'), 'w').write(HTML % d)
    tf = os.path.expanduser('~/.hyperframes-tele-off')
    if not os.path.exists(tf):   # tắt gửi số liệu sử dụng của HyperFrames
        subprocess.run(['npx', '--yes', 'hyperframes@0.9.34', 'telemetry', 'disable'], capture_output=True, timeout=300); open(tf, 'w').close()
    r_ = subprocess.run(['npx', '--yes', 'hyperframes@0.9.34', 'render', '-q', 'looks', '-o', os.path.abspath(out)], cwd=work, capture_output=True, text=True, timeout=900)
    if not os.path.exists(out) or os.path.getsize(out) < 10000: raise RuntimeError('dựng motion lỗi: ' + (r_.stderr or r_.stdout)[-300:])
    shutil.rmtree(work, ignore_errors=True)
    return out

if __name__ == '__main__':   # thử nhanh: python3 mg.py loai clip.mp4|- out.mp4 [seed]
    import sys
    render(sys.argv[1], sys.argv[3], 4.0, sys.argv[2] if sys.argv[2] != '-' else None, seed=sys.argv[4] if len(sys.argv) > 4 else None)
