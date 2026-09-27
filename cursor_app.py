# -*- coding: utf-8 -*-
"""光标管家 - 一键换光标 (精致版)
主题库定位顺序：环境变量 CURSOR_LIB > exe/脚本同级目录 > 脚本上级目录 > 用户目录
  - 主题列表 / 像素预览 / 一键应用
  - 拖拽或按钮安装主题包：支持 .zip，也支持把解压后的文件夹直接拖进来(自动忽略教程/图片等杂物)
"""
import os, sys, io, re, json, struct, shutil, zipfile, tempfile
import ctypes
import winreg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# 主题库定位：环境变量 CURSOR_LIB > 候选目录中"确实含主题"的 > 程序同级> 用户目录
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_APP_DIR)

def _has_themes(path):
    """目录里是否含有光标主题(子目录含 .inf 描述文件 或 多个 .cur/.ani 光标文件)"""
    if not os.path.isdir(path):
        return False
    try:
        entries = os.listdir(path)
    except Exception:
        return False
    # 1) 直接看子目录：含 .inf，或含至少一个 .cur/.ani（有几个算几个，不设数量门槛）
    for name in entries:
        full = os.path.join(path, name)
        if not os.path.isdir(full):
            continue
        try:
            sub = os.listdir(full)
        except Exception:
            continue
        low = [s.lower() for s in sub]
        if any(s.endswith('.inf') for s in low):
            return True
        if any(s.endswith(('.cur', '.ani')) for s in low):
            return True
    return False

_CANDIDATES = []
if os.environ.get('CURSOR_LIB'):
    _CANDIDATES.append(os.environ['CURSOR_LIB'])
_CANDIDATES += [
    os.path.join(_APP_DIR, '光标主题'),   # 安装包形态：程序目录\光标主题
    _APP_DIR,                             # 绿色形态：主题就在程序旁边
    os.path.join(_PARENT, '光标主题'),    # 源码形态：上级\光标主题
    _PARENT,
    os.path.join(os.path.expanduser('~'), '光标主题'),
]
# 先挑确实含主题的，退而求其次挑存在的目录，最后兜底到用户目录
LIB = next((p for p in _CANDIDATES if _has_themes(p)), None)
if LIB is None:
    LIB = next((p for p in _CANDIDATES if os.path.isdir(p)), None)
if LIB is None:
    LIB = os.path.join(os.path.expanduser('~'), '光标主题')
os.makedirs(LIB, exist_ok=True)
CONFIG_PATH = os.path.join(LIB, 'config.json')

SLOT_ORDER = ['Arrow','Help','AppStarting','Wait','Crosshair','IBeam','NWPen','No',
              'SizeNS','SizeWE','SizeNWSE','SizeNESW','SizeAll','UpArrow','Hand','Pin','Person']

OCR = {'Arrow':32512,'Help':32651,'AppStarting':32650,'Wait':32514,'Crosshair':32515,
       'IBeam':32513,'No':32648,'SizeNS':32645,'SizeWE':32644,'SizeNWSE':32642,
       'SizeNESW':32643,'SizeAll':32646,'UpArrow':32516,'Hand':32649,'NWPen':32631}

NAME_MAP = {}
def _m(slots):
    for slot, names in slots.items():
        for n in names:
            NAME_MAP[n.lower()] = slot
_m({
 'Arrow':    ['正常选择','pointer','normal','arrow'],
 'Help':     ['帮助选择','help','helpsel'],
 'AppStarting':['后台运行','working','work','appstarting'],
 'Wait':     ['忙','busy','wait'],
 'Crosshair':['精确选择','精准选择','cross','precision'],
 'IBeam':    ['文本选择','text','beam'],
 'NWPen':    ['手写','handwriting','pen','handwrite'],
 'No':       ['不可用','unavailable','unavail'],
 'SizeNS':   ['垂直调整大小','vert','vertical','sel_1','ns'],
 'SizeWE':   ['水平调整大小','horz','horizontal','sel_2','ew'],
 'SizeNWSE': ['沿对角线调整大小 1','沿对角线调整大小1','沿对角线调整 1','dgn1','sel_3','diagonal1','nwse'],
 'SizeNESW': ['沿对角线调整大小 2','沿对角线调整大小2','沿对角线调整 2','dgn2','sel_4','diagonal2','nesw'],
 'SizeAll':  ['移动','move','sizeall'],
 'UpArrow':  ['候选','alternate','up'],
 'Hand':     ['链接选择','连接选择','link'],
 'Pin':      ['位置选择','pin','loc'],
 'Person':   ['个人选择','person'],
})

# .inf 的 Schemes 串里用的变量名 -> 槽位。
# 位置不可靠：老包的 inf 可能少列中间的槽位(比如没有 cross)，
# 按顺序硬套会让后面全部错位，所以按名字对。
INF_VAR_MAP = {}
def _iv(slots):
    for slot, names in slots.items():
        for n in names:
            INF_VAR_MAP[n.lower()] = slot
_iv({
 'Arrow':       ['pointer','normal','arrow','cur','aero_arrow'],
 'Help':        ['help','helpsel','helpselect'],
 'AppStarting': ['work','working','appstarting','appstart'],
 'Wait':        ['busy','wait'],
 'Crosshair':   ['cross','crosshair','precision'],
 'IBeam':       ['text','ibeam','beam'],
 'NWPen':       ['handwrt','handwriting','pen'],
 'No':          ['unavailiable','unavailable','unavail','no'],
 'SizeNS':      ['vert','vertical','ns','size_ns'],
 'SizeWE':      ['horz','horizontal','we','size_we'],
 'SizeNWSE':    ['dgn1','diagonal1','nwse','size_nwse'],
 'SizeNESW':    ['dgn2','diagonal2','nesw','size_nesw'],
 'SizeAll':     ['move','sizeall','size_all'],
 'UpArrow':     ['alternate','up','uparrow'],
 'Hand':        ['link','hand'],
 'Pin':         ['pin','loc','location'],
 'Person':      ['person'],
})

# ---------------- registry ----------------
def _open_live():
    return winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r'Control Panel\Cursors', 0, winreg.KEY_ALL_ACCESS)

def _open_schemes():
    return winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r'Control Panel\Cursors\Schemes', 0, winreg.KEY_ALL_ACCESS)

def get_scheme_name():
    try:
        with _open_live() as k:
            return winreg.QueryValueEx(k, '')[0]
    except Exception:
        return ''


def broadcast():
    class A: pass
    u = ctypes.windll.user32
    u.SendMessageTimeoutW(0xFFFF, 0x001A, 0, 'Windows', 2, 1000, ctypes.byref(ctypes.c_void_p()))

def set_system_cursors(slotmap):
    ok, fail = 0, 0
    for slot, oid in OCR.items():
        path = slotmap.get(slot)
        if not path or not os.path.exists(path):
            continue
        h = ctypes.windll.user32.LoadCursorFromFileW(path)
        if h and ctypes.windll.user32.SetSystemCursor(h, oid):
            ok += 1
        else:
            fail += 1
    return ok, fail

# ---------------- ani / cur ----------------
def _parse_chunks(data, start, end):
    # 块头里声明的 size 是可信的，但文件可能是坏的/被截断的：
    # 不校验的话切片会静默变短，payload 拿到半截数据，
    # 后面 PIL 会抛 "Truncated File Read" 这种看不懂的错
    out, off = [], start
    while off + 8 <= end:
        cid = data[off:off+4]
        size = struct.unpack('<I', data[off+4:off+8])[0]
        if off + 8 + size > end:
            raise ValueError(f'文件已损坏：块 {cid!r} 声明 {size} 字节，但剩余数据不够')
        out.append((cid, data[off+8:off+8+size]))
        off += 8 + size + (size & 1)
    return out







def load_cursor_image(path):
    """PIL image of a .cur/.ani (first frame)"""
    try:
        if path.lower().endswith('.ani'):
            data = open(path, 'rb').read()
            for cid, payload in _parse_chunks(data, 12, len(data)):
                if cid == b'LIST' and payload[:4] == b'fram':
                    for icid, ip in _parse_chunks(payload, 4, len(payload)):
                        if icid == b'icon':
                            try:
                                return Image.open(io.BytesIO(ip)).convert('RGBA')
                            except Exception:
                                return _icon_fallback_decode(ip)
            return None
        try:
            return Image.open(path).convert('RGBA')
        except Exception:
            return _icon_fallback_decode(open(path, 'rb').read())
    except Exception:
        return None

def _icon_fallback_decode(data):
    """decode cur/ico payload via type-1 ico re-wrap (handles PNG & multi-size)"""
    try:
        cnt = struct.unpack('<H', data[4:6])[0]
        best = None
        for i in range(cnt):
            e = data[6+16*i: 6+16*(i+1)]
            w, h = e[0] or 256, e[1] or 256
            size, off = struct.unpack('<II', e[8:16])
            if best is None or w*h > best[0]:
                best = (w*h, w, h, size, off)
        if not best:
            return None
        payload = data[best[4]:best[4]+best[3]]
        entry = bytes([best[1] if best[1] < 256 else 0,
                       best[2] if best[2] < 256 else 0, 0, 0])
        entry += struct.pack('<HHII', 0, 0, best[3], 22)
        ico = struct.pack('<HHH', 0, 1, 1) + entry + payload
        return Image.open(io.BytesIO(ico)).convert('RGBA')
    except Exception:
        return None

# ---------------- inf parsing ----------------
def parse_inf(inf_path):
    text = None
    for enc in ('utf-16', 'utf-8', 'gbk'):
        try:
            text = open(inf_path, encoding=enc).read()
            break
        except Exception:
            continue
    if not text:
        return None
    m = re.search(r'HKEY_CURRENT_USER\s*,|HKCU\s*,.*Schemes.*', text, re.I)
    line = None
    for ln in text.splitlines():
        if 'Schemes' in ln and 'HKCU' in ln.upper():
            line = ln.strip()
            break
    if not line:
        return None
    strings, sec = {}, None
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith('['):
            sec = s.strip('[]').strip().lower()
            continue
        if sec == 'strings' and '=' in s:
            k2, v2 = s.split('=', 1)
            strings[k2.strip().lower()] = v2.strip().strip('"')
    # inf 的 Schemes 串里按变量名对应槽位，有几个认几个，不要求凑满 17 个。
    # 按位置硬套是不行的：老包常少列中间的槽位，那后面的槽位就全错位了。
    files, idx = {}, 0
    for e in line.split(','):
        toks = re.findall(r'%([^%]+)%', e)
        if not toks:
            continue
        var = toks[-1].lower()
        if var in ('scheme_name', 'cur_dir'):
            continue
        if var not in strings:
            idx += 1
            continue
        slot = INF_VAR_MAP.get(var)
        if slot is None:
            # 变量名不认识时，仅在这一项确实没对上的情况下按位置兜底
            if idx < len(SLOT_ORDER):
                slot = SLOT_ORDER[idx]
        idx += 1
        if slot and slot not in files:
            files[slot] = strings[var]
    if not files:
        return None
    sname = strings.get('scheme_name') or os.path.basename(os.path.dirname(inf_path))
    return (sname, files)

# ---------------- theme library ----------------
def cursor_files_in(folder):
    out = []
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if is_cursor_file(f):
                out.append(os.path.join(root, f))
    return out

# 这些目录里装的是教程/说明/备用图，不是给系统用的光标，递归时要跳过
SKIP_DIR_HINTS = ('教程', '说明', '预览', '截图', '图片', '壁纸', '备用', 'tutorial', 'readme', 'preview', 'screenshot')

def _is_junk_dir(name):
    low = name.lower()
    return any(h in low for h in SKIP_DIR_HINTS)

JUNK_STEM_HINTS = ('教程', '说明', '预览', '截图', '安装方法', '安装说明', 'readme', 'tutorial', 'preview', 'screenshot', 'icon', '图标', 'logo', '背景', '壁纸')

def _is_junk_stem(stem):
    low = stem.lower()
    return any(h in low for h in JUNK_STEM_HINTS)

def is_cursor_file(path_or_name):
    """是不是一个真正的光标文件：扩展名必须是 .cur/.ani，且文件名不能是教程/图标之类的杂物"""
    name = os.path.basename(str(path_or_name))
    if not name.lower().endswith(('.cur', '.ani')):
        return False
    return not _is_junk_stem(os.path.splitext(name)[0])

def map_slots_by_name(folder):
    return map_slots_by_name_from_list(cursor_files_in(folder))

def map_slots_by_name_from_list(paths):
    """按文件名把一批光标文件对应到槽位；每个槽位只取第一个命中的"""
    slotmap = {}
    keys = sorted(NAME_MAP.keys(), key=len, reverse=True)
    # 先按文件名长度排一遍，让命名更精确的文件优先被选中
    for path in sorted(paths, key=lambda p: len(os.path.basename(p)), reverse=True):
        # 只认"文件名本身就是槽位名"的，避免 normal_教程 这类被误判成光标
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        slot = NAME_MAP.get(stem)
        if not slot:
            hits = [k for k in keys if k in stem]
            if hits:
                slot = NAME_MAP[hits[0]]
        if slot and slot not in slotmap:
            slotmap[slot] = path
    return slotmap

def scan_themes():
    themes = {}
    if not os.path.isdir(LIB):
        return themes
    for name in sorted(os.listdir(LIB)):
        folder = os.path.join(LIB, name)
        if not os.path.isdir(folder):
            continue
        files = cursor_files_in(folder)
        if not files:
            continue
        slotmap, inf_name = None, None
        for root, _d, fs in os.walk(folder):
            for f in fs:
                if f.lower().endswith('.inf'):
                    r = parse_inf(os.path.join(root, f))
                    if r:
                        inf_name, order_map = r
                        resolved = {}
                        for slot, fname in order_map.items():
                            cands = [p for p in files if os.path.basename(p).lower() == fname.lower()]
                            if cands:
                                resolved[slot] = cands[0]
                        # inf 里列的文件能对上几个算几个
                        if resolved:
                            slotmap = resolved
                    break
            if slotmap:
                break
        if not slotmap:
            slotmap = map_slots_by_name(folder)
        # 识别几个算几个：只要有 1 个能对上槽位就收进主题库
        if slotmap:
            themes[name] = {'folder': folder, 'slotmap': slotmap, 'inf_name': inf_name}
    return themes

def extract_zip_fix(zpath, dest):
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            name = info.filename
            if not (info.flag_bits & 0x800):
                try:
                    name = name.encode('cp437').decode('gbk')
                except Exception:
                    pass
            target = os.path.normpath(os.path.join(dest, name))
            if not target.startswith(os.path.normpath(dest)):
                continue
            if info.is_dir() or name.endswith('/'):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as f, open(target, 'wb') as g:
                shutil.copyfileobj(f, g)

def install_zip(zpath, progress=lambda s: None):
    base_name = os.path.splitext(os.path.basename(zpath))[0]
    tmp = tempfile.mkdtemp(prefix='cursor_install_')
    try:
        progress('解压中...')
        extract_zip_fix(zpath, tmp)
        return _install_from_dir(tmp, base_name, progress)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def install_folder(folder, progress=lambda s: None):
    """直接把一个已解压的文件夹装进主题库(内容原样，不改动源目录)"""
    base_name = os.path.basename(os.path.normpath(folder))
    return _install_from_dir(folder, base_name, progress)

def _install_from_dir(src_dir, base_name, progress=lambda s: None):
    theme_name, slotmap = None, None
    for root, _d, fs in os.walk(src_dir):
        for f in fs:
            if f.lower().endswith('.inf'):
                r = parse_inf(os.path.join(root, f))
                if r:
                    theme_name, order_map = r
                    allf = []
                    for r2, d2, fs2 in os.walk(src_dir):
                        d2[:] = [x for x in d2 if not _is_junk_dir(x)]
                        for f2 in fs2:
                            if is_cursor_file(f2):
                                allf.append(os.path.join(r2, f2))
                    resolved = {}
                    for slot, fname in order_map.items():
                        cands = [p for p in allf if os.path.basename(p).lower() == fname.lower()]
                        if cands:
                            resolved[slot] = cands[0]
                    # inf 里列的文件能对上几个算几个
                    if resolved:
                        slotmap = resolved
                break
        if slotmap:
            break
    if not slotmap:
        progress('未发现 .inf，按文件名识别...')
        # 按槽位名把源文件认出来，但槽位表里存的必须是"源文件本身"的路径，
        # 不能在临时目录里比对完就把临时目录删掉——那样后面复制时源路径已经不存在了
        found = []
        for r2, d2, fs2 in os.walk(src_dir):
            d2[:] = [x for x in d2 if not _is_junk_dir(x)]
            for f2 in fs2:
                if is_cursor_file(f2):
                    found.append(os.path.join(r2, f2))
        slotmap = map_slots_by_name_from_list(found)
    if len(slotmap) < 1:
        raise ValueError('没能识别出光标文件（文件名需能对应到槽位，如 正常选择.cur / Normal.ani）')

    wanted = theme_name or base_name
    dest = os.path.join(LIB, wanted)
    # 源目录本身就在主题库里(直接把库里已有主题拖回来)时不能往自己身上复制，另起一个名字
    src_norm = os.path.normcase(os.path.normpath(src_dir))
    i = 2
    while os.path.exists(dest) and os.path.normcase(os.path.normpath(dest)) != src_norm:
        dest = os.path.join(LIB, f'{wanted}({i})')
        i += 1
    if os.path.normcase(os.path.normpath(dest)) == src_norm:
        dest = os.path.join(LIB, f'{wanted}(副本)')
        j = 2
        while os.path.exists(dest):
            dest = os.path.join(LIB, f'{wanted}(副本{j})')
            j += 1
    os.makedirs(dest, exist_ok=True)
    progress('复制到主题库...')
    copied = 0
    for slot, path in slotmap.items():
        shutil.copy2(path, dest)
        copied += 1
    # 带上 .inf：槽位映射的唯一权威来源，丢了它下次扫描就只能靠文件名猜，
    # 像 select.ani→Crosshair 这种靠文件名根本推不出来
    for root, _d, fs in os.walk(src_dir):
        for f in fs:
            if f.lower().endswith('.inf'):
                try:
                    shutil.copy2(os.path.join(root, f), dest)
                except Exception:
                    pass
    return os.path.basename(dest), copied

# ---------------- apply ----------------
def apply_theme(name, themes, status=lambda s: None):
    t = themes[name]
    slotmap = t['slotmap']
    with _open_live() as k:
        for slot in SLOT_ORDER:
            p = slotmap.get(slot)
            if p:
                winreg.SetValueEx(k, slot, 0, winreg.REG_EXPAND_SZ, p)
        winreg.SetValueEx(k, '', 0, winreg.REG_SZ, name)
    with _open_schemes() as k:
        s = ','.join(slotmap.get(sl, '') for sl in SLOT_ORDER)
        winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ, s)
    ok, fail = set_system_cursors(slotmap)
    save_config('last_theme', name)
    broadcast()
    return ok, fail

# ---------------- config ----------------
def load_config():
    try:
        return json.load(open(CONFIG_PATH, encoding='utf-8'))
    except Exception:
        return {}

def save_config(key, value):
    cfg = load_config()
    cfg[key] = value
    try:
        json.dump(cfg, open(CONFIG_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception:
        pass

# ---------------- UI ----------------
BG      = '#161a23'
PANEL   = '#1f2430'
FG      = '#e8eaf0'
DIM     = '#8b93a7'
ACCENT  = '#4f8cff'
ACCENT2 = '#39d98a'
HOVER   = '#2a3040'
SELECT  = '#33415e'

class App:
    def __init__(self, root, S=1.5):
        self.root = root
        self.S = S
        root.title('光标管家')
        root.geometry(f'{int(820*S)}x{int(560*S)}')
        root.minsize(int(760*S), int(520*S))
        root.configure(bg=BG)
        self.themes = {}
        self._photo = None
        self._photos = []
        self._build_ui()
        self._autoinstall_packs()
        self.refresh_themes()
        self._load_state()
        self._setup_dnd()

    def _autoinstall_packs(self):
        """自动安装 放进 安装包 目录的 zip 主题(已装过的按文件名跳过)"""
        packs = os.path.join(LIB, '安装包')
        if not os.path.isdir(packs):
            return
        cfg = load_config()
        done = set(cfg.get('installed_zips', []))
        dirty = False
        for f in sorted(os.listdir(packs)):
            if not f.lower().endswith('.zip') or f in done:
                continue
            try:
                self.status_msg('自动安装: ' + f)
                self.root.update_idletasks()
                name, copied = install_zip(os.path.join(packs, f), progress=self.status_msg)
                done.add(f)
                dirty = True
                self.status_msg(f'自动安装完成: {name} ({copied} 个文件)')
            except Exception as ex:
                self.status_msg(f'自动安装失败 {f}: {ex}')
        if dirty:
            save_config('installed_zips', sorted(done))

    # ---------- widgets ----------
    def _build_ui(self):
        f = ('Microsoft YaHei UI', 10)
        fb = ('Microsoft YaHei UI', 10, 'bold')
        fs = ('Microsoft YaHei UI', 9)

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=14, pady=(12, 6))
        tk.Label(header, text='🖱️ 光标管家', font=('Microsoft YaHei UI', 15, 'bold'),
                 bg=BG, fg=FG).pack(side='left')
        self.cur_label = tk.Label(header, text='', font=fs, bg=BG, fg=ACCENT2)
        self.cur_label.pack(side='right')

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=14)

        # left: theme list
        left = tk.Frame(body, bg=PANEL)
        left.pack(side='left', fill='both', expand=True, ipadx=2, ipady=2)
        tk.Label(left, text=' 主题库', font=fb, bg=PANEL, fg=DIM, anchor='w').pack(fill='x', pady=(6, 2))
        lb_wrap = tk.Frame(left, bg=PANEL)
        lb_wrap.pack(fill='both', expand=True, padx=8)
        self.listbox = tk.Listbox(lb_wrap, bg=PANEL, fg=FG, font=f, selectbackground=SELECT,
                                  selectforeground=FG, relief='flat', highlightthickness=1,
                                  highlightbackground='#2c3345', activestyle='none')
        sb = ttk.Scrollbar(lb_wrap, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.listbox.pack(side='left', fill='both', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        self.listbox.bind('<Double-Button-1>', lambda e: self.apply_selected())

        btns = tk.Frame(left, bg=PANEL)
        btns.pack(fill='x', padx=8, pady=8)
        def mkbtn(parent, text, cmd, color=ACCENT, w=13):
            b = tk.Button(parent, text=text, command=cmd, font=f, bg=color, fg='white',
                          activebackground=HOVER, activeforeground=FG, relief='flat',
                          bd=0, cursor='hand2', width=w, pady=4)
            return b
        mkbtn(btns, '应用主题', self.apply_selected).grid(row=0, column=0, padx=(0, 6), pady=3, sticky='ew')
        mkbtn(btns, '安装主题包', self.install_dialog, color='#8a63ff').grid(row=0, column=1, pady=3, sticky='ew')
        mkbtn(btns, '打开主题库', lambda: os.startfile(LIB), color='#3a4152', w=6).grid(row=1, column=0, padx=(0, 6), pady=3, sticky='ew')
        mkbtn(btns, '刷新', self.refresh_themes, color='#3a4152', w=6).grid(row=1, column=1, pady=3, sticky='ew')
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        # right: preview
        right = tk.Frame(body, bg=PANEL)
        right.pack(side='left', fill='both', expand=True, padx=(10, 0), ipadx=2, ipady=2)
        tk.Label(right, text=' 预览', font=fb, bg=PANEL, fg=DIM, anchor='w').pack(fill='x', pady=(6, 2))
        self.preview = tk.Canvas(right, width=int(300*self.S), height=int(210*self.S), bg='#14171f', highlightthickness=1,
                                 highlightbackground='#2c3345')
        self.preview.pack(padx=8, pady=4, anchor='n')
        self.prev_name = tk.Label(right, text='选择左侧主题', font=fs, bg=PANEL, fg=DIM)
        self.prev_name.pack()

        # footer
        foot = tk.Frame(self.root, bg=BG)
        foot.pack(fill='x', padx=14, pady=(0, 8))
        self.status = tk.Label(foot, text='就绪', font=fs, bg=BG, fg=DIM, anchor='e')
        self.status.pack(side='right')

    def status_msg(self, s):
        self.status.configure(text=s)
        self.root.update_idletasks()

    # ---------- themes ----------
    def refresh_themes(self):
        self.themes = scan_themes()
        self.listbox.delete(0, 'end')
        current = get_scheme_name()
        self._index = []
        for name in self.themes:
            mark = '  ✓ ' if name == current else '    '
            self.listbox.insert('end', mark + name)
            self._index.append(name)
        self.cur_label.configure(text='当前方案: ' + (current or '未知'))
        for i, name in enumerate(self._index):
            if name == current:
                self.listbox.selection_set(i)
                self.listbox.see(i)
                break
        self._on_select()

    def _selected_name(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self._index[sel[0]]

    def _on_select(self, _e=None):
        name = self._selected_name()
        if name:
            self._render_preview(name)

    def apply_selected(self):
        name = self._selected_name()
        if not name:
            self.status_msg('请先选择一个主题')
            return
        self.status_msg('应用中: ' + name)
        try:
            ok, fail = apply_theme(name, self.themes)
            self.status_msg(f'已应用 {name} (即时生效 {ok} 项{", 其余登录后补齐" if fail else ""})')
            self.refresh_themes()
        except Exception as ex:
            messagebox.showerror('应用失败', str(ex))
            self.status_msg('应用失败')

    # ---------- preview ----------
    def _render_preview(self, name):
        t = self.themes.get(name)
        c = self.preview
        c.delete('all')
        self._photos = []
        if not t:
            return
        S = self.S
        slotmap = t['slotmap']
        def draw(slot, x, y, box):
            path = slotmap.get(slot)
            im = load_cursor_image(path) if path else None
            if not im:
                return
            w, h = im.size
            scale = min(box / w, box / h)
            im2 = im.resize((max(1, int(w*scale)), max(1, int(h*scale))), Image.NEAREST)
            ph = ImageTk.PhotoImage(im2)
            self._photos.append(ph)
            c.create_image(x, y, image=ph, anchor='nw')
        c.create_text(int(150*S), int(18*S), text='正常选择', fill=DIM, font=('Microsoft YaHei UI', 9))
        draw('Arrow', int(150*S) - int(48*S), int(30*S), int(96*S))
        labels = [('链接选择', 'Hand'), ('文本选择', 'IBeam'), ('忙', 'Wait'), ('不可用', 'No')]
        x = int(22*S)
        for text, slot in labels:
            c.create_text(x + int(28*S), int(140*S), text=text, fill=DIM, font=('Microsoft YaHei UI', 8))
            draw(slot, x, int(152*S), int(44*S))
            x += int(66*S)
        self.prev_name.configure(text=f'{name}  ·  {len(slotmap)} 个槽位')

    # ---------- install ----------
    def install_dialog(self):
        path = filedialog.askopenfilename(title='选择光标主题压缩包',
                                          filetypes=[('光标主题包', '*.zip'),
                                                     ('光标文件', '*.cur *.ani'),
                                                     ('所有文件', '*.*')])
        if path:
            self._install_path(path)

    def _install_path(self, path):
        self._run_install(lambda: install_zip(path, progress=self.status_msg),
                          '安装中: ' + os.path.basename(path))

    def _install_folder_path(self, folder):
        self._run_install(lambda: install_folder(folder, progress=self.status_msg),
                          '识别中: ' + os.path.basename(os.path.normpath(folder)))

    def _run_install(self, fn, busy_msg):
        try:
            self.status_msg(busy_msg)
            self.root.update_idletasks()
            name, copied = fn()
            self.status_msg(f'已安装主题 [{name}] ({copied} 个文件)')
            self.refresh_themes()
            messagebox.showinfo('安装完成', f'主题 [{name}] 已加入主题库\n({copied} 个文件)')
        except Exception as ex:
            messagebox.showerror('安装失败', str(ex))
            self.status_msg('安装失败')

    # ---------- dnd ----------
    def _setup_dnd(self):
        # 能否拖拽取决于 root 本身是否带 tkdnd 扩展，而不是外部先赋的标志位
        if not hasattr(self.root, 'drop_target_register'):
            self.status_msg('就绪')
            return
        try:
            from tkinterdnd2 import DND_FILES
            # tkdnd 的 <<Drop>> 只对注册的那个窗口生效，不会从子控件冒泡上来。
            # 窗口里铺满 Listbox/Canvas/Button，只注册 root 的话拖到任何控件上都收不到事件，
            # 所以把 root 和所有后代控件都注册一遍。
            targets = [self.root]
            def collect(w):
                for c in w.winfo_children():
                    targets.append(c)
                    collect(c)
            collect(self.root)
            ok = 0
            for w in targets:
                try:
                    w.drop_target_register(DND_FILES)
                    w.bind('<<Drop>>', self._on_drop)
                    ok += 1
                except Exception:
                    continue
            self.dnd_ok = ok > 0
            self.status_msg('就绪 (支持拖入 .zip 或文件夹)')
        except Exception:
            self.dnd_ok = False
            self.status_msg('就绪')

    def _on_drop(self, e):
        # tkdnd 的 e.data 可能是 str(单个) 或 tuple(多个)，且含空格的路径会被 {} 包裹
        raw = getattr(e, 'data', None)
        if raw is None:
            return
        if isinstance(raw, (tuple, list)):
            parts = [str(p) for p in raw]
        else:
            data = str(raw).strip()
            if data.startswith('{') and data.endswith('}'):
                data = data[1:-1]
            parts = re.split(r'\}\s*\{', data)
        for path in parts:
            path = path.strip().strip('{}').strip()
            if not path or not os.path.exists(path):
                continue
            if path.lower().endswith('.zip'):
                self._install_path(path)
                return
            if os.path.isdir(path):
                self._install_folder_path(path)
                return
        # 没找到可用的目标：明确告诉用户，而不是静默失败
        first = next((p.strip().strip('{}').strip() for p in parts if p.strip()), '')
        if first and os.path.exists(first):
            self.status_msg('拖入的是文件，请用 .zip 主题包或将解压后的文件夹拖进来')
            messagebox.showwarning('无法安装', '请拖入 .zip 主题包，或包含光标文件的文件夹。')
        else:
            self.status_msg('找不到拖入的文件')
            messagebox.showwarning('无法安装', f'找不到文件:\n{first}')

    # ---------- state ----------
    def _load_state(self):
        try:
            last = load_config().get('last_theme')
        except Exception:
            last = None
        if last and last in self.themes and get_scheme_name() != last:
            self.status_msg('上次使用: ' + last)

def _make_root():
    """优先用 tkinterdnd2 的 Tk 以支持拖拽，失败则退回标准 Tk"""
    try:
        if getattr(sys, 'frozen', False):
            base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
            tkdnd = os.path.join(base, 'tkinterdnd2', 'tkdnd')
            if os.path.isdir(tkdnd):
                os.environ.setdefault('TKDND_LIBRARY', tkdnd)
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk(), True
    except Exception:
        return tk.Tk(), False

def main():
    # DPI awareness: 在高缩放屏上获得清晰渲染
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    root, dnd_ok = _make_root()
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        root.tk.call('tk', 'scaling', dpi / 72.0)
    except Exception:
        pass
    root.option_add('*Font', ('Microsoft YaHei UI', 10))
    S = 1.5
    try:
        S = ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        pass
    app = App(root, S=S)
    if not dnd_ok:
        # 退回标准 Tk 时不支持拖拽；App 已自行判定过，这里只兜底提示
        app.dnd_ok = False
    root.mainloop()

if __name__ == '__main__':
    main()
