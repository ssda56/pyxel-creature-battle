# 背景音乐（BGM）说明

本目录下的两个文件来自 **Pyxel 官方发行包自带的示例音乐**：

| 本仓库文件 | Pyxel 官方示例文件 | 作者 | 授权 |
|---|---|---|---|
| `bgm1.ogg` | `audio_bgm1.ogg` | Takashi Kitao | MIT |
| `bgm2.ogg` | `audio_bgm2.ogg` | Takashi Kitao | MIT |

二者**逐字节完全相同**（SHA256 一致），本仓库仅做了重命名以便代码引用。

- Pyxel 项目：https://github.com/kitao/pyxel （MIT License, © Takashi Kitao）
- 完整署名说明见仓库根目录的 [NOTICE](../../NOTICE)。

其余 15 个音效不是音频文件，而是由 `src/ui/sound.py` 用 MML 音源序列器**实时合成**的。
