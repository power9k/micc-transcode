# Motion graphic (HyperFrames) cho bản dựng CapCut – chủ dặn 11/11:
#  - đồ họa sinh động KHÔNG CÓ CHỮ (chữ vẫn làm trên CapCut), ghép cùng cảnh quay gốc (cảnh nằm trong thẻ bo góc)
#  - màu theo tông web MICC (nền xanh than, vàng kim) – lấy từ biến màu của web
#  - mỗi clip lưu trong CHÍNH thư mục project (không đưa vào kho chung)
import json, os, shutil, subprocess

W, H = 1080, 1920
# biến màu web (3-web-source/v5: --k0..k3 nền, --g1..g6 vàng)
K = ['#050914', '#090e1c', '#0d1426', '#131c32', '#1a2744']
G = {'g1': '#d6b262', 'g2': '#f0d08a', 'g3': '#f4e2b4', 'g4': '#967632', 'g5': '#b08c3e', 'g6': '#f7e8c4'}
LOAI = {   # loại đồ họa Claude được chọn (mô tả để Claude hiểu)
    'ban_do': 'bản đồ / vị trí: cảnh dự án trong thẻ, ghim vị trí rơi xuống, sóng lan, đường đi nét đứt tới điểm khác',
    'khu_3d': 'khu nhà / tòa tháp 3D mọc lên trên mặt sàn xoay (quy mô dự án, siêu dự án, số căn, mật độ)',
    'tang_truong': 'cảnh trong thẻ + cột biểu đồ mọc + mũi tên tăng (giá tăng, sinh lời, lãi, tiềm năng)',
    'giam': 'cột biểu đồ giảm dần + mũi tên đi xuống (lãi suất cao/thấp, rủi ro, chi phí giảm, hàng còn ít)',
    'luoi_can': 'lưới ô căn hộ sáng dần lên hoặc tắt dần (số căn, bán hết, còn lại bao nhiêu)',
    'dien_thoai': 'màn hình điện thoại chứa cảnh, thẻ kết quả trượt lên (app, AI, tìm căn, công nghệ, mạng xã hội)',
    'dem_nguoc': 'vòng đếm ngược / đồng hồ quét (thời gian, 3 giây, 30 giây, hạn chót, nhanh)',
    'phieu_loc': 'phễu lọc: nhiều thẻ rơi vào phễu, ra 1 thẻ sáng (lọc nhu cầu, chọn đúng, sàng lọc)',
    'the_anh': 'cảnh đẹp trong thẻ 3D xoay vào, viền vàng, bụi sáng (minh họa chung, sang trọng)',
}

HTML = r'''<!doctype html><html><head><meta charset="utf-8"><script src="gsap.min.js"></script><style>
html,body{margin:0;background:#000}#root{position:relative;width:1080px;height:1920px;overflow:hidden;background:%(k0)s}
.bg{position:absolute;inset:-200px;background:radial-gradient(ellipse at 50%% 35%%,%(k4)s 0%%,%(k2)s 45%%,%(k0)s 100%%)}
.topo{position:absolute;inset:-300px;opacity:.13;background:repeating-radial-gradient(circle at 30%% 40%%,transparent 0 38px,%(g2)s 39px 41px,transparent 42px 80px),repeating-radial-gradient(circle at 75%% 70%%,transparent 0 52px,%(g2)s 53px 55px,transparent 56px 110px)}
.card{position:absolute;border-radius:48px;overflow:hidden;background:%(k3)s;box-shadow:0 40px 120px rgba(0,0,0,.6),0 0 0 6px %(g1)s,0 0 80px rgba(214,178,98,.45)}
.card video{width:100%%;height:100%%;object-fit:cover;display:block}
.ring{position:absolute;border:6px solid %(g2)s;border-radius:50%%}
.spark{position:absolute;width:10px;height:10px;border-radius:50%%;background:%(g6)s;box-shadow:0 0 18px 6px %(g1)s}
.bar{position:absolute;width:120px;border-radius:18px 18px 0 0;background:linear-gradient(%(g3)s,%(g5)s);transform-origin:50%% 100%%}
.coin{position:absolute;width:130px;height:130px;border-radius:50%%;background:radial-gradient(circle at 35%% 30%%,%(g6)s,%(g1)s 55%%,%(g4)s);box-shadow:0 0 0 8px %(g5)s inset,0 20px 40px rgba(0,0,0,.4)}
.stage{position:absolute;left:0;top:0;width:1080px;height:1920px;perspective:2200px}
.floor{position:absolute;left:60px;top:760px;width:960px;height:960px;transform-style:preserve-3d;transform:rotateX(62deg) rotateZ(-35deg);background:linear-gradient(rgba(240,208,138,.2) 2px,transparent 2px) 0 0/90px 90px,linear-gradient(90deg,rgba(240,208,138,.2) 2px,transparent 2px) 0 0/90px 90px,radial-gradient(%(k4)s,%(k0)s)}
.bld{position:absolute;transform-style:preserve-3d}.bld i{position:absolute;display:block;backface-visibility:hidden}
.cell{position:absolute;width:150px;height:110px;border-radius:16px;background:%(k3)s;box-shadow:0 0 0 3px rgba(214,178,98,.35) inset}.cell i{position:absolute;inset:0;border-radius:16px;background:linear-gradient(%(g3)s,%(g1)s);box-shadow:0 0 26px %(g1)s;opacity:0}
.phone{position:absolute;left:250px;top:260px;width:580px;height:1180px;border-radius:80px;background:%(k1)s;box-shadow:0 0 0 14px %(g4)s,0 0 0 20px %(g1)s,0 60px 140px rgba(0,0,0,.7)}
.phone .scr{position:absolute;left:28px;top:28px;right:28px;bottom:28px;border-radius:58px;overflow:hidden;background:%(k2)s}
.res{position:absolute;left:300px;width:480px;height:150px;border-radius:30px;background:linear-gradient(90deg,%(k3)s,%(k4)s);box-shadow:0 0 0 4px %(g1)s,0 20px 50px rgba(0,0,0,.5)}
.res b{position:absolute;left:24px;top:24px;width:100px;height:100px;border-radius:20px;background:linear-gradient(%(g3)s,%(g5)s)}
.res u{position:absolute;left:150px;height:18px;border-radius:9px;background:rgba(244,226,180,.55)}
</style></head><body>
<div id="root" data-composition-id="root" data-width="1080" data-height="1920" data-fps="30" data-duration="%(dur)s">
<div class="bg"></div><div class="topo" id="topo"></div>
%(body)s
</div>
<script>
const D=%(dur)s, P=%(par)s, tl=gsap.timeline({paused:true});
tl.to('#topo',{x:120,y:-160,rotation:6,duration:D,ease:'none'},0);
function sparks(n,y0){const r=document.getElementById('root');for(let i=0;i<n;i++){const s=document.createElement('div');s.className='spark';s.style.left=(80+((i*137)%%920))+'px';s.style.top=(y0+((i*71)%%300))+'px';r.appendChild(s)}
 tl.fromTo('.spark',{y:0,opacity:0},{y:-900,opacity:1,duration:Math.max(1.5,D-.8),stagger:.05,ease:'power1.out'},.3)}
function cardIn(sel,dl){tl.fromTo(sel,{rotationY:-70,rotationX:12,scale:.6,opacity:0,y:200},{rotationY:0,rotationX:0,scale:1,opacity:1,y:0,duration:1,ease:'power3.out'},dl||0);
 tl.to(sel,{scale:1.05,duration:Math.max(.5,D-1.6),ease:'none'},(dl||0)+1)}
%(js)s
tl.to('#root',{opacity:1,duration:.01},D-.01);
window.__timelines=window.__timelines||{};window.__timelines['root']=tl;
</script></body></html>'''

def _vid(clip):
    return '<video id="v1" src="clip.mp4" muted playsinline data-start="0" data-duration="%s"></video>' if clip else ''

def scene(loai, dur, clip, n=0):
    v = (_vid(clip) % dur) if clip else ''
    if loai == 'ban_do':
        body = ('<div class="stage"><div id="c1" class="card" style="left:90px;top:380px;width:900px;height:1100px">%s</div></div>'
                '<svg style="position:absolute;left:0;top:0" width="1080" height="1920"><path id="route" d="M540 1000 C 700 1250, 860 1350, 900 1640" fill="none" stroke="%s" stroke-width="12" stroke-dasharray="26 22" stroke-linecap="round"/>'
                '<circle id="dot2" cx="900" cy="1640" r="26" fill="%s"/></svg>'
                '<div id="r1" class="ring" style="left:490px;top:980px;width:100px;height:40px"></div><div id="r2" class="ring" style="left:490px;top:980px;width:100px;height:40px"></div>'
                '<svg id="pin" style="position:absolute;left:480px;top:820px" width="120" height="160" viewBox="0 0 120 160"><path d="M60 156C60 156 8 92 8 56a52 52 0 0 1 104 0c0 36-52 100-52 100z" fill="%s" stroke="%s" stroke-width="5"/><circle cx="60" cy="56" r="20" fill="%s"/></svg>') % (v, G['g2'], G['g1'], G['g2'], K[1], K[2])
        js = ("cardIn('#c1',0);tl.fromTo('#pin',{y:-700,opacity:0},{y:0,opacity:1,duration:.7,ease:'bounce.out'},.9);"
              "tl.fromTo('#r1',{scale:.2,opacity:1},{scale:4,opacity:0,duration:1.2,ease:'power2.out'},1.5);tl.fromTo('#r2',{scale:.2,opacity:1},{scale:4,opacity:0,duration:1.2,ease:'power2.out'},2.1);"
              "const r=document.getElementById('route'),L=r.getTotalLength();tl.fromTo('#route',{strokeDashoffset:L,opacity:0},{strokeDashoffset:0,opacity:1,duration:1.2},1.8);tl.fromTo('#dot2',{scale:0,transformOrigin:'50% 50%'},{scale:1,duration:.4,ease:'back.out(2)'},2.9);")
    elif loai == 'khu_3d':
        body = '<div class="stage"><div class="floor" id="floor"></div></div>'
        if clip: body += '<div id="c1" class="card" style="left:240px;top:150px;width:600px;height:420px">%s</div>' % v
        js = ("const fl=document.getElementById('floor');const B=[[1,1,3],[3,1,5],[5,2,4],[2,4,6],[4,5,8],[6,4,4],[7,7,3],[1,6,4],[6,1,2],[3,7,5]],C=['%s','%s','%s','%s','%s'];const bl=[];"
              "B.forEach(([gx,gy,h],k)=>{const w=150,Hh=h*70,d=document.createElement('div');d.className='bld';d.style.cssText=`left:${gx*95}px;top:${gy*95}px;width:${w}px;height:${w}px;`;const c=C[k%%5];"
              "const sh=f=>`linear-gradient(rgba(0,0,0,${f}),rgba(0,0,0,${f})),repeating-linear-gradient(90deg,transparent 0 22px,rgba(9,14,28,.45) 22px 34px),repeating-linear-gradient(transparent 0 26px,rgba(255,255,255,.25) 26px 30px),${c}`;"
              "[[`width:${w}px;height:${Hh}px;transform:rotateX(-90deg) translateY(${-Hh}px);transform-origin:0 0;`,.05],[`width:${w}px;height:${Hh}px;transform:translateY(${w}px) rotateX(-90deg) translateY(${-Hh}px);transform-origin:0 0;`,.18],[`width:${Hh}px;height:${w}px;transform:rotateY(90deg);transform-origin:0 0;`,.3],[`width:${Hh}px;height:${w}px;transform:translateX(${w}px) rotateY(90deg);transform-origin:0 0;`,.12]].forEach(([css,f])=>{const i=document.createElement('i');i.style.cssText=css+`background:${sh(f)}`;d.appendChild(i)});"
              "const rf=document.createElement('i');rf.style.cssText=`width:${w}px;height:${w}px;transform:translateZ(${Hh}px);background:%s;box-shadow:0 0 30px %s`;d.appendChild(rf);fl.appendChild(d);bl.push(d)});"
              "tl.fromTo('#floor',{rotationZ:-60,scale:.7},{rotationZ:-15,scale:1.05,duration:D,ease:'power1.inOut'},0);bl.forEach((b,k)=>tl.fromTo(b.children,{scaleY:0,opacity:0},{scaleY:1,opacity:1,duration:.6,ease:'back.out(1.6)'},.3+k*Math.min(.18,(D-1.2)/10)));sparks(24,1500);"
              % (G['g3'], G['g2'], G['g6'], G['g1'], '#e7c77e', G['g6'], G['g2'])) + ("cardIn('#c1',.2);" if clip else '')
    elif loai in ('tang_truong', 'giam'):
        hs = [180, 300, 440, 620] if loai == 'tang_truong' else [620, 440, 300, 180]
        path = 'M170 1420 L350 1300 L520 1340 L760 1010 L900 860' if loai == 'tang_truong' else 'M170 900 L350 1050 L520 1010 L760 1280 L900 1420'
        head = 'M840 850 L915 845 L905 920' if loai == 'tang_truong' else 'M840 1430 L915 1430 L905 1355'
        body = ('<div id="c1" class="card" style="left:110px;top:160px;width:860px;height:620px">%s</div>' % v if clip else '') + ''.join(
            '<div class="bar" id="b%d" style="left:%dpx;bottom:420px;height:%dpx"></div>' % (i, 190 + 180 * i, h_) for i, h_ in enumerate(hs)) + (
            '<svg style="position:absolute;left:0;top:0" width="1080" height="1920"><path id="arrow" d="%s" fill="none" stroke="%s" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/><path id="head" d="%s" fill="none" stroke="%s" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            '<div class="coin" id="k1" style="left:80px;top:1600px"></div><div class="coin" id="k2" style="left:860px;top:1650px"></div>') % (path, G['g6'], head, G['g6'])
        js = (("tl.fromTo('#c1',{y:-900,rotation:-8},{y:0,rotation:0,duration:.8,ease:'power3.out'},0);tl.to('#c1',{scale:1.04,duration:Math.max(.5,D-1),ease:'none'},.8);" if clip else '') +
              "[0,1,2,3].forEach(k=>tl.fromTo('#b'+k,{scaleY:0},{scaleY:1,duration:.6,ease:'back.out(1.4)'},.4+k*.15));"
              "const ar=document.getElementById('arrow'),L=ar.getTotalLength();ar.style.strokeDasharray=L;tl.fromTo('#arrow',{strokeDashoffset:L},{strokeDashoffset:0,duration:1.1,ease:'power2.inOut'},1.0);"
              "tl.fromTo('#head',{opacity:0},{opacity:1,duration:.3},2.0);tl.fromTo('#k1',{y:500,rotation:-90},{y:0,rotation:0,duration:.7,ease:'back.out(1.7)'},1.4);tl.fromTo('#k2',{y:500,rotation:90},{y:0,rotation:0,duration:.7,ease:'back.out(1.7)'},1.6);")
    elif loai == 'luoi_can':
        cols, rows = 5, 8; down = int(n or 0) < 0
        body = ('<div id="c1" class="card" style="left:190px;top:120px;width:700px;height:420px">%s</div>' % v if clip else '') + ''.join(
            '<div class="cell" id="q%d" style="left:%dpx;top:%dpx"><i></i></div>' % (r * cols + c, 60 + c * 196, 640 + r * 140) for r in range(rows) for c in range(cols))
        js = (("cardIn('#c1',0);" if clip else '') +
              "const q=[...document.querySelectorAll('.cell')].sort(()=>0);const ord=q.map((e,i)=>[e,(i*37)%q.length]).sort((a,b)=>a[1]-b[1]).map(x=>x[0]);"
              "tl.fromTo('.cell',{scale:0,opacity:0},{scale:1,opacity:1,duration:.4,stagger:.015,ease:'back.out(2)'},.2);"
              + ("ord.forEach((e,i)=>tl.to(e.firstChild,{opacity:1,duration:.15},1.0+i*(D-1.6)/ord.length));" if not down else
                 "tl.set('.cell i',{opacity:1},0);ord.forEach((e,i)=>tl.to(e.firstChild,{opacity:0,duration:.15},1.0+i*(D-1.6)/ord.length*.9));"))
    elif loai == 'dien_thoai':
        body = ('<div class="phone" id="ph"><div class="scr">%s</div></div>' % v) + ''.join(
            '<div class="res" id="r%d" style="top:%dpx"><b></b><u style="top:34px;width:260px"></u><u style="top:72px;width:190px"></u><u style="top:104px;width:120px"></u></div>' % (i, 1000 + i * 175) for i in range(3))
        js = ("tl.fromTo('#ph',{y:1400,rotation:10},{y:0,rotation:0,duration:.9,ease:'power3.out'},0);tl.to('#ph',{scale:1.03,duration:Math.max(.5,D-1),ease:'none'},.9);"
              "[0,1,2].forEach(k=>tl.fromTo('#r'+k,{x:900,opacity:0},{x:0,opacity:1,duration:.5,ease:'back.out(1.6)'},1.0+k*.35));sparks(14,1500);")
    elif loai == 'dem_nguoc':
        body = ('<div id="c1" class="card" style="left:240px;top:200px;width:600px;height:600px;border-radius:50%%">%s</div>' % v if clip else '') + (
            '<svg style="position:absolute;left:0;top:0" width="1080" height="1920"><circle cx="540" cy="1250" r="330" fill="none" stroke="%s" stroke-width="10" opacity=".25"/>'
            '<circle id="sw" cx="540" cy="1250" r="330" fill="none" stroke="%s" stroke-width="34" stroke-linecap="round" transform="rotate(-90 540 1250)"/>'
            '<line id="hand" x1="540" y1="1250" x2="540" y2="960" stroke="%s" stroke-width="16" stroke-linecap="round"/><circle cx="540" cy="1250" r="30" fill="%s"/></svg>') % (G['g2'], G['g1'], G['g6'], G['g2'])
        js = (("cardIn('#c1',0);" if clip else '') +
              "const c=document.getElementById('sw'),L=2*Math.PI*330;c.style.strokeDasharray=L;tl.fromTo('#sw',{strokeDashoffset:0},{strokeDashoffset:L,duration:Math.max(1,D-.6),ease:'none'},.3);"
              "tl.fromTo('#hand',{rotation:0,svgOrigin:'540 1250'},{rotation:360,svgOrigin:'540 1250',duration:Math.max(1,D-.6),ease:'none'},.3);sparks(16,1550);")
    elif loai == 'phieu_loc':
        body = ('<svg style="position:absolute;left:0;top:0" width="1080" height="1920"><path id="fun" d="M150 760 L930 760 L640 1220 L640 1500 L440 1500 L440 1220 Z" fill="%s" stroke="%s" stroke-width="10" stroke-linejoin="round"/></svg>' % (K[3], G['g1'])
                + ''.join('<div class="res" id="f%d" style="left:%dpx;top:260px;width:220px;height:150px"><b></b></div>' % (i, 80 + (i % 4) * 240) for i in range(8))
                + '<div id="c1" class="card" style="left:290px;top:1440px;width:500px;height:360px">%s</div>' % v)
        js = ("tl.fromTo('#fun',{opacity:0,scale:.8,transformOrigin:'50% 50%'},{opacity:1,scale:1,duration:.5},0);"
              "[0,1,2,3,4,5,6,7].forEach(k=>tl.fromTo('#f'+k,{y:-500,opacity:0,rotation:(k%2?12:-12)},{y:620+(k%3)*40,x:(440-(80+(k%4)*240))*.8,opacity:0.0,rotation:0,scale:.4,duration:1.1,ease:'power2.in'},.3+k*.12));"
              "cardIn('#c1',Math.min(1.6,D-1.4));sparks(14,1500);")
    else:   # the_anh
        body = '<div class="stage"><div id="c1" class="card" style="left:90px;top:380px;width:900px;height:1160px">%s</div></div>' % v
        js = "cardIn('#c1',0);sparks(26,1450);"
    return body, js

def render(loai, out, dur, clip=None, n=0, work=None, log=print):
    loai = loai if loai in LOAI else 'the_anh'
    if loai in ('dien_thoai', 'phieu_loc', 'the_anh', 'ban_do') and not clip: loai = 'khu_3d' if loai != 'dien_thoai' else 'tang_truong'
    work = work or out + '.d'; shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gsap.min.js'), work)
    if clip: shutil.copy(clip, os.path.join(work, 'clip.mp4'))
    body, js = scene(loai, round(dur, 2), clip, n)
    d = dict(K=K, dur=round(dur, 2), body=body, js=js, par=json.dumps({'n': n}), k0=K[0], k1=K[1], k2=K[2], k3=K[3], k4=K[4], **G)
    open(os.path.join(work, 'index.html'), 'w').write(HTML % d)
    tf = os.path.expanduser('~/.hyperframes-tele-off')
    if not os.path.exists(tf):   # tắt gửi số liệu sử dụng của HyperFrames
        subprocess.run(['npx', '--yes', 'hyperframes@0.9.34', 'telemetry', 'disable'], capture_output=True, timeout=300); open(tf, 'w').close()
    r = subprocess.run(['npx', '--yes', 'hyperframes@0.9.34', 'render', '-q', 'looks', '-o', os.path.abspath(out)], cwd=work, capture_output=True, text=True, timeout=900)
    if not os.path.exists(out) or os.path.getsize(out) < 10000: raise RuntimeError('dựng motion lỗi: ' + (r.stderr or r.stdout)[-300:])
    shutil.rmtree(work, ignore_errors=True)
    return out

if __name__ == '__main__':   # thử nhanh: python3 mg.py loai clip.mp4 out.mp4
    import sys
    render(sys.argv[1], sys.argv[3], 4.0, sys.argv[2] if sys.argv[2] != '-' else None)
