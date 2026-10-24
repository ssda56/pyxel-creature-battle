"""静态数据层：地图 / 精灵 / 道具 / 技能等**只读**数据表。

本批（T2）只有 :mod:`src.data.map_data`；后续批次在此目录下加
``species_data.py`` / ``item_data.py`` / ``skill_data.py``。

约定：数据表全部是**字面量**（dict / list / tuple），运行期只读不改。
"""
