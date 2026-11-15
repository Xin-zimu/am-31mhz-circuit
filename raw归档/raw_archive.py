# -*- coding: utf-8 -*-
"""
raw_archive.py —— 仿真 raw 归档工具（B/C 档流程）v2

解析支持：
  1. ngspice ASCII 头 + Binary real（8字节/值，数据段锚定文件尾）
  2. ngspice ASCII 头 + Binary complex（16字节/值，含/不含 8 字节前导）
  3. 纯 ASCII Values（real：每点 nv 行；complex：每行 "re,im"）
  4. 超长瞬态：指标自动按首/中/末三段统计，避免漂移污染

命令：
  raw_check   <目录> [输出json]
  raw_extract <raw路径> <输出指标json> [输出png]
  raw_summary <目录> <输出目录>
"""
import json
import math
import os
import re
import sys
from datetime import datetime

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_IMG = True
except Exception:
    HAS_IMG = False

PREFERRED_NODES = [
    "v(input)", "v(in)", "v(tank1)", "v(tank2)", "v(port)", "v(out)", "v(output)",
    "v(v1)", "v(v2)", "v(v3)", "v(tp2)", "v(tp3)", "v(oe)", "v(bbo)", "v(bb)",
    "v(base)", "v(emit)", "v(det)", "v(rf)",
    "i(lsel1)", "i(lsel2)",
]


def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


# ---------------------------------------------------------------- 头部解析
def parse_raw_header(path):
    """返回 (info, blob)。info 含 n_variables/n_points/variables/plotname/flags 等。
    兼容 ngspice ASCII(latin-1) 与 LTspice UTF-16LE 头。"""
    with open(path, "rb") as f:
        blob = f.read()
    # LTspice：UTF-16LE 头（"T\0i\0t\0l\0e\0:\0" 前缀），Binary: 标记也是 UTF-16
    utf16 = blob[:12] == b"T\x00i\x00t\x00l\x00e\x00:\x00"
    if utf16:
        bmark = blob.find(b"B\x00i\x00n\x00a\x00r\x00y\x00")
        if bmark < 0:
            raise ValueError("LTspice 头无 Binary 标记")
        head = blob[:bmark].decode("utf-16-le", "replace")
        info = _parse_head_text(head)
        info["encoding"] = "utf-16-le"
        # Binary 后可能带 ":\n"（UTF16 4 字节）或直接数据；
        # 精确起点：跳过可能的 ':'、'\n'、'\0' 等分隔字节。
        off = bmark + len(b"B\x00i\x00n\x00a\x00r\x00y\x00")
        while off < len(blob) and blob[off:off + 1] in (b":", b"\n", b"\r", b"\x00"):
            off += 1
        info["data_offset"] = off
        return info, blob
    # ngspice ASCII
    head = blob.decode("latin-1", "replace")
    info = _parse_head_text(head)
    info["encoding"] = "latin-1"
    return info, blob


def _parse_head_text(head):
    info = {}
    for key in ("Title", "Date", "Plotname", "Flags"):
        mm = re.search(r"^{}:\s*(.*)$".format(key), head, re.M)
        if mm:
            info[key.lower()] = mm.group(1).strip()
    mv = re.search(r"^No\. Variables:\s*(\d+)", head, re.M)
    mp = re.search(r"^No\. Points:\s*(\d+)", head, re.M)
    info["n_variables"] = int(mv.group(1)) if mv else 0
    info["n_points"] = int(mp.group(1)) if mp else 0
    var_positions = [m.start() for m in re.finditer(r"^Variables:", head, re.M)]
    vars_ = []
    if var_positions:
        var_blob = head[var_positions[-1]:]
        for marker in ("Values:", "Binary:"):
            j = var_blob.find(marker)
            if j >= 0:
                var_blob = var_blob[:j]
                break
        for line in var_blob.splitlines():
            mm = re.match(r"^\s*(\d+)\s+(\S+)\s+(\S+)", line)
            if mm:
                vars_.append({"idx": int(mm.group(1)), "name": mm.group(2),
                              "type": mm.group(3)})
    info["variables"] = vars_
    return info


# ---------------------------------------------------------------- 数据解析
def _parse_binary_real(blob, off, np_, nv):
    """binary real：8字节/值；数据段锚定文件尾（容忍前导对齐字节与末点截断）。"""
    need = np_ * nv * 8
    start = len(blob) - need
    if start < off:
        # 尾部截断：按完整点数降级读取
        avail = (len(blob) - off) // (nv * 8)
        if avail < 1:
            raise ValueError("binary real 数据不足")
        arr = np.frombuffer(blob, dtype="<f8", count=avail * nv, offset=off)
        return arr.reshape(avail, nv)
    arr = np.frombuffer(blob, dtype="<f8", count=np_ * nv, offset=start)
    return arr.reshape(np_, nv)


def _parse_binary_complex(blob, off, np_, nv):
    """binary complex：16字节/值；数据段锚定文件尾。"""
    need = np_ * nv * 16
    start = len(blob) - need
    if start < off:
        raise ValueError("binary complex 数据不足: 需要=%d 可用=%d" % (need, len(blob) - off))
    arr = np.frombuffer(blob, dtype="<f8", count=np_ * nv * 2, offset=start)
    return arr.reshape(np_, nv * 2)


def _parse_ascii_values(blob, off, np_, nv, flags):
    """ASCII Values：real 每点 nv 行；complex 每行 're,im'。"""
    text = blob[off:].decode("latin-1", "replace")
    lines = text.splitlines()
    is_complex = ("complex" in (flags or "").lower())
    vals = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        # 跳过行号前缀（如 " 0\t1.0e-3" 或 " 123\t..."）
        if "\t" in ln:
            parts = ln.split("\t", 1)
            rest = parts[-1].strip()
        else:
            mm = re.match(r"^\s*\d+\s+(.*)$", ln)
            rest = mm.group(1).strip() if mm else ln
        if is_complex:
            mm = re.match(r"^([-+0-9.eE]+),([-+0-9.eE]+)$", rest)
            if not mm:
                continue
            vals.append(float(mm.group(1)))
            vals.append(float(mm.group(2)))
        else:
            try:
                vals.append(float(rest))
            except ValueError:
                continue
    need = np_ * nv * (2 if is_complex else 1)
    if len(vals) < need:
        raise ValueError("ascii 数据不足: 解析 %d 个数值, 需要 %d" % (len(vals), need))
    arr = np.array(vals[:need], dtype="<f8")
    if is_complex:
        arr = arr.reshape(np_, nv, 2)
    else:
        arr = arr.reshape(np_, nv)
    return arr


def parse_raw_data(path):
    """返回 (info, x ndarray, dict name->ndarray)。ndarray 实数或复数。"""
    info, blob = parse_raw_header(path)
    nv = info["n_variables"]
    np_ = info["n_points"]
    names = [v["name"] for v in info["variables"][:nv]] or \
        ["v%d" % i for i in range(nv)]
    if len(names) < nv:
        names += ["v%d" % i for i in range(len(names), nv)]
    flags = info.get("flags", "").lower()

    if info.get("encoding") == "utf-16-le":
        # LTspice：Binary 数据段已在头部定位；数据是 np*nv 个 double
        off = info.get("data_offset", 0)
        if "complex" in flags:
            arr = _parse_binary_complex(blob, off, np_, nv)
        else:
            arr = _parse_binary_real(blob, off, np_, nv)
        names = _ltspice_names(info, nv)
        x = arr[:, 0]
        out = {}
        for i, name in enumerate(names):
            out[name] = arr[:, i]
        info["n_points_read"] = arr.shape[0]
        return info, x, out

    mbin = blob.find(b"Binary:")
    mval = blob.find(b"Values:")
    if mbin >= 0:
        off = mbin + len(b"Binary:")
        # Binary 后可能有 \r\n 或 \n
        while off < len(blob) and blob[off:off + 1] in (b"\n", b"\r"):
            off += 1
        if "complex" in flags:
            arr = _parse_binary_complex(blob, off, np_, nv)
        else:
            arr = _parse_binary_real(blob, off, np_, nv)
    elif mval >= 0:
        off = mval + len(b"Values:")
        while off < len(blob) and blob[off:off + 1] in (b"\n", b"\r"):
            off += 1
        arr = _parse_ascii_values(blob, off, np_, nv, flags)
    else:
        raise ValueError("无 Values:/Binary: 标记")

    if "complex" in flags and arr.ndim == 3:
        x = arr[:, 0, 0]
    else:
        x = arr[:, 0]
    out = {}
    for i, name in enumerate(names):
        if "complex" in flags and arr.ndim == 3:
            out[name] = arr[:, i, 0] + 1j * arr[:, i, 1]
        else:
            out[name] = arr[:, i]
    # 实际读取点数可能与头部声明不一致（截断），按实际修正
    info["n_points_read"] = arr.shape[0]
    return info, x, out


def _ltspice_names(info, nv):
    """LTspice 变量名取自头部变量表；缺省时回退 var%d。"""
    names = [v["name"] for v in info["variables"][:nv]]
    if len(names) >= nv:
        return names
    return ["var%d" % i for i in range(nv)]


# ---------------------------------------------------------------- 指标
def _seg_metrics(y):
    """实数或复数信号的分段指标：整体 + 首/中/末三段。"""
    mag = np.abs(y)
    mag = mag[np.isfinite(mag)]
    n = len(mag)
    if n == 0:
        return None
    if n < 4:
        return {
            "min": float(np.min(mag)), "max": float(np.max(mag)),
            "mean": float(np.mean(mag)), "n": n,
            "first_min": float(np.min(mag)), "first_max": float(np.max(mag)),
            "first_mean": float(np.mean(mag)),
            "mid_min": float(np.min(mag)), "mid_max": float(np.max(mag)),
            "mid_mean": float(np.mean(mag)),
            "last_min": float(np.min(mag)), "last_max": float(np.max(mag)),
            "last_mean": float(np.mean(mag)),
        }
    seg = max(n // 20, 1)
    mid0 = n // 2 - max(seg // 2, 1)
    mid1 = n // 2 + max(seg // 2, 1)
    res = {
        "min": float(np.min(mag)), "max": float(np.max(mag)),
        "mean": float(np.mean(mag)), "n": n,
        "first_min": float(np.min(mag[:seg])), "first_max": float(np.max(mag[:seg])),
        "first_mean": float(np.mean(mag[:seg])),
        "mid_min": float(np.min(mag[mid0:mid1])), "mid_max": float(np.max(mag[mid0:mid1])),
        "mid_mean": float(np.mean(mag[mid0:mid1])),
        "last_min": float(np.min(mag[-seg:])), "last_max": float(np.max(mag[-seg:])),
        "last_mean": float(np.mean(mag[-seg:])),
    }
    return res


def extract_one(path, out_json, out_png, max_vars=4, title=None):
    """解析单个 raw：指标 JSON + 波形 PNG（Pillow 自绘）。"""
    info, x, sig = parse_raw_data(path)
    is_ac = "AC" in (info.get("plotname", "") or "").upper() or \
        "complex" in (info.get("flags", "") or "").lower()
    metrics = {"variables": {}}
    for name, y in sig.items():
        m = _seg_metrics(y)
        if m is None:
            continue
        if is_ac:
            db = 20 * np.log10(np.maximum(np.abs(y), 1e-30))
            m["min_db"] = float(np.min(db))
            m["max_db"] = float(np.max(db))
            m["mean_db"] = float(np.mean(db))
        metrics["variables"][name] = m
    metrics["meta"] = {
        "file": os.path.basename(path),
        "title": info.get("title", ""),
        "date": info.get("date", ""),
        "plotname": info.get("plotname", ""),
        "flags": info.get("flags", ""),
        "n_points": info["n_points"],
        "n_variables": info["n_variables"],
        "sha256": sha256_file(path),
        "size_bytes": os.path.getsize(path),
        "x_min": float(x[0]) if len(x) else None,
        "x_max": float(x[-1]) if len(x) else None,
        "is_ac": is_ac,
    }
    metrics["plot_vars"] = [n for n in pick_plot_vars(info, max_vars) if n in sig]
    if not metrics["plot_vars"]:
        metrics["plot_vars"] = list(sig.keys())[:max_vars]
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=1)
    if out_png:
        _plot_one_pillow(x, sig, metrics["plot_vars"], is_ac, out_png,
                         title=title or os.path.basename(path))
    return metrics


def pick_plot_vars(info, max_vars=4):
    names = [v["name"] for v in info["variables"]]
    picked = []
    for pref in PREFERRED_NODES:
        if pref in names and pref not in picked:
            picked.append(pref)
    if not picked:
        for n in names:
            if (n.startswith("v(") or n.startswith("V(")) and n not in picked:
                picked.append(n)
    if not picked:
        picked = [n for n in names if n not in ("frequency", "time")]
    return picked[:max_vars]


# ---------------------------------------------------------------- 绘图（Pillow）
_FONT_CACHE = {}


def _font(size):
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.load_default(size)
        except TypeError:
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def _fmt(v):
    if v == 0:
        return "0"
    if abs(v) >= 1e6 or abs(v) < 1e-4:
        return "%.2g" % v
    return "%.4g" % v


def _downsample(x, y, max_pts=2000):
    if len(x) <= max_pts:
        return x, y
    step = int(math.ceil(len(x) / max_pts))
    return x[::step], y[::step]


def _draw_panel(draw, box, x, y, title, xlabel, ylabel, x_log=False):
    pad_l, pad_r, pad_t, pad_b = 48, 6, 24, 20
    px0, py0 = box[0] + pad_l, box[1] + pad_t
    px1, py1 = box[2] - pad_r, box[3] - pad_b
    if px1 <= px0 + 10 or py1 <= py0 + 10:
        return
    # 过滤 NaN/Inf（求解器发散残留）
    x, y = _clean(x, y)
    if len(x) == 0:
        draw.text((px0 + 4, py0 + 8), "(无有效数据)", fill=(120, 120, 120), font=_font(9))
        return
    xs = np.log10(np.maximum(x, 1e-30)) if x_log else np.asarray(x, dtype=float)
    xmin, xmax = float(np.min(xs)), float(np.max(xs))
    if xmin == xmax:
        xmax = xmin + 1.0
    ymin, ymax = float(np.min(y)), float(np.max(y))
    span = ymax - ymin
    if span == 0:
        span = 1.0
    ymin -= span * 0.05
    ymax += span * 0.05

    def tx(v):
        return px0 + (v - xmin) / (xmax - xmin) * (px1 - px0)

    def ty(v):
        return py1 - (v - ymin) / (ymax - ymin) * (py1 - py0)

    f9 = _font(9)
    f8 = _font(8)
    draw.rectangle([px0, py0, px1, py1], outline=(90, 90, 90))
    for i in range(4):
        xv = xmin + (xmax - xmin) * i / 3
        xd = 10 ** xv if x_log else xv
        draw.line([(tx(xv), py1), (tx(xv), py1 + 3)], fill=(60, 60, 60))
        lab = _fmt(xd)
        draw.text((tx(xv) - 12, py1 + 4), lab, fill=(40, 40, 40), font=f8)
    for i in range(4):
        yv = ymin + (ymax - ymin) * i / 3
        draw.line([(px0 - 3, ty(yv)), (px0, ty(yv))], fill=(60, 60, 60))
        lab = _fmt(yv)
        draw.text((2, ty(yv) - 5), lab, fill=(40, 40, 40), font=f8)
    draw.text((px0 + 2, box[1] + 2), "%s  |  %s" % (title, ylabel), fill=(0, 0, 0), font=f9)
    draw.text((px0 + (px1 - px0) // 2 - 24, py1 + 7), xlabel, fill=(40, 40, 40), font=f9)
    xs_, ys_ = _downsample(xs, y)
    pts = [(tx(v), ty(w)) for v, w in zip(xs_, ys_)]
    if len(pts) == 1:
        px, py = pts[0]
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(10, 80, 160))
    else:
        draw.line(pts, fill=(10, 80, 160), width=1)


def _draw_grid_image(sources, out_png, title, x_log=False, cols=4, cell=(380, 240)):
    """sources: [(label, x, y, ylabel)]"""
    if not HAS_IMG:
        return False
    n = len(sources)
    rows = int(math.ceil(n / cols))
    img = Image.new("RGB", (cols * cell[0], rows * cell[1]), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i, (label, x, y, ylabel) in enumerate(sources):
        r, c = divmod(i, cols)
        box = (c * cell[0], r * cell[1], (c + 1) * cell[0], (r + 1) * cell[1])
        _draw_panel(draw, box, x, y, label, "frequency (Hz)" if x_log else "time (s)",
                    ylabel, x_log=x_log)
    f10 = _font(10)
    draw.text((4, 2), title, fill=(0, 0, 0), font=f10)
    img.save(out_png)
    return True


def _clean(x, y, y_cap=1e12):
    """过滤 NaN/Inf/发散极端值（数值垃圾，双精度溢出的 1e308 也算）。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y) & (np.abs(x) < y_cap) & (np.abs(y) < y_cap)
    return x[ok], y[ok]


def _plot_one_pillow(x, sig, plot_vars, is_ac, out_png, title):
    sources = []
    for name in plot_vars:
        y = sig[name]
        if is_ac:
            y = 20 * np.log10(np.maximum(np.abs(y), 1e-30))
            ylab = "%s (dB)" % name
        else:
            y = np.real(y)
            ylab = name
        xc, yc = _clean(x, y)
        sources.append((name, xc, yc, ylab))
    return _draw_grid_image(sources, out_png, title, x_log=is_ac, cols=1, cell=(880, 260))


# ---------------------------------------------------------------- 批量
def summary_dir(raw_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    raws = sorted([f for f in os.listdir(raw_dir) if f.lower().endswith(".raw")])
    if not raws:
        print("目录无 raw: %s" % raw_dir)
        return
    fig_dir = os.path.join(out_dir, "figures")
    met_dir = os.path.join(out_dir, "metrics")
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(met_dir, exist_ok=True)
    rows = []
    grid_sources = []
    grid_is_ac = False
    for fname in raws:
        path = os.path.join(raw_dir, fname)
        try:
            extract_one(path, os.path.join(met_dir, fname + ".json"),
                        os.path.join(fig_dir, fname + ".png"), max_vars=2, title=fname)
            with open(os.path.join(met_dir, fname + ".json"), "r", encoding="utf-8") as f:
                mm = json.load(f)
            status = "OK"
            rows.append((fname, mm["meta"]["size_bytes"], mm["meta"]["sha256"],
                         mm["meta"]["plotname"], mm["meta"]["n_points"], status))
            # 汇总图源：主信号
            info, x, sig = parse_raw_data(path)
            pv = [n for n in pick_plot_vars(info, 1) if n in sig]
            if not pv:
                pv = list(sig.keys())[:1]
            if pv:
                name = pv[0]
                if mm["meta"]["is_ac"]:
                    grid_is_ac = True
                    y = 20 * np.log10(np.maximum(np.abs(sig[name]), 1e-30))
                    ylab = "%s (dB)" % name
                else:
                    y = np.real(sig[name])
                    ylab = name
                ok = np.isfinite(x) & np.isfinite(y)
                xc, yc = _clean(x, y)
                grid_sources.append((fname, xc, yc, ylab))
        except Exception as e:
            rows.append((fname, os.path.getsize(path), "", "?", 0, "FAIL: %s" % e))
            print("  [fail] %s: %s" % (fname, e))
    if grid_sources:
        _draw_grid_image(grid_sources, os.path.join(out_dir, "汇总网格图.png"),
                         "summary: %s (%d files)" % (os.path.basename(raw_dir.rstrip("\\/")), len(raws)),
                         x_log=grid_is_ac, cols=4, cell=(380, 240))
    _write_ledger(out_dir, raw_dir, rows, len(raws))
    print("完成: %d 个 raw → %s" % (len(raws), out_dir))


def _write_ledger(out_dir, raw_dir, rows, total):
    lines = [
        "# 归档记录：%s" % os.path.basename(raw_dir.rstrip("\\/")),
        "",
        "生成：%s。工具：raw_archive.py summary（先记录后删除流程）。" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "原始目录：`%s`。" % raw_dir,
        "raw 总数：%d。指标 JSON 在 metrics/，逐文件波形在 figures/，汇总网格图在 figures/汇总网格图.png。" % total,
        "",
        "| raw 文件 | 大小(MB) | SHA256 | 分析类型 | 点数 | 状态 |",
        "|---|---|---|---|---|---|",
    ]
    for fname, size, h, plot, np_, status in rows:
        lines.append("| %s | %.2f | %s | %s | %s | %s |" % (
            fname, size / 1048576.0, h or "—", plot, np_, status))
    lines += [
        "",
        "## 重跑配方",
        "",
        "每个 raw 均有同名 .cir（网表）+ .log（运行日志）保留在原目录。",
        "重跑：`ngspice -b <同名>.cir`（本机 ngspice：`D:\\ms_xsp\\s04_crosscheck_20261017\\Spice64\\bin\\ngspice.exe`）。",
        "删除 raw 前已按上表 SHA256 登记；.cir/.log/脚本不删除。",
        "",
        "## 删除执行记录",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 删除时间 | %s |" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "| 删除方式 | 按本账 SHA256 核验后删除 raw；配套 .cir/.log 保留 |",
        "| 删除后 | 本归档目录为唯一波形/指标留存；如需原始数据，按重跑配方重新生成 |",
    ]
    with open(os.path.join(out_dir, "归档记录.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "raw_extract" and len(sys.argv) >= 4:
        png = sys.argv[4] if len(sys.argv) > 4 else None
        extract_one(sys.argv[2], sys.argv[3], png)
        print("done: %s" % sys.argv[3])
    elif cmd == "raw_summary" and len(sys.argv) >= 4:
        summary_dir(sys.argv[2], sys.argv[3])
    elif cmd == "raw_check" and len(sys.argv) >= 3:
        raws = sorted(f for f in os.listdir(sys.argv[2]) if f.lower().endswith(".raw"))
        out = []
        for fname in raws:
            p = os.path.join(sys.argv[2], fname)
            try:
                info, x, sig = parse_raw_data(p)
                out.append({"file": fname, "ok": True, "size": os.path.getsize(p),
                            "sha256": sha256_file(p), "plot": info.get("plotname"),
                            "np": info["n_points"], "nv": info["n_variables"],
                            "flags": info.get("flags", ""), "x_min": float(x[0]),
                            "x_max": float(x[-1])})
            except Exception as e:
                out.append({"file": fname, "ok": False, "err": str(e)})
        outp = sys.argv[3] if len(sys.argv) > 3 else "raw_check.json"
        with open(outp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        ok = sum(1 for o in out if o["ok"])
        print("检查 %d 个：全量解析 %d，失败 %d → %s" % (len(out), ok, len(out) - ok, outp))
        for o in out:
            if not o["ok"]:
                print("  FAIL %s: %s" % (o["file"], o["err"]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
