# -*- coding: utf-8 -*-
r"""把外部生图产出转成游戏可用的字符画精灵。

用法（**必须用系统 Python**，项目 venv 里没有 Pillow）：
    C:\Users\1\AppData\Local\Programs\Python\Python312\python.exe tools\art_import.py art-inbox\creature_1_battle.png

流程：检测逻辑像素块 -> 抠洋红背景 -> 量化到 16 色调色板 -> 输出字符画 + 8 倍预览
约定见 docs/美术生图提示词.md
"""
from __future__ import annotations

import os
import sys

from PIL import Image

# 游戏调色板（与 src/assets_gen/palette.py 一致）
PALETTE = [
    (0x0b, 0x0b, 0x12), (0x16, 0x21, 0x3e), (0x3e, 0x7b, 0xd6), (0x1f, 0x6b, 0x2e),
    (0x4f, 0xa8, 0x45), (0x5b, 0x3a, 0x8e), (0x8a, 0x8a, 0x96), (0xff, 0xff, 0xff),
    (0xd8, 0x48, 0x48), (0xe0, 0x7b, 0x39), (0xf5, 0xe0, 0x50), (0x9b, 0xd4, 0x5b),
    (0x5a, 0xc8, 0xe8), (0x8a, 0x5a, 0x3c), (0xf2, 0x78, 0x9a), (0xd8, 0xd8, 0xe0),
]
# 字符 -> 调色板索引：'.'=透明, '1'..'9'=1..9, 'a'..'f'=10..15
INDEX_TO_CHAR = {i: (str(i) if 1 <= i <= 9 else "abcdef"[i - 10]) for i in range(1, 16)}

MAGENTA_MIN = 180  # 提纯洋红判定下限
ALPHA_MIN = 100


def is_magenta(p):
    r, g, b, a = p
    if a < ALPHA_MIN:
        return True
    return r >= MAGENTA_MIN and b >= MAGENTA_MIN and g <= 90


def nearest_index(rgb):
    r, g, b = rgb[:3]
    best, bd = 7, 1 << 30
    for i in range(1, 16):          # 跳过 0（透明键）
        pr, pg, pb = PALETTE[i]
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < bd:
            bd, best = d, i
    return best, bd ** 0.5


def detect_block_size(im):
    """返回让每个块内像素完全一致的最大整数块尺寸；找不到返回 1。"""
    w, h = im.size
    px = im.load()
    for bs in (32, 16, 8, 4, 2):
        if w % bs or h % bs:
            continue
        ok = True
        for by in range(0, h, bs):
            for bx in range(0, w, bs):
                base = px[bx, by]
                for y in range(by, by + bs):
                    for x in range(bx, bx + bs):
                        if px[x, y] != base:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            return bs
    return 1


def convert(path: str, out_dir: str) -> dict:
    im = Image.open(path).convert("RGBA")
    w, h = im.size

    # 颜色数（去重）——用于判断有无抗锯齿/渐变
    colors = im.getcolors(maxcolors=1 << 20) or []
    distinct = len(colors)

    bs = detect_block_size(im)
    lw, lh = w // bs, h // bs

    px = im.load()
    logi = [[px[c * bs + bs // 2, r * bs + bs // 2] for c in range(lw)] for r in range(lh)]

    rows, raw_used, err_sum, err_n = [], set(), 0.0, 0
    for r in range(lh):
        line = []
        for c in range(lw):
            p = logi[r][c]
            if is_magenta(p):
                line.append(".")
                continue
            idx, dist = nearest_index(p)
            raw_used.add((p[0], p[1], p[2]))
            err_sum += dist
            err_n += 1
            line.append(INDEX_TO_CHAR[idx])
        rows.append("".join(line))

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(out_dir, exist_ok=True)
    txt_path = os.path.join(out_dir, name + ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# %s  逻辑尺寸 %dx%d  块尺寸 %d\n" % (name, lw, lh, bs))
        f.write("# palette: '.'=透明, '1'-'9'=索引1-9, 'a'-'f'=索引10-15\n")
        f.write("ROWS = [\n")
        for line in rows:
            f.write('    "%s",\n' % line)
        f.write("]\n")

    # 8 倍预览
    prev = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    pp = prev.load()
    for r in range(lh):
        for c in range(lw):
            ch = rows[r][c]
            if ch == ".":
                pp[c, r] = (255, 0, 255, 255)
            else:
                idx = int(ch) if ch.isdigit() else 10 + "abcdef".index(ch)
                pp[c, r] = PALETTE[idx] + (255,)
    prev_path = os.path.join(out_dir, name + "_preview.png")
    prev.resize((lw * 8, lh * 8), Image.NEAREST).save(prev_path)

    mean_err = (err_sum / err_n) if err_n else 0.0
    magenta_ratio = sum(1 for r_ in rows for ch in r_ if ch == ".") / float(lw * lh)

    return {
        "name": name, "size": (w, h), "block": bs, "logical": (lw, lh),
        "distinct_colors": distinct, "raw_colors_used": len(raw_used),
        "mean_quant_error": mean_err, "magenta_ratio": magenta_ratio,
        "txt": txt_path, "preview": prev_path,
    }


def report(res):
    print("=" * 62)
    print("图片      :", res["name"])
    print("原尺寸    : %dx%d   逻辑网格: %dx%d   块尺寸: %d" % (res["size"] + res["logical"] + (res["block"],)))
    print("背景占比  : %.1f%%  (>=40%% 才算可抠)" % (res["magenta_ratio"] * 100))
    print("原图颜色数:", res["distinct_colors"], "(<=24 视为无抗锯齿)")
    print("量化误差  : %.1f  (平均 RGB 距离，越小越好)" % res["mean_quant_error"])
    checks = [
        ("背景可抠", res["magenta_ratio"] >= 0.40),
        ("无抗锯齿", res["distinct_colors"] <= 24),
        ("网格可识别", res["block"] in (8, 16, 32)),
        ("量化损失小", res["mean_quant_error"] <= 26),
    ]
    print("-" * 62)
    for label, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("-" * 62)
    print("字符画 :", res["txt"])
    print("预览图 :", res["preview"], " <- 请肉眼确认可辨认、属性色正确")
    return all(ok for _, ok in checks)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: art_import.py <png> [<png> ...]")
        raise SystemExit(2)
    out_dir = os.path.join("art-inbox", "_converted")
    all_ok = True
    for p in sys.argv[1:]:
        if not os.path.exists(p):
            print("找不到文件:", p)
            all_ok = False
            continue
        all_ok &= report(convert(p, out_dir))
    raise SystemExit(0 if all_ok else 1)
