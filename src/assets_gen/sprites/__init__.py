"""全部精灵 / 图块素材模块。

每个素材模块都必须导出 SPRITES: list[SpriteMatrix]，
由 sprite_base.bake_all() 统一烘焙。
"""
from src.assets_gen.sprites import creature_placeholder, player, tileset

ALL_SPRITES: list = list(tileset.SPRITES) + list(player.SPRITES) + list(creature_placeholder.SPRITES)

__all__ = ["ALL_SPRITES", "tileset", "player", "creature_placeholder"]
