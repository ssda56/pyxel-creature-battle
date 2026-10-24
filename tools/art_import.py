# -*- coding: utf-8 -*-
r"""把外部生图产出转成游戏可用的字符画精灵。

用法（**必须用系统 Python**，项目 venv 里没有 Pillow）：
    C:\Users\1\AppData\Local\Programs\Python\Python312\python.exe tools\art_import.py art-inbox\creature_1_battle.png --target 32

流程：
  1. 从四角取样识别背景色（不要求洋红）
  2. 从边缘泛洪标记背景（避免把主体内部的同色区误抠）
  3. 用容差检测逻辑像素块尺寸
  4. 归一化到 target×target（默认 32）：按块中心采样 + 多数投票降采样
  5. 每个像素量化到游戏 16 色（**排除索引 0，它是透明键**）
  6. 输出字符画矩阵 + 8/16 倍预览 + 自动体检报告

约定见 docs/美术生图提示词.md
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, deque

from PIL import Image

PALETTE = [
    (0x0b, 0x0b, 0x12), (0x16, 0x21, 0x3e), (0x3e, 0x7b, 0xd6), (0x1f, 0x6b, 0x2e),
    (0x4f, 0xa8, 0x45), (0x5b, 0x3a, 0x8e), (0x8a, 0x8a, 0x96), (0xff, 0xff, 0xff),
    (0xd8, 0x48, 0x48), (0xe0, 0x7b, 0x39), (0xf5, 0xe0, 0x50), (0x9b, 0xd4, 0x5b),
    (0x5a, 0xc8, 0xe8), (0x8a, 0x5a, 0x3c), (0xf2, 0x78, 0x9a), (0xd8, 0xd8, 0xe0),
]
INDEX_TO_CHAR = {i: (str(i) if 1 <= i <= 9 else "abcdef"[i - 10]) for i in range(1, 16)}
CHAR_TO_INDEX = {v: k for k, v in INDEX_TO_CHAR.items()}

BG_TOL = 26        # 背景容差
BLOCK_TOL = 34     # 块内允许的颜色抖动（抗锯齿/压缩噪点）


def nearest_index(rgb):
    """到调色板的最近色；跳过索引 0（透明键）。"""
    r, g, b = rgb[:3]
    best, bd = 7, 1 << 30
    for i in range(1, 16):
        pr, pg, pb = PALETTE[i]
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < bd:
            bd, best = d, i
    return best, bd ** 0.5


def detect_bg(im):
    """四角取样，取出现最多的颜色作为背景色。"""
    w, h = im.size
    pts = [(3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4), (w // 2, 3), (3, h // 2)]
    return Counter(im.getpixel(p) for p in pts).most_common(1)[0][0]


def bg_mask(im, bg, tol=BG_TOL):
    """从边缘泛洪，标记背景（只沿连通区域扩散）。"""
    w, h = im.size
    px = im.load()
    near = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            near[y][x] = all(abs(p[i] - bg[i]) <= tol for i in range(3))
    mask = [[False] * w for _ in range(h)]
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if near[y][x] and not mask[y][x]:
                mask[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if near[y][x] and not mask[y][x]:
                mask[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and near[ny][nx] and not mask[ny][nx]:
                mask[ny][nx] = True
                q.append((nx, ny))
    return mask


def detect_block(im, mask):
    """让每个块内颜色差异都在容差内的最大块尺寸。"""
    w, h = im.size
    px = im.load()
    for bs in (64, 32, 16, 8, 4, 2):
        if w % bs or h % bs:
            continue
        ok = True
        for by in range(0, h, bs):
            for bx in range(0, w, bs):
                if mask[by + bs // 2][bx + bs // 2]:
                    continue
                r0, g0, b0 = px[bx, by][:3]
                for y in range(by, by + bs, max(1, bs // 4)):
                    for x in range(bx, bx + bs, max(1, bs // 4)):
                        if mask[y][x]:
                            continue
                        r, g, b = px[x, y][:3]
                        if abs(r - r0) > BLOCK_TOL or abs(g - g0) > BLOCK_TOL or abs(b - b0) > BLOCK_TOL:
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


def majority(cells):
    """cells: [(rgb, is_bg)] -> 取多数；背景过半则返回 None。"""
    bg_n = sum(1 for _, b in cells if b)
    if bg_n * 2 > len(cells):
        return None
    return Counter(c for c, b in cells if not b).most_common(1)[0][0]


def convert(path, out_dir, target=32, crop_pad=0):
    im0 = Image.open(path).convert("RGB")
    bg = detect_bg(im0)
    mask = bg_mask(im0, bg)
    bs = detect_block(im0, mask)
    w, h = im0.size
    lw, lh = w // bs, h // bs

    # 块中心采样得到逻辑图
    px = im0.load()
    logi = []
    for by in range(lh):
        row = []
        for bx in range(lw):
            cx, cy = bx * bs + bs // 2, by * bs + bs // 2
            row.append((px[cx, cy][:3], mask[cy][cx]))
        logi.append(row)

    # 裁掉四周纯背景（留 pad）
    xs = [x for y in range(lh) for x in range(lw) if not logi[y][x][1]]
    ys = [y for y in range(lh) for x in range(lw) if not logi[y][x][1]]
    if xs:
        x0, x1 = max(0, min(xs) - crop_pad), min(lw - 1, max(xs) + crop_pad)
        y0, y1 = max(0, min(ys) - crop_pad), min(lh - 1, max(ys) + crop_pad)
        logi = [row[x0:x1 + 1] for row in logi[y0:y1 + 1]]
        lh, lw = len(logi), len(logi[0])

    # 归一化到 target×target（多数投票）
    out_rows = []
    for oy in range(target):
        sy0 = oy * lh // target
        sy1 = max(sy0 + 1, (oy + 1) * lh // target)
        line = []
        for ox in range(target):
            sx0 = ox * lw // target
            sx1 = max(sx0 + 1, (ox + 1) * lw // target)
            cells = [logi[y][x] for y in range(sy0, sy1) for x in range(sx0, sx1)]
            c = majority(cells)
            if c is None:
                line.append(".")
            else:
                idx, _ = nearest_index(c)
                line.append(INDEX_TO_CHAR[idx])
        out_rows.append("".join(line))

    err_sum, err_n = 0.0, 0
    for r in range(target):
        for c in range(target):
            ch = out_rows[r][c]
            if ch == ".":
                continue
            idx = CHAR_TO_INDEX[ch]
            oy0, oy1 = r * lh // target, max(r * lh // target + 1, (r + 1) * lh // target)
            ox0, ox1 = c * lw // target, max(c * lw // target + 1, (c + 1) * lw // target)
            cells = [logi[y][x] for y in range(oy0, oy1) for x in range(ox0, ox1)]
            m = majority(cells)
            if m is None:
                continue
            pr, pg, pb = PALETTE[idx]
            err_sum += ((m[0] - pr) ** 2 + (m[1] - pg) ** 2 + (m[2] - pb) ** 2) ** 0.5
            err_n += 1

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(out_dir, exist_ok=True)
    txt = os.path.join(out_dir, name + ".txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write("# %s  逻辑块=%d  归一化后=%dx%d\n" % (name, bs, target, target))
        f.write("# '.'=透明, '1'-'9'=索引1-9, 'a'-'f'=索引10-15\n")
        f.write("ROWS = [\n")
        for line in out_rows:
            f.write('    "%s",\n' % line)
        f.write("]\n")

    prev = Image.new("RGB", (target, target), (255, 0, 255))
    pp = prev.load()
    for r in range(target):
        for c in range(target):
            ch = out_rows[r][c]
            if ch != ".":
                pp[c, r] = PALETTE[CHAR_TO_INDEX[ch]]
    prev_path = os.path.join(out_dir, name + "_%d_preview.png" % target)
    prev.resize((target * 12, target * 12), Image.NEAREST).save(prev_path)

    used = sorted({ch for row in out_rows for ch in row if ch != "."})
    return {
        "name": name, "src": im0.size, "bg": bg, "block": bs,
        "logical_cropped": (lw, lh), "target": target,
        "colors": len(used), "mean_err": (err_sum / err_n) if err_n else 0.0,
        "fill": 1.0 - sum(1 for row in out_rows for ch in row if ch == ".") / float(target * target),
        "txt": txt, "preview": prev_path,
    }


def report(r):
    print("=" * 64)
    print("源图      :", r["name"], "%dx%d" % r["src"])
    print("背景色    :", r["bg"], " 块尺寸:", r["block"], " 裁边后逻辑:", "%dx%d" % r["logical_cropped"])
    print("输出      : %dx%d  实际用色 %d 色  主体填充率 %.1f%%  量化误差 %.1f"
          % (r["target"], r["target"], r["colors"], r["fill"] * 100, r["mean_err"]))
    print("-" * 64)
    print("字符画:", r["txt"])
    print("预览图:", r["preview"], " <- 12 倍放大")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--target", type=int, default=32)
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--out", default=os.path.join("art-inbox", "_converted"))
    a = ap.parse_args()
    for f in a.files:
        if not os.path.exists(f):
            print("找不到:", f)
            continue
        report(convert(f, a.out, a.target, a.pad))
