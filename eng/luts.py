# -*- coding: utf-8 -*-
"""Bộ LUT màu MICC (.cube 33³) – chủ dặn 20/11: project CapCut chọn sẵn màu LUT cho đẹp.
Mỗi LUT là một "look" điện ảnh nhẹ tay (trên nền đã cân màu từng cảnh bằng lớp Điều chỉnh), dựng bằng công thức nên không cần file ngoài."""
import numpy as np, re

N = 33
LOOKS = {   # tên file: (mô tả, cường độ gợi ý trong CapCut 0..1)
    'MICC_TealOrange': ('Điện ảnh xanh ngọc – cam: bóng tối xanh ngọc, da và vùng sáng ấm', .5),
    'MICC_WarmGold':   ('Sang trọng vàng đồng: ấm, vùng sáng ánh vàng champagne, đen mềm', .5),
    'MICC_CleanBright': ('Trong trẻo sáng sủa: sáng hơn, trắng sạch, màu tươi vừa phải (bất động sản, nội thất)', .55),
    'MICC_SoftFilm':   ('Phim nhẹ nhàng: đen bạc nhẹ, màu dịu, trung tính ấm – nữ tính, mơ mộng', .5),
    'MICC_Moody':      ('Trầm sâu: tương phản cao, xanh lá dịu, bóng tối xanh lạnh – kịch tính, đêm', .45),
    'MICC_Fresh':      ('Tươi mát: trời xanh, cây xanh rực hơn, da tự nhiên – ngoài trời ban ngày', .5),
}

def _lum(c): return c[..., 0] * .2126 + c[..., 1] * .7152 + c[..., 2] * .0722
def _sat(c, s):
    l = _lum(c)[..., None]; return l + (c - l) * s
def _vib(c, v):   # tăng màu nhạt nhiều, màu đã đậm ít (giữ da)
    c = np.clip(c, 0, 1); mx, mn = c.max(-1, keepdims=True), c.min(-1, keepdims=True); s = mx - mn
    return _sat(c, 1 + v * np.clip(1 - s, 0, 1) ** 1.5)
def _curve(x, k):   # S-curve mềm quanh 0.5, k>0 tăng tương phản
    x = np.clip(x, 0, 1); return np.clip(.5 + (x - .5) * (1 + k) - k * 4 * (x - .5) ** 3, 0, 1)
def _lift(x, b, w=1.0): return b + x * (w - b)
def _split(c, sh, hi, amt):   # nhuộm bóng tối / vùng sáng
    l = _lum(c)[..., None]; ws = np.clip(1 - l * 2, 0, 1) ** 1.2; wh = np.clip(l * 2 - 1, 0, 1) ** 1.2
    return c + amt * (ws * (np.array(sh) - .5) + wh * (np.array(hi) - .5))
def _wb(c, t, g=0.0):   # t>0 ấm, g>0 xanh lá → tím
    return c * np.array([1 + t * .5, 1 - g * .3, 1 - t * .5])
def _hue_band(c, center_rgb, s_mul, l_add=0.0):   # dịu / đậm một dải màu (vd cây xanh)
    cc = np.array(center_rgb, float); cc /= np.linalg.norm(cc)
    l = _lum(c)[..., None]; d = c - l; dn = d / (np.linalg.norm(d, axis=-1, keepdims=True) + 1e-6)
    w = np.clip((dn * (cc - cc.mean())/np.linalg.norm(cc - cc.mean())).sum(-1, keepdims=True), 0, 1) ** 2
    return l + d * (1 + (s_mul - 1) * w) + l_add * w

def look(name, c):
    if name == 'MICC_TealOrange':
        c = _curve(c, .18); c = _split(c, (.30, .55, .62), (.70, .52, .36), .32); c = _hue_band(c, (1, .55, .3), 1.12); c = _sat(c, 1.04)
    elif name == 'MICC_WarmGold':
        c = _wb(c, .07); c = _curve(c, .10); c = _split(c, (.48, .44, .42), (.72, .60, .40), .30); c = _lift(c, .025, .985); c = _sat(c, .96)
    elif name == 'MICC_CleanBright':
        c = np.clip(c, 0, 1) ** .9; c = _curve(c, .10); c = _wb(c, -.02); c = _vib(c, .22); c = _lift(c, 0.0, 1.0)
    elif name == 'MICC_SoftFilm':
        c = _curve(c, .08); c = _lift(c, .06, .96); c = _wb(c, .035); c = _sat(c, .84); c = _split(c, (.46, .5, .56), (.6, .54, .48), .16)
    elif name == 'MICC_Moody':
        c = _curve(c, .28); c = np.clip(c, 0, 1) ** 1.06; c = _hue_band(c, (.3, 1, .3), .7); c = _split(c, (.32, .46, .6), (.6, .54, .46), .26); c = _sat(c, .92)
    elif name == 'MICC_Fresh':
        c = _curve(c, .12); c = _hue_band(c, (.3, .5, 1), 1.18); c = _hue_band(c, (.35, 1, .3), 1.15); c = _vib(c, .14); c = np.clip(c, 0, 1) ** .96
    return np.clip(c, 0, 1)

# ---- chuyển màu theo máy quay (chủ dặn 21/11: xem source quay bằng máy gì → LUT phù hợp): log / HLG → Rec.709 rồi mới phủ look
CONV = {'SLog3': 'Sony S-Log3', 'VLog': 'Panasonic V-Log', 'CLog3': 'Canon C-Log3', 'DLog': 'DJI D-Log M', 'HLG': 'HLG (iPhone / máy quay HDR)'}
def _lin(conv, x):
    x = np.clip(x, 0, 1)
    if conv in ('SLog3', 'DLog'):
        a = 171.2102946929 / 1023; return np.where(x >= a, (10 ** ((x * 1023 - 420) / 261.5)) * .19 - .01, (x * 1023 - 95) * .01125 / (171.2102946929 - 95))
    if conv == 'VLog': return np.where(x < .181, (x - .125) / 5.6, 10 ** ((x - .598206) / .241514) - .00873)
    if conv == 'CLog3':
        return np.where(x < .097465473, -(10 ** ((.12783901 - x) / .36726845) - 1) / 14.98325, np.where(x <= .15277891, (x - .12512219) / 1.9754798, (10 ** ((x - .12240537) / .36726845) - 1) / 14.98325))
    if conv == 'HLG': return np.where(x <= .5, x * x / 3, (np.exp((x - .55991073) / .17883277) + .28466892) / 12) * 3.2
    return x
def to709(conv, c):
    if not conv: return c
    l = np.clip(_lin(conv, c), 0, None) * .82; t = (l * (2.51 * l + .03)) / (l * (2.43 * l + .59) + .14)   # tone map kiểu phim (ACES gần đúng)
    t = np.clip(t, 0, 1) ** (1 / 2.2); return np.clip(_sat(t, 1.12 if conv != 'HLG' else 1.0), 0, 1)
def cam_conv(cam):   # cam = thông tin ffprobe (make, model, trc…) + ước lượng log → loại chuyển màu
    if not cam: return ''
    trc = str(cam.get('trc') or '').lower(); mk = (str(cam.get('make') or '') + ' ' + str(cam.get('model') or '') + ' ' + str(cam.get('enc') or '')).lower()
    if 'arib-std-b67' in trc: return 'HLG'
    if not cam.get('log'): return ''
    if re.search(r'panasonic|lumix|dc-|gh\d|s5', mk): return 'VLog'
    if re.search(r'canon|eos|c70|r5|r6', mk): return 'CLog3'
    if re.search(r'dji|osmo|fc\d|mavic|pocket', mk): return 'DLog'
    return 'SLog3'
def cube(name, conv=''):
    g = np.linspace(0, 1, N); b, gg, r = np.meshgrid(g, g, g, indexing='ij')   # .cube: R chạy nhanh nhất
    c = np.stack([r, gg, b], -1).reshape(-1, 3); base = to709(conv, c.copy()); o = look(name, base.copy())
    if conv: k = LOOKS[name][1]; o = base * (1 - k) + o * k   # bản chuyển máy quay dùng 100 %: chuyển đủ, look vẫn nhẹ tay
    head = 'TITLE "%s"\n# MICC media – %s%s\nLUT_3D_SIZE %d\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n' % (name + ('__' + conv if conv else ''), LOOKS[name][0], (' · chuyển từ ' + CONV[conv]) if conv else '', N)
    return (head + '\n'.join('%.6f %.6f %.6f' % tuple(x) for x in o) + '\n').encode('utf-8')

def pick(style, recent, rnd):   # chọn look theo phong cách bộ dựng, khác các project gần đây
    pools = {'tvc': ['MICC_WarmGold', 'MICC_SoftFilm', 'MICC_TealOrange'], 'academy': ['MICC_CleanBright', 'MICC_Fresh', 'MICC_SoftFilm'],
             'bds': ['MICC_TealOrange', 'MICC_CleanBright', 'MICC_WarmGold', 'MICC_Fresh'], 'night': ['MICC_Moody', 'MICC_TealOrange']}
    pool = pools.get(style) or pools['bds']; c = [x for x in pool if x not in (recent or [])[-2:]] or pool
    return rnd.choice(c)
