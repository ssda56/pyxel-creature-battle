# 中文字体目录

把 `simhei.ttf` 放进这个目录，`src/ui/text.py` 会优先使用它。

不放也能跑：会依次回退到
`C:\Windows\Fonts\simhei.ttf` → `msyh.ttc` → `Deng.ttf` → `simsun.ttc`。

> **不要**把素材目录里的 `umplus_j12r.bdf` / `PixelMplus12-Regular.ttf` 复制过来：
> 它们是日文字体，缺简体字形，“精灵对战”会渲染成“精?小游”（已实测）。
