"""18 只精灵的**成品字符画**（方案 D：程序化字符画，批 4 重绘）。

每只精灵两张图，名字与旧占位版**完全一致**（场景代码按名字取图）：

    战斗图  creature_{id}_battle  32x32
    图  标  creature_{id}_icon    16x16

画法
----
先用 `Canvas`（椭圆 / 三角 / 直线）拼出剪影，再压一条色 5 的椭圆环把
头与身体分开，统一 `outline()` 加一圈外描边，最后才补眼睛、嘴、高光等细节，
免得细节被描边吃掉。导出成本文件里的**字面量字符画**，运行期零解析开销。

配色约定（见 palette.py）
----------------------
- `'.'` 恒为透明；**色 0 绝不能出现在画面里**（它是 blt 的透明键，会整块消失）。
- 描边统一 **色 5**；每只身体大面积色 = 它的属性主色（TYPE_COLORS）。
- 眼睛一律「白色眼白 + 色 1 深蓝瞳孔 + 白色高光」：若瞳孔直接用色 5，
  会和描边同色，远看是一对空心方块，眼神全丢。

精灵 id 与《数值设定.md》§1.2 一致：
    1 小火狮 火 / 2 水滴滴 水 / 3 兔小子 草 / 4 小狮鹫 风
    5 独角兽 光 / 6 三头犬 暗 / 7 不死鸟 火 / 8 闪电小子 雷
新增 10 只（见 docs/02-新增10只精灵规划.md §三）：
    9 雾尾狐 火 / 10 涟漪豚 水 / 11 灯火鳅 水 / 12 花刃忍 草 / 13 荆星芽 草
    14 雏羽啾 风 / 15 夜幕翼 暗 / 16 绒医团 光 / 17 导线蛇 雷 / 18 雷云团 雷
"""

from __future__ import annotations

from src.assets_gen.sprite_base import SpriteMatrix

#: 精灵共用调色板：字符 -> 调色板索引
PALETTE: dict[str, int] = {
    ".":  None, # 透明（不写像素）
    "K":  5,    # 深紫 DARK_PURPLE：**描边**，也是头身分隔线与口鼻暗部
    "E":  1,    # 深蓝 DEEP_BLUE：瞳孔（比描边更深，眼睛才有神）
    "O":  9,    # 橙 ORANGE：火属性主色
    "R":  8,    # 红 RED：鬃毛 / 翼尖 / 嘴 / 三头犬的发光眼
    "Y":  10,   # 黄 YELLOW：雷主色、火焰尖端、金角与金喙
    "W":  7,    # 白 WHITE：光主色、眼白、高光、尾羽
    "B":  12,   # 浅蓝 LIGHT_BLUE：水属性主色
    "N":  2,    # 蓝 BLUE：风属性主色、水与羽翼的暗部
    "L":  11,   # 浅绿 LIGHT_GREEN：草属性主色
    "G":  4,    # 中绿 GREEN：兔子耳间的叶子
    "D":  3,    # 深绿 DARK_GREEN：叶脉
    "P":  14,   # 粉 PINK：暗属性主色、内耳、腮红、鼻孔
    "T":  15,   # 浅灰 LIGHT_GRAY：口鼻、肚皮、身体阴影
    "M":  13,   # 棕 BROWN：独角兽的蹄
}


# ======================================================================
# 1 小火狮（火）—— 圆滚幼狮：橙脸压在红色火焰鬃毛正中，鬃毛外缘伸出黄色火舌，右侧一簇尾焰
# 战斗图用色索引：[1, 5, 7, 8, 9, 10, 14, 15]
# 图标用色索引：  [1, 5, 7, 8, 9, 10, 14]
# ======================================================================
FIRE_LION_BATTLE = [
    "................................",
    "...............KYK..............",
    ".......K.......KYK.......K......",
    "......KRK...KKKYYYKKK...KRK.....",
    "......KYRKKKRRRYYYRRRKKKRYK.....",
    "......KYYRRRRRYYYYYRRRRRYYK.....",
    "......KYYYYRRYYYYYYYRRYYYYK.....",
    "......KYYYYYYRRRRRRRYYYYYYK.....",
    ".....KRYYYRYRRRRKRRRRYRYYYRK....",
    ".....KRYYYRRRKKKOKKKRRRYYYRK....",
    "....KRRYYRRKKROOOOORKKRRYYRRK...",
    "....KRRYRRWWWWWOOWWWWWKRRYRRK...",
    "..K.KRYRRRWWWEWOOWWWEWKRRRYRK.K.",
    ".KYKKRRRRRWEEEWOOWEEEWKRRRRRKKY.",
    "..KYYYYYRKWEEEWOOWEEEWOKRYYYYYK.",
    "..KYYYYRRRWEEEWOOWEEEWKRRRYYYYK.",
    "..KYYYRRRRWWWWWOTWWWWWKRRRRYYYK.",
    "..KYYYRRRRKOOTTPPPTTOOKRRRRYYYK.",
    "..KYYRRRRRRKTTTPPPTTTKRRRRRRYYY.",
    "..KYYKRRRRRYRTTTTTTTRYRRRRRKYYY.",
    "..KYKKRRRRRYRRRKTKRRRYRRRRRKKYY.",
    "..KYK.KRRRYYYRRRRRRRYYYRRRK.KYR.",
    "...K...KRRYYYRRRRRRRYYYRRKOKYRR.",
    "........KYYYYYRRRRRYYYYYOOOYRRR.",
    ".......KYYYYYYYRRRYYYYYYYOOOOYR.",
    "........KOOOOTTTRTTTOOOOOOOOOKY.",
    ".........KOOTTTTTTTTTOOKKKOKK.K.",
    ".........KOOOOOOTTOOOOOOK.K.....",
    ".........KOOOKKOTKKOOOOOK.......",
    ".........KOOOKKOOKKOOOOOK.......",
    ".........KOOOKKOKKKOOOOOK.......",
    "................................",
]

FIRE_LION_ICON = [
    "................",
    ".......KYK......",
    ".....KKKYKKK....",
    "..K.KRRRYYRRK.K.",
    ".KYKRRRYKYYRRKY.",
    ".KYRRRKKOKKRRRY.",
    ".KYYWWWWWWWWRYY.",
    ".KYYWWEWWWEWYYY.",
    ".KYYWEEWWEEWKYY.",
    ".KYRWEEWWEEWRRY.",
    ".KYRWWWPPWWWRRY.",
    "..KRRYKKOKKYRRK.",
    "...KYYKRKRYYYK..",
    "..KYYYYYRYYYYYK.",
    "...KKKKKRKKKKK..",
    "................",
]


# ======================================================================
# 2 水滴滴（水）—— 竖向水滴：顶部 1~2 像素尖顶，向下单调加宽，最宽处在下半部
# 战斗图用色索引：[1, 2, 5, 7, 12, 14]
# 图标用色索引：  [1, 5, 7, 12]
# ======================================================================
WATER_DROP_BATTLE = [
    "................................",
    "...............KK...............",
    "..............KBBK..............",
    "..............KBBK..............",
    ".............KBBBBK.............",
    ".............KWWBBK.............",
    "............KWWBBBBK............",
    "............KWWBBBBK............",
    "...........KWWBBBBBBK...........",
    "..........KKWWBBBBBBK...........",
    ".........KWWBBBBBBBBBK..........",
    ".........KWWBBBBBBBBBK..........",
    ".........KWWBBBBBBBBBKK.........",
    "........KWWBBBBBBBBBBBBK........",
    "........KBBBBBBBBBBBBBNK........",
    ".......KBBBBBBBBBBBBBBBNK.......",
    ".......KBBBBBBBBBBBBBBBNK.......",
    "......KBBWWWWBBBBBBWWWWBNK......",
    "......KBBWWEWBBBBBBWWEWBNK......",
    "......KBBWEEWBBBBBBWEEWBNK......",
    ".....KBBBWEEWBBBBBBWEEWBBNK.....",
    ".....KBBBWWWWBBBBBBWWWWBBNK.....",
    ".....KBPPBBBBBBBBBBBBBBPPK......",
    "......KPPBBBBBBNNNBBBBBPPK......",
    ".......KBBBBBBBBBBBBBBBNK.......",
    "........KKBBBBBBBBBBBNKK........",
    "..........KKBBBBBBNKKK..........",
    ".......KK...KKKKKKK....KK.......",
    "......KBBK............KBBK......",
    "......KBBK............KBBK......",
    ".......KK..............KK.......",
    "................................",
]

WATER_DROP_ICON = [
    "................",
    ".......KK.......",
    "......KBBK......",
    "......KBBK......",
    ".....KWBBBK.....",
    ".....KWBBBK.....",
    "....KWBBBBBK....",
    "...KWBBBBBBBK...",
    "..KBWWBBBBWWBK..",
    ".KBBWEBBBBEWBBK.",
    "..KBBBBBBBBBBK..",
    "...KBBBBBBBBK...",
    "....KKKKKKKK....",
    "................",
    "................",
    "................",
]


# ======================================================================
# 3 兔小子（草）—— 瘦高绿兔：V 形外张的长耳（内耳粉）、耳间一片叶子、白绒球尾巴
# 战斗图用色索引：[1, 3, 4, 5, 7, 11, 14]
# 图标用色索引：  [1, 4, 5, 7, 11, 14]
# ======================================================================
GRASS_RABBIT_BATTLE = [
    "................................",
    "...K...........K...........K....",
    "..KLK.........KDK.........KLK...",
    "...KKK.......KKDKK.......KKK....",
    "...KLPK.....KGGDGGK.....KPLK....",
    "....KKK....KGGGDGGGK....KKK.....",
    "....KLPK....KGGDGGK....KPLK.....",
    "....KLPK.....KKDKK.....KPLK.....",
    ".....KLPK......K......KPLK......",
    ".....KLPK.............KPLK......",
    "......KPPK.....K.....KPPK.......",
    "......KLPK..KKKKKKK..KPLK.......",
    "......KLPPKKKKKLKKKKKPPLK.......",
    ".......KPPKKLLLLLLLKKPPK........",
    ".......KPKWWWWWLWWWWWKPK........",
    ".......KLKWWWEWLWWWEWKLK........",
    ".......KKLWEEEWLWEEEWLKK........",
    "........KKWEEEWLWEEEWKK.........",
    "........PKWWWWWLWWWWWKP.........",
    "......PPPPPLLLPPLLLLPPPPP.......",
    "........PKKKLLPPLLLKKKP.........",
    "..........KKKKKLKKKKK...........",
    "..........KLLLLKLLLLK...K.......",
    "..........KLLGGGGLLLK.KKWKK.....",
    ".........KLLLLLDLLLLKKWWWWWK....",
    ".........KLLLLLLLLLLLKWWWWWK....",
    "........KKLLLLLLLLLLKWWWWWWWK...",
    ".......KLLLLLLLLLLLLLKWWWWWK....",
    "......KLLLLLLLLLLLLLLLWWWWWK....",
    ".......KLLLLLLLLLLLLLLLKWKK.....",
    "........KKLKKKKLKLLLLLK.K.......",
    "................................",
]

GRASS_RABBIT_ICON = [
    "................",
    ".KLKK.......KKL.",
    "..KKPK..K..KPKK.",
    "..KLKK.KGKKKKLK.",
    "...KLPKGGGGPLK..",
    "...KLKPKKKPKLK..",
    "....KLKKLKKKK...",
    "....KKLLLLLLKK..",
    "....KWWEWWEWKK..",
    "...KKWEEWEEWLKK.",
    "....PWEEWEEWPK..",
    "...PPPWWPWWPPP..",
    "....PKLLLLLLPK..",
    ".....KKKLKKKK...",
    "......KKKKKK....",
    "................",
]


# ======================================================================
# 4 小狮鹫（风）—— 半鹰半狮：蓝色羽身 + 白色胸脯与尾羽，横向展开的双翼，橙色钩喙
# 战斗图用色索引：[1, 2, 5, 7, 9, 10]
# 图标用色索引：  [1, 2, 5, 7, 9, 10]
# ======================================================================
WIND_GRIFFIN_BATTLE = [
    "................................",
    "..........K..........K..........",
    ".........KYK........KYK.........",
    "..........KYK.......KK..........",
    "..K.......KYYK.....KYK..........",
    ".KWK......KYYYK.K..KYK........K.",
    "..KNK......KYYYKKKKYYK.......KN.",
    "..KWNK.....KYYKKNKKKK.......KNW.",
    "..KWWNK....KYKNNNNNNKK.....KNWW.",
    "..KWWNNK...KKNNNNNNNNKK...KNNWW.",
    "..KWWWNNK.KWWWWWNWWWWWKK.KNNWWW.",
    "..KWWWWNNKKWWWEWNWWWEWKKKNNWWWW.",
    "..KWWWWNNNKWEEEWNWEEEWKKNNNWWWW.",
    "..KWWWWWNNKWEEEWNWEEEWNKNNWWWWW.",
    "...KWWWWWNNWEEEWWWEEEWKNNWWWWWK.",
    "...KWWWWWWNWWWWWWWWWWWKNWWWWWWK.",
    "...KWWWWNNNNKNWWWWWWNKNNNNWWWWK.",
    "...KWWWNNNWNNKNNWONNKNNWNNNWWWK.",
    "...KWWWNNNWKKKKKOKKKKKKWNNNWWWK.",
    "...KWWNNNKKW.KNNONNNK.WKKNNNWWK.",
    "...KWNNKK..WKNNNNNNNNKW..KKNNWK.",
    "...KWKK....WNNNNWNNNNNW....KKWK.",
    "....K......KWNNWWWWNNWK......K..",
    "..........KNWNWWWWWWNWNK........",
    "...........KNWWWWWWWWNK.........",
    "...........KNNWWWWWWNNK.........",
    "............KNNWWWWNNK..........",
    ".............KYYWNYYK...........",
    ".............KYYWWYYK...........",
    "............KKYYWWYYKK..........",
    "..........KKWWWWWWWWWWKK........",
    "................................",
]

WIND_GRIFFIN_ICON = [
    "................",
    "..........K.....",
    ".K.......KYK....",
    ".WK.....KYK...K.",
    ".KWK...KNYK..KW.",
    ".KWWKWWWWWWWKWW.",
    ".KWWWWWEWWEWWWW.",
    ".KWWWWEEWEEWWWW.",
    ".KWWNNNOOOONNWW.",
    ".KWNNKNNOONNNNW.",
    ".KWKKKNNONNNKKW.",
    "..K.KNNNWWNNNKK.",
    ".....KNWWWWNK...",
    ".....KNNWWNNK...",
    "......KNWNNK....",
    "................",
]


# ======================================================================
# 5 独角兽（光）—— 白色胖马：四足横立，额头一支金黄尖角，粉红鬃毛与尾巴
# 战斗图用色索引：[1, 5, 7, 10, 13, 14, 15]
# 图标用色索引：  [1, 5, 7, 10, 14, 15]
# ======================================================================
LIGHT_UNICORN_BATTLE = [
    "................................",
    "......................KYK.......",
    "......................KYK.......",
    "..................K...KYK.......",
    ".................KWK.KYTYK......",
    "..................KWKKTYYK......",
    "..................KPWYTYYYK.....",
    ".................KPPPTWYYYK.....",
    ".................KPPPYYYYYYK....",
    ".................KPPPKKWKKKK....",
    ".................KPPPWWWWWWKK...",
    "................KPPPPPWWWEWKK...",
    ".................KPPPWWWEEWWKK..",
    ".................KPPPWWWEEWWK...",
    ".................KPPPWWWWWWPWK..",
    "................KKPPPKKWKWWWK...",
    ".....K.....KKKKKWPPPPPKKKKWK....",
    "....KPK..KKWWWWWWWPPPWWWK.K.....",
    "...KPPPKKWWWWWWWWWPPPWWWK.......",
    "..KPPPPPWWWWWWWWWWWPWWWWWK......",
    "..KPPPPWWWWWWTWWWWWWWWWWWWK.....",
    ".KPPPPPWWWWWTWWWTWWWWWWWWWK.....",
    "..KPPPWWWWWTTTTTTTTTTWWWWWWK....",
    "..KPPPPWWWTTTTTTTTTTTWWWWWK.....",
    "..KPPPPWWTTTTTTTTTTTTWWWWWK.....",
    ".KPPPPPWWWTTTTTTTTTTWWWWWK......",
    "..KPPPKWWWWTTTTTTTTTTTWWWK......",
    "..KPPPKWWWKWWWWWTWWWWWWWWK......",
    "...KPKKWWWKWWWKKWKWWWKWWWK......",
    "....K.KMMMKMMMK.KKMMMKMMMK......",
    ".......KKK.KKK....KKK.KKK.......",
    "................................",
]

LIGHT_UNICORN_ICON = [
    "................",
    ".........K......",
    "........KYK.....",
    "........KTKK....",
    ".....KKKKTYKK...",
    "....KPPKTWWWKK..",
    "....KPPKTWEWKK..",
    "....KPPWWEEWYKK.",
    "....KPPKWWWWWWK.",
    "...KPPPKWWWWWPW.",
    "...KPPPWKWKWWWK.",
    "..KWPPWWWKWWWK..",
    ".KWWWWWWWWWWWWK.",
    "..KWWWWWWWWWWK..",
    "...KWWWWWWWWK...",
    "................",
]


# ======================================================================
# 6 三头犬（暗）—— 深粉躯体 + 三个并排的头（中间高两边低），深紫口鼻，红色发光眼与小尖牙
# 战斗图用色索引：[5, 7, 8, 14]
# 图标用色索引：  [5, 7, 8, 14]
# ======================================================================
DARK_CERBERUS_BATTLE = [
    "................................",
    "................................",
    "...........K..........K.........",
    "..........KPKK......KKPK........",
    "...........KPPKK.KKKPPK.........",
    "............KPPPKPPPPK..........",
    "..K.........KPPPKKPPPK..........",
    ".KPKK.......KKPKKKKPKK.......KK.",
    "..KPPKKK.KKKPPPKPKKPPPKKK.KKKPP.",
    "...KPPPPKPPPPKKPPPPKKPPPPKPPPPK.",
    "...KPPPKKKPPPKWRPWRKKPPPKKKPPPK.",
    "....KPKKKKKPKKRRPRRPKKPKKKKKPK..",
    "....KPKKPKKPKKKPKPPKKKPKKPKKPK..",
    "....KKPPPPPKKKKPKKPKKKKPPPPPKK..",
    "....KWRPPWRKK.KWWKWK.KWRPPWRKKK.",
    "...KKRRPPRRPKK.KKKK.KKRRPPRRPKK.",
    "....KKPPKPPKK...KK...KKPPKPPKKK.",
    "....KKPKKKPKKKKKPKKKKKKPKKKPKKK.",
    ".....KWKWKWPPPPPPPPPPPPWKWKWKKK.",
    "......KKKKPPPPPPPPPPPPPPKKKKKKK.",
    "......KPKPPPPPPPPPPPPPPPPKPKKKK.",
    "......KPPPPPPPPPPPPPPPPPPPPK.KK.",
    ".....KPPPPPPPPPPPPPPPPPPPPPPK.K.",
    "......KPPPPPPPPPPPPPPPPPPPPK....",
    "......KPPPPPPPPPPPPPPPPPPPPK....",
    "......KPPPPPPPPPPPPPPPPPPPPK....",
    "......KPPPKPPPPPPPPPPPPKPPPK....",
    "......KKKKKKKKKKPKKKKKKKKKKK....",
    ".......KKK..KKK.K..KKK..KKK.....",
    "................................",
    "................................",
    "................................",
]

DARK_CERBERUS_ICON = [
    "................",
    "......K....K....",
    ".....KPK..KPK...",
    ".K....KPKKPK....",
    ".PK...KPKPPK....",
    ".KPKKKPKPKKPKKK.",
    ".KPPKPPWPWKPPKP.",
    ".KKKPKKRPRPKKPK.",
    ".KRRPRPKKKKRRPR.",
    ".KKPKPKKKKKKPKP.",
    ".KKKKKKPPPPKKKK.",
    "..KPKPPPPPPPPKP.",
    ".KPPPPPPPPPPPPP.",
    "..KPPPPPPPPPPPP.",
    "...KPPPPPPPPPPK.",
    "................",
]


# ======================================================================
# 7 不死鸟（火）—— 侧视火鸟：举起的金色大翼（红色翼尖），橙身长尾羽，金色喙朝右
# 战斗图用色索引：[1, 5, 7, 8, 9, 10]
# 图标用色索引：  [1, 5, 7, 8, 9, 10]
# ======================================================================
PHOENIX_BATTLE = [
    "................................",
    "...................K......K.....",
    "....K.............KRK.K..KRK....",
    "...KRK.............KKKYK.KRK....",
    "....KK.............KRKYK.KRK....",
    "....KRK............KRRYKKRRK....",
    "....KRRK............KRYYKRRK....",
    "....KRRRK...........KYYYRRRK....",
    "....KRRROK..........KRYYRRRK....",
    ".....KRRROK.........KRYYYRRK....",
    ".....KRRRROK.......KKWWWWOYKK...",
    ".....KRRRRORK......KKWWEWOYYYKK.",
    ".....KRRRRROYK....KKOWEEWOYYYYY.",
    ".....KRRRRRYOYKK...KKWEEWOYYYKK.",
    ".....KRORRYYYOYOKKKKKWWWWOYKK...",
    "......KROOYYYYOYOOOKKKKOKKK.....",
    "......KRRYYYOOYYYYOOOK.K........",
    "......KRYYYYRYYOOOOOOK..........",
    "......KRYYRRRRYOOOOOOK..........",
    "......KRKORRRYROOOOOOOK.........",
    ".......KKRRRYRRROOOOOK..........",
    ".........KRRYRROOOOOOK..........",
    "........KKRYRRROOOOOOK..........",
    ".......KRRKOROOOOOOOK...........",
    ".....KKRRRRKOOOOOOOK............",
    "....KRRRRRRKKYYOKYYK............",
    "..KKRRRRRRRYKYYKKYYK............",
    ".KRKKKKRRRRYKYYKKYYK............",
    "..K..KRRRRYYKYYKKYYK............",
    "....KRRRKKYKYYYYYYYYK...........",
    "...KRRKKKYK.KKKKKKKK............",
    "................................",
]

PHOENIX_ICON = [
    "................",
    ".K......RK......",
    ".RK.....KRKK....",
    ".KRK....KRRKKK..",
    ".KRRK...KWWWWKK.",
    ".KRRRKK.KWWEWYK.",
    ".KRRRRRKKWEEWYY.",
    "..KRRRYKOWWWWYY.",
    "..KRRYOOOOOKKK..",
    "..KRYYOOOOOOK...",
    "..KRKOOOOOOOOK..",
    "...K.KOOOOOOK...",
    ".....KOOOOOOK...",
    "......KYOOYYK...",
    "......KYOKYYK...",
    "................",
]


# ======================================================================
# 8 闪电小子（雷）—— 圆滚黄色电气体，头顶两只闪电角，白色圆脸颊，右侧锯齿闪电尾
# 战斗图用色索引：[5, 7, 8, 9, 10]
# 图标用色索引：  [1, 5, 7, 8, 10]
# ======================================================================
THUNDER_KID_BATTLE = [
    "................................",
    ".......K...........K............",
    "......KYK.........KYK...........",
    ".......KK.........KK............",
    ".......KYK.......KYK............",
    ".......KYYK.....KYYK............",
    "........KYK.....KYK.............",
    "........KYYK...KYYK.............",
    "........KYYYK.KYYYK.............",
    "........KYYYYKYYYYK.............",
    ".........KKKKKKKKK..............",
    ".........KKKKYKKKK..............",
    "........KYOYYYYYOYK.............",
    ".......KYYOYYYYYOYYK.K..........",
    "......KYYYOYYYYYOYYYKYKK........",
    ".....KYYYYOYYYYYOYYYYKYYKK......",
    "....KYWWKKWYYYYWWKKWYYKYYYYYY...",
    "....KYWKKKWYYYYWKKKWYYKYYYYKK...",
    "....KYWKKKWYYYYWKKKWYYKYYYK.....",
    "...KYYWKKKWYYYYWKKKWYYYKYK......",
    "....WYWWWWWYYYYWWWWWYYWKYYK.....",
    "...WWWYYYYYYYYYYYYYYYWWWYYYKK...",
    "..WWWWWYYYYYYYYYYYYYWWWWWYYYY...",
    "...WWWYYYYYYRYRYYYYYYWWWYYYKK...",
    "....WKYYYYYYYRYYYYYYYKWKYYK.....",
    "......KYYYYYYYYYYYYYK..KYK......",
    "......KKYYYYYYYYYYYKK...K.......",
    ".....KYYYYOYYOYYOYYYYK..........",
    "....KYYYYYYYKYKYYYYYYYK.........",
    ".....KYYYYYK.K.KYYYYYK..........",
    "......KKYKK.....KKYKK...........",
    "................................",
]

THUNDER_KID_ICON = [
    "................",
    "..KYK......KYK..",
    "...KYK.....KK...",
    "...KYYK...KYK...",
    "....KYYK.KYYK...",
    "....KYYYKYYYKK..",
    "....KYYYYYYKYYK.",
    "...KYYYYYYYYYYY.",
    "..KYWWEWWWEWYK..",
    "..KYWEEWWEEWYK..",
    ".KYWWEEWWEEWYWK.",
    "..KWWWWWWWWWYW..",
    "..WWWYYYYYYYWWW.",
    "..KWYYYRRYYYYW..",
    "...WYYYYYYYYKW..",
    "................",
]


# ======================================================================
# 9 雾尾狐（火）—— 低伏起跑的小火狐：大尖耳、前爪离地，尾巴占右侧 1/3，尾尖由橙渐变成黄烟团；烟只做轮廓外缘 3 个圆
# 耳内红、腹浅灰，眼睛白圈 + 深蓝瞳孔
# 战斗图用色索引：[1, 5, 7, 8, 9, 10, 15]
# 图标用色索引：  [1, 5, 7, 8, 9, 10, 15]
# ======================================================================
MIST_FOX_BATTLE = [
    "................................",
    "...K.......K.............K......",
    "..KOK.....KOK...........KRK.....",
    "..KOK.....KOK..........KRRRKKK..",
    "..KORK...KROK...........KRKYYYK.",
    "..KORK...KROK............KKYYYK.",
    "..KOROK..KROOK............KYYYK.",
    "..KORRK.KORROK...........KYYYK..",
    "..KORROKKORROK...........KYYYRK.",
    "..KORROKOORROOK.........KYYYRRR.",
    "..KORRROORRRROK.......KKYYYYKRK.",
    "..KOOOOOOOOOOOK......KYYYYYYKK..",
    ".KOWWWWOOWWWWKOK.....KYYYYYOOK..",
    "..KWEEWOOWEEWOK.....KYYYYYOOK...",
    "..KWEWWOOWEWWOK.....KKYYYYOOK...",
    "..KWWWWOOWWWWOK....KOOOYOOOK....",
    "...KOOOOOOOOOKKKKKKOOOOOOOK.....",
    "...KOOOOKKOOOOOOOOOOOOOOOOK.....",
    "....KOOOWOOOOOOOOOOOOOOOOK......",
    ".....KKOOOOOOOOOOOOOOOOOK.......",
    ".....KOOTTTTTOOOOOOOOOOK........",
    "....KOTTTTTTTTTOOOOOOOK.........",
    "...KOOTTTTTTTTTOOOOOOK..........",
    "...KOOTTTTTTTTTOOOOOK...........",
    "...KOOOOTTTTTOOOOOOKKK..........",
    "...KOOOOKKOOOOOOOOOTTTK.........",
    "...KOTOK..KKKKKKKOTTTTTK........",
    "..KTTTTTK........KKTTTK.........",
    "...KKTKK...........KKK..........",
    ".....K..........................",
    "................................",
    "................................",
]

MIST_FOX_ICON = [
    "................",
    "...K......K.....",
    "..KOK....KOK....",
    "..KORK..KRORK...",
    "..KORK..KRORRK..",
    "..KORRKKKRROKK..",
    "..KORROOORROKYK.",
    "..KORRRORRRRYYY.",
    "..KKWEOOWEOOKOK.",
    "..KOEWOOEWOOOOO.",
    "...KOOOOOOOOOOK.",
    "...KOOTKTTOOOOK.",
    "....KOTTTTOOOK..",
    ".....KTTTTKOK...",
    "................",
    "................",
]

# ======================================================================
# 10 涟漪豚（水）—— 圆滚滚的豚形水兽，身体占画面约 70%；小背鳍、短尾鳍，身下一圈水环托住，头身之间一道 1px 色 5 分隔线
# 腹白、脸颊粉、水环暗部用蓝；眼睛大而圆
# 战斗图用色索引：[1, 2, 5, 7, 12, 14]
# 图标用色索引：  [1, 2, 5, 7, 12, 14]
# ======================================================================
RIPPLE_DOLPHIN_BATTLE = [
    "................................",
    ".............K..................",
    "............KNK.................",
    "............KNK.................",
    "...........KNNNK................",
    "..........KNNNNNK...............",
    "..........KNNNNNNKK.............",
    "........KKBBBBBBBBBKK...........",
    ".....WWWWBBBBBBBWWWWBK..........",
    ".....WEEWBBBBBBBWEEWBBK.........",
    ".....WEWWBBBBBBBWEWWBBBK........",
    "....KWWWWBBBBBBBWWWWBBBBK.......",
    "...PPBBBBBBBBBBBBBBBBBBPPK......",
    "...KBBBBBBBBBBBBBBBBBBBBBK......",
    "..KBBKKKKKKKKKKKKKKKKKKKBBK.....",
    "..KBBBBBBBBBBBBBBBBBBBBBBBK.....",
    "..KBBBBBBBBBBNBNBBBBBBBBBBK.....",
    "..KBBBBBBBBBBBWBBBBBBBBBBBK.....",
    "..KBBBBBBBWWWWWWWWWBBBBBBBK.....",
    "...KBBBBWWWWWWWWWWWWWBBBBK......",
    "...KBBBBWWWWWWWWWWWWWBBBNKKKKK..",
    "....KBBWWWWWWWWWWWWWWWBBKNNNNN..",
    ".....KBBWWWWWWWWWWWWWBBKKNNNNK..",
    "......KBWWWWWWWWWWWWWBK.KNNNK...",
    "...KK.KNNNNNNNNNNNNNNNK.KNNK....",
    "..KNNKKKKKKKKKKKKKKKKKKKNNK.....",
    ".KNNNNNNNNNNNNNNNNNNNNNNNNNK....",
    "..KNNNNNNNNNNNNNNNNNNNNNNNK.....",
    "...KKKKNNNNNNNNNNNNNNNKKKK......",
    ".......KKKKKKKKKKKKKKK..........",
    "................................",
    "................................",
]

RIPPLE_DOLPHIN_ICON = [
    "................",
    "................",
    ".......KK.......",
    "......KKKK......",
    "....KKBBBBKK....",
    "...WEBBBWEBBK...",
    "..PEWBBBEWBBPK..",
    "..KBKKKKKKKBBK..",
    ".KBBBBBBBBBBBB..",
    "..KBBBWWWWBBBK..",
    "..KBBWWWWWWBBK..",
    "..KBWWWWWWWWBK..",
    "...KBWWWWWWBK...",
    "...KNNKKKKNNK...",
    "..KNNNNNNNNNNK..",
    "................",
]

# ======================================================================
# 11 灯火鳅（水）—— 宽头六鳃的两栖小兽，S 形侧身，尾尖挂一盏水滴形小灯（黄 + 白高光，仅 3x3），四肢短粗
# 主体浅蓝、鳃与尾暗部蓝、灯黄；嘴用蓝点，不抢灯光
# 战斗图用色索引：[1, 2, 5, 7, 10, 12]
# 图标用色索引：  [1, 2, 5, 7, 10, 12]
# ======================================================================
LAMP_LOACH_BATTLE = [
    "................................",
    "................................",
    "................................",
    "................................",
    "...K.....KKK.......K......KKK...",
    "..KNKKKKKBBBKKK.KKKNK....KWWYK..",
    ".KNNNNNBBBBBBBBKNNNNNK...KYYYK..",
    "..KNNNNNBBBBBBBNNNNNK....KYYYK..",
    "...KBBNBBBBBBBBBNKKK......KKK...",
    "...KBWWWWBBBBBBBBK.K.....KNK....",
    "..KNBWEEWBBBWWWWBKKNK...KNNK....",
    ".KNNNWEWWBBBWEEWNNNNNK..KNNK....",
    "..KNNWWWWBBBWEWWNNNNK...KNKK....",
    "...KBBNBBBBBWWWWNKKK.....KKBK...",
    "...KBBBBBBBBBBBBBK.......KBBBK..",
    "....KBBBBBNNBBBBBBK.....KBBBBBK.",
    ".....KBBBBBBBBBBBBKK..KKBBBBBBK.",
    "......KBBBBBBBBBBBBBKKBBBBBBBK..",
    "......KBBBBBBBBBBBBBBBBBBBBBBK..",
    "......KBBBBBBBBBBBBBBBBBBBBBBK..",
    "......KBBBBBBBBBBBBBNNNNNBBBK...",
    ".....KBBBBBBBBBBBBBNNNNNNNBK....",
    ".....KBBBKKBBBBBBBBBNNNNNBK.....",
    ".....KBBBK.KBBBBBBBBBBBBBK......",
    "......KKK...KKBBBBBBBBBKK.......",
    ".............KBBBKKKKKK.........",
    "..............KKK...............",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
]

LAMP_LOACH_ICON = [
    "................",
    "........K.......",
    "........YK......",
    ".......KYYK.....",
    ".......KYKK.....",
    "....KKKBBBBKKK..",
    "..KKNNBBBBBBNNK.",
    ".KNNNBBBBBBBBNN.",
    "...KBEWBBEWBBBK.",
    "..KKBBBBBBBBBBK.",
    ".KNNBBBBBBBBBBN.",
    "..KKNBBBNBBBBNK.",
    "....KBBNNNNBBK..",
    ".....KNNNNNNK...",
    "......KNNNNK....",
    "................",
]

# ======================================================================
# 12 花刃忍（草）—— 直立植物忍者：四片粉花瓣作兜帽、双手各一片绿叶刃，围巾状叶片向右飘，眼部只留一条深蓝横缝
# 花瓣粉 + 浅绿两层、花心黄、叶刃中绿；不画人脸与五瓣脸谱
# 战斗图用色索引：[1, 4, 5, 7, 10, 11, 14]
# 图标用色索引：  [1, 5, 7, 10, 11, 14]
# ======================================================================
PETAL_NINJA_BATTLE = [
    "................................",
    "..............KP................",
    "..............KP................",
    ".............KPPK...............",
    "............KPPLPK..............",
    "...........KPPPLPPK.............",
    "...KKKKKKKKKPPLLPPKKKKKKKKK.....",
    "..KPPPPPPPPPPPYYPPPPPPPPPPPK....",
    "...KPPPPPPPPPLLLLPPPPPPPPPK.....",
    "....KPPPPPPPPLLLLPPPPPPPPK......",
    ".....KPPPPPPLLLLLLPPPPPPK.......",
    "......KPPPPPLLLLLLPPPPPK........",
    ".......KPPPLWLWLWLWPPPPK........",
    "........KPPEEEEEEEEPPPPK........",
    ".........KPLLLLLLLLPKPPPK.......",
    "..........KLLLLLLLLKKKKKPKK.....",
    ".K........KLKLLLLGLGGGGGGGGGGKK.",
    ".GKK.....KLLLLLLLLLLGGGGGGGGGGG.",
    ".KGGKK..KLLLLLLLLLLLLGGGGKGGGGG.",
    ".KGGGGKKLLLLLLLLLLLLLLKKKKGGGGG.",
    ".KGGGGGGLLKLLLLLLLLGLLLGKKGGGGK.",
    ".KGGGGGGGGKLLLLLLLLGGLLLGGGGGGG.",
    ".KGGGGGGKKKLLLLLLLLKKGLGGGGGGGG.",
    ".KGGGGGK..KLLLLLLLLK.KKGGGGGGGK.",
    ".KGGGKK...KLLLLLLLLK...KKGGGGK..",
    ".KGGK......KLLLLLLK......KGGGK..",
    ".KGK......KLLLLLLLLK.....KGGGGK.",
    "..K.......KLLLLLLLLK.....KGKGK..",
    "..........KLLLKKLLLK......K.K...",
    ".........KLLLK..KLLLK...........",
    ".........KLLLK..KLLLK...........",
    "................................",
]

PETAL_NINJA_ICON = [
    "................",
    "........PK......",
    "........PK......",
    ".......KLPK.....",
    "......KPLPPK....",
    ".K....KPLPPK....",
    ".PKKKKPPYLPPKKK.",
    ".KPPPPPPLLPPPPP.",
    "...KPPPLLLLPPPK.",
    "....KPLLLLLLPK..",
    ".....KLLLLLLK...",
    "....KLLWLWLLLK..",
    ".....KEEEEEEK...",
    ".....KLLLLLLK...",
    "......KLLLLK....",
    "................",
]

# ======================================================================
# 13 荆星芽（草）—— 矮胖五角星花苞怪：星角由肉质叶片叠成，中心一颗红星核，两侧粗藤手臂 + 两条短根须
# 叶缘浅绿（先画大一号的浅绿星再盖中绿星）、星核外一圈深绿、藤与根须用棕
# 战斗图用色索引：[1, 3, 4, 5, 7, 8, 11, 13]
# 图标用色索引：  [4, 5, 8, 11, 13]
# ======================================================================
BRIER_STAR_BATTLE = [
    "................................",
    "................K...............",
    "................GK..............",
    "................GK..............",
    "...............KGGK.............",
    "..............KLGGLK............",
    "..............KGGGGK............",
    ".............KLGGGGLK...........",
    ".............KGGGGGGK...........",
    "........KKKKKLGGGGGGLKKKKK......",
    ".....KKKLLLGGGGGGGGGGGGLLLKKK...",
    "....KGGGGGGGGGDDGDDDGGGGGGGGGK..",
    ".....KGGGGGGGDGGRRGGDGGGGGGGK...",
    "......KGGGGGGDGWRRRGDGGGGGGK....",
    "......KLGGGGDGRRRRRRGDGGGGLK....",
    ".......KLGGGDGRRRRRRGDGGGLK.....",
    ".........KLGGDGRRRRGDGGLK.......",
    ".........KLGGDWEREWGDGGLK.......",
    "......KKKKLGGGDDGDDDGGGLKKKK....",
    "....KKMMMMLGGGGGGGGGGGGLMMMMKK..",
    "...KMMMMMMGGGGGGGGGGGGGGMMMMMMK.",
    "..KMMMMMMMGGGGGGLGGGGGGGMMMMMMM.",
    ".KMMMMMMMMGGGGGLKKLGGGGGMMMMMMM.",
    ".MMMMMKKKKGGGLKK..KKLGGGKKKKMMM.",
    ".MMMMK...KGLKKK...KKKKLGK...KMM.",
    ".MMMK...KLKKMMMK.KMMMKKKLK...KM.",
    ".KKK.....K.KMMMK.KMMMK..K.....K.",
    "...........KMMMK.KMMMK..........",
    "...........KMMMK.KMMMK..........",
    "...........KMMMK.KMMMK..........",
    "................................",
    "................................",
]

BRIER_STAR_ICON = [
    "................",
    "........GK......",
    "........GK......",
    ".......KGGK.....",
    "......KKGGKK....",
    "...KKKLGGGGLKKK.",
    "..KGGGGGGGGGGGG.",
    "...KGGGGRRGGGGK.",
    ".KMKKKGGRRGGKKK.",
    ".MMMMMGGGGGGMMM.",
    ".KMMMMGGGGGGMMM.",
    "..KKKLGMKMMGLKK.",
    "....KGGMKMMGGK..",
    ".....KKMKMMKK...",
    "......KMKMMK....",
    "................",
]

# ======================================================================
# 14 雏羽啾（风）—— 刚破壳的小鸡形鸟：下半身半个蛋壳（壳边不平整），短圆翅膀、头顶两撮绒羽，眼神困倦（上眼皮压下来）
# 主体黄、绒羽与翅膀浅灰、蛋壳白、喙橙；不用蓝色，避开旧飞鸟系
# 战斗图用色索引：[1, 5, 7, 9, 10, 15]
# 图标用色索引：  [1, 5, 7, 9, 10, 15]
# ======================================================================
CHICK_SPARROW_BATTLE = [
    "................................",
    "...........K........K...........",
    "..........KTK.......TK..........",
    "..........KTTK.....KTK..........",
    "..........KTTK.....KTK..........",
    "..........KTTTK...KTTK..........",
    "...........KTTK.K.KTK...........",
    "...........KTTKKYKKTK...........",
    "...........KTTTYYYTTK...........",
    "...........KYTYYYYYTK...........",
    "..........TYYYYYYYYYTK..........",
    ".........WWWWYYYYYYWWWK.........",
    ".........KEEYYYYYYYYEYK.........",
    "........KTYYYYYYYYYYYYTK........",
    ".......KTTTYYYYYYYYYYTTTK.......",
    "......KTTTTTYYYYYYYYTTTTTK......",
    "......KTTTTTYYYOOOOOTTTTTK......",
    ".....KWTTTTYYYYOOOYYYTTTTTK.....",
    "......KKKTWWYYYOOYYYWWTKKK......",
    "........KWWWWYYOYYYYWWWK........",
    ".......KWWWWWWWWYWWWWWWWK.......",
    "......KWWWWWWWWWWWWWWWWWWK......",
    "......KWWWWWWWWWWWWWWWWWWK......",
    "......KWWWWWWWWWWWWWWWWWWK......",
    "......KWWWWWWWWWWWWWWWWWWK......",
    "......KWWWWWWWWWWWWWWWWWWK......",
    "......KWWWWWWTTTTTTTWWWWWK......",
    "......KWWWWTTTTTTTTTTWWWWK......",
    ".......KWWTTTTTTTTTTTTWWK.......",
    "........KWWTTTTTTTTTTWWK........",
    ".........KWWWTTTTTTTWWK.........",
    "................................",
]

CHICK_SPARROW_ICON = [
    "................",
    "....KTK..KTK....",
    "....KTTKKTTK....",
    "....KTTKKTTK....",
    "....KTTKKTTK....",
    "....KTTTTTTK....",
    "....KYTYYTYK....",
    "....KTYYYTYK....",
    ".KTWEWYYEWYYTK..",
    "..KKYYYOYYYYK...",
    "..KWWYYOOOYWWK..",
    "..KWWYYOYYYWWK..",
    ".KWWWWYOYYWWWW..",
    "..KWWWWWWWWWWK..",
    "..KWWWWWWWWWWK..",
    "................",
]

# ======================================================================
# 15 夜幕翼（暗）—— 单只月牙翅的暗色蝙蝠：翼展占上半部、身体小、双耳长，眼睛只剩一条粉亮缝；翼膜下缘做翼指锯齿
# 翼膜粉、身体深蓝——**大面积主体绝不能用 5**（会和描边同色、轮廓消失）
# 战斗图用色索引：[1, 5, 7, 14]
# 图标用色索引：  [1, 5, 14]
# ======================================================================
NIGHT_WING_BATTLE = [
    "................................",
    "................................",
    "................................",
    "...........K..........K.........",
    "..........KEK........KEK........",
    "........K..KK........KK..K......",
    ".....KKKPKKKEK......KEKKKPKKK...",
    "....KPPPPPPPEEK....KEEPPPPPPPK..",
    "...KPPPPPPPPPEEK..KEEPPPPPPPPPK.",
    "..KPPPPPPPPPPEEP.KPEEPPPPPPPPPP.",
    "..KPPPPPPPPPPEEEKKEEEPPPPPPPPPP.",
    "..KPPPPPPPPPPPEEEEEEPPPPPPPPPPP.",
    "..KPPPPPPPPPPPEEEEEEPPPPPPPPPPP.",
    ".KPPPPPPPPPPPPEEEEEEPPPPPPPPPPP.",
    ".KPPPPPPPPPPPEWEEEEWEPPPPPPPPPP.",
    ".KPPPPPPPPPPPPPPEEPPPPPPPPPPPPP.",
    "..KPPPPPPPPPPEEEEEEEEPPPPPPPPPP.",
    "..KPPPPPPPPPPPEEEEEEPPPPPPPPPPP.",
    "....KPPPPPPPPPEEEWEEPPPPPPPPPK..",
    ".....KPPPPPPPEEEEEEEEPPPPPPPK...",
    ".....KPKKKKKPEEEEEEEEPKKKKKPK...",
    ".....KPK....KEEEEEEEEK....KPK...",
    "......K.....KEEEEEEEEK.....K....",
    "............KEEEEEEEEK..........",
    ".............KEEEEEEK...........",
    ".............KEEEEEEK...........",
    "..............KEEEEK............",
    "...............KEKK.............",
    "................................",
    "................................",
    "................................",
    "................................",
]

NIGHT_WING_ICON = [
    "................",
    ".....KEK..KEK...",
    "......KK..KK....",
    "......KE.KEK....",
    "...KKKKEKKEKKKK.",
    "..KPPPPEEEEPPPP.",
    ".KPPPPPEEEEPPPP.",
    ".KPPPPPPEPPPPPP.",
    ".KPPPPPEEEEPPPP.",
    ".KPPPPPEEEEPPPP.",
    "..KPPPPEEEEPPPP.",
    "..KPPKKEEEEKKPP.",
    "..KPK.KEEEEK.KP.",
    "..KPK..KEEK..KP.",
    "................",
    "................",
]

# ======================================================================
# 16 绒医团（光）—— 粉色绒球医护兽：头戴白色小医护帽（帽檐浅灰），胸前一块浅绿心形贴布（不用红十字），四肢短小
# 绒毛用粉 + 沿外缘一圈浅灰茸点表现；帽与眼睛白、心形浅绿
# 战斗图用色索引：[1, 5, 7, 11, 14, 15]
# 图标用色索引：  [1, 5, 7, 11, 14, 15]
# ======================================================================
MEDIC_FLUFF_BATTLE = [
    "................................",
    ".............KKKKK..............",
    "...........KKWWWWWKK............",
    "..........KWWWWWWWWWK...........",
    ".........KWWWWWWWWWWWK..........",
    "........KWWWWWWWWWWWWWK.........",
    "........KWWWWWWWWWWWWWK.........",
    "........KWWWWWWWWWWWWWK.........",
    ".......KTTTTTTTTTTTTTTTK........",
    ".......KTTTTTTTTTTTTTTTK........",
    "........KKKKPPPPPPPKKKK.........",
    ".........KPPPTPPPTPPPK..........",
    ".......KKTPPPPPPPPPPPTKK........",
    "......KPWWWWPPPPPWWWWPPPK.......",
    "......KPWEEWPPPPPWEEWPPPK.......",
    ".....KTPWEWWPPPPPWEWWPPPTK......",
    ".....KPPWWWWPPPPPWWWWPPPPK......",
    "....KPPPPPPPPPPPPPPPPPPPPPK.....",
    "....KPPPPPPPPPKKPPPPPPPPPPK.....",
    "....KTPPPPPPPPPPPPPPPPPPPTK.....",
    "....KPPPPPPPPPLPLPPPPPPPPPK.....",
    "....KPPPPPPPPLLLLLPPPPPPPPK.....",
    "...KWWWPPPPPPPLLLPPPPPPPWWWK....",
    "..KWWWWPPPPPPPPLPPPPPPPPWWWWK...",
    "..KWWWWPPPPPPPPPPPPPPPPPWWWWK...",
    "..KWWWWPPPPPPPPPPPPPPPPPWWWWK...",
    ".KWWWWKKKTPPPPPPPPPPPTKKKWWWWK..",
    ".KWWWK.KWWWWWTPPPTWWWWWK.KWWWK..",
    ".KWWWK.KWWWWWPPPPPWWWWWK.KWWWK..",
    "..KKK..KWWWWWKKKKKWWWWWK..KKK...",
    "........KKKKK.....KKKKK.........",
    "................................",
]

MEDIC_FLUFF_ICON = [
    "................",
    "......KKKK......",
    ".....KWWWWK.....",
    "....KWWWWWWK....",
    "...KWWWWWWWWK...",
    "....KWTPPTWK....",
    "...KPPPPPPPPK...",
    "..KPTPPPPPPTPK..",
    "..KPEWPPEWPPPK..",
    ".KPTPPPPPPPPTP..",
    "..KPPPPLLPPPPK..",
    "..KPPPLLLLPPPK..",
    "..KPTPPPPPPTPK..",
    "...KPPPPPPPPK...",
    "....KKTPPTKK....",
    "................",
]

# ======================================================================
# 17 导线蛇（雷）—— 盘成 8 字形的深色电蛇：头抬起、吐黄信，尾端是双插脚插头，身上缠两段黄色电弧（只在轮廓外）
# 主体深蓝 + 头顶浅灰亮部、插头浅灰、插脚与电弧黄；电弧不盖住身体
# 战斗图用色索引：[1, 5, 7, 10, 15]
# 图标用色索引：  [1, 5, 7, 10, 15]
# ======================================================================
WIRE_SNAKE_BATTLE = [
    "................................",
    "..............................K.",
    ".............................KY.",
    ".K........KKK...............KYK.",
    ".YK.....KKTTTKK............KYK..",
    ".KYK...KETTTTTEK............KYK.",
    "..KYK.KEWWWWWWWWK............KY.",
    ".KYK..KEWEEWWEEWK.............K.",
    ".YK...KEWEWWWEWWK.KKKKKKK.......",
    ".K....KEWWWWWWWWKKEEEEEEEK......",
    "......KEEEEEEEEEKEEEEEEEEEK.....",
    ".......KEEEEEEEKEEEEEEEEEEEK....",
    ".......KEEYEEEEEEEEEEEEEEEEEK...",
    "........KEYEEEEEEEETTTTTEEEEEK..",
    ".......KKEEEEEEEEEEKKKKKEEEEEK..",
    "......KEEEEEEEEEEEEEK...KEEEEK..",
    "......KEEEEEEEEEEEEEK...KEEEEK..",
    ".....KEEEEEEEEEEEEEEEK..KEEEEK..",
    "....KEEEEEEEEEEEEEEEEEKKEEEEEK..",
    "....KEEEEEKKKKEEEEEEEEKEEEEEEK..",
    "....KEEEEEK...KEEEEEEEEEEEEEKK..",
    "....KEEEEEK....KEEEEEEEETTTTTTK.",
    "....KEEEEEK.....KEEEEEEETTTTTTK.",
    "....KEEEEEK.....KEEEEEEETTTTTTK.",
    "....KEEEEEEKKKKKEEEEEEKKTTTTTTK.",
    ".....KEEEEEEEEEEEEEEEK.KTTTTTTK.",
    "......KEEEEEEEEEEEEEK...KYKKYK..",
    "......KEEEEEEEEEEEEEK...KYKKYK..",
    ".......KKEEEEEEEEEKK....KYKKYK..",
    ".........KEEEEEEEK.......K..K...",
    "................................",
    "................................",
]

WIRE_SNAKE_ICON = [
    "................",
    "......KK........",
    ".....KTTK.....K.",
    "....WEEWEK...KY.",
    "...KEWEEEEK...K.",
    "....KEEEEK......",
    "...KEEEEEEK.....",
    "..KEEEEEEEEK....",
    ".KEEEEKEEEEEK...",
    ".KEEEEKKKEEEKK..",
    ".KEEEEK.EETTTTK.",
    ".KEEEEEKEETTTTK.",
    "..KEEEEEEETTTTK.",
    "...KEEEEEEKYKYK.",
    "................",
    "................",
]

# ======================================================================
# 18 雷云团（雷）—— 团状雷云：四个圆叠成云体，云顶伸两根黄色短雷角，云身一道白色高光，云底压一行深蓝暗部，底下 3 滴雨
# 云浅灰、雷角黄、雨点浅蓝；不画王冠、不画人脸，靠「云 + 雷角 + 雨点」识别
# 战斗图用色索引：[1, 5, 7, 10, 12, 15]
# 图标用色索引：  [1, 5, 7, 10, 12, 15]
# ======================================================================
STORM_CLOUD_BATTLE = [
    "................................",
    "...........KK.....KK............",
    "..........KYYK...KYYK...........",
    ".........KYKK.....KKYK..........",
    "..........KYK.....KYK...........",
    ".........KYK..KKK..KYK..........",
    "........KYKKKKTTTKKKKYK.........",
    "........KKYTTTTTTTTTYKK.........",
    ".......KYKTWWWTTTTTTTKYK........",
    ".....KKKTWWTTTTTTTTTTTTKKK......",
    "....KTTTWTTTTTTTTTTTTTTTTTK.....",
    "...KTTTTTTTTTTTTTTTTTTTTTTTK....",
    "..KTTTTTTTTTTTTTTTTTTTTTTTTTK...",
    "..KTTTTWWWWTTTTTTTTWWWWTTTTTK...",
    ".KTTTTTWEEWTTTTTTTTWEEWTTTTTTK..",
    ".KTTTTTWEWWTTTTTTTTWEWWTTTTTTK..",
    ".KTTTTTWWWWTTTTTTTTWWWWTTTTTTK..",
    "..KTTTTTTTTTTTTTTTTTTTTTTTTTK...",
    "..KTTTTTTTTTTTTTTTTTTTTTTTTTK...",
    "...KTTTTTTTTTTTTTTTTTTTTTTTK....",
    "....KTTTTTTTTTTTTTTTTTTTTTK.....",
    ".....KKKTTTTTTTTTTTTTTTKKK......",
    "........KKTTTTTTTTTTTKK.........",
    "..........KKKKKKKKKKK...........",
    "................................",
    "................................",
    "......B.................B.......",
    ".....BBB.......B.......BBB......",
    "......B.......BBB.......B.......",
    "...............B................",
    "................................",
    "................................",
]

STORM_CLOUD_ICON = [
    "................",
    ".....KK...KK....",
    "....KYYK.KYYK...",
    ".....KK...KK....",
    "....KYKKKKKYK...",
    "...KYKTTTTTKYK..",
    "...KKYTWWTTYKK..",
    "..KTTTWTTTTTTTK.",
    ".KTWETTTTWETTTT.",
    ".KTEWTTTTEWTTTT.",
    ".KTTTTTTTTTTTTT.",
    "..KTTTTTTTTTTTK.",
    "...KKTTTTTTTKK..",
    ".....KKKKKKKB...",
    "...........BBB..",
    "................",
]


#: 精灵 id -> (名称, 属性, 战斗图字符画, 图标字符画)
_CREATURES = [
    (1, "小火狮", "火", FIRE_LION_BATTLE, FIRE_LION_ICON),
    (2, "水滴滴", "水", WATER_DROP_BATTLE, WATER_DROP_ICON),
    (3, "兔小子", "草", GRASS_RABBIT_BATTLE, GRASS_RABBIT_ICON),
    (4, "小狮鹫", "风", WIND_GRIFFIN_BATTLE, WIND_GRIFFIN_ICON),
    (5, "独角兽", "光", LIGHT_UNICORN_BATTLE, LIGHT_UNICORN_ICON),
    (6, "三头犬", "暗", DARK_CERBERUS_BATTLE, DARK_CERBERUS_ICON),
    (7, "不死鸟", "火", PHOENIX_BATTLE, PHOENIX_ICON),
    (8, "闪电小子", "雷", THUNDER_KID_BATTLE, THUNDER_KID_ICON),
    (9, "雾尾狐", "火", MIST_FOX_BATTLE, MIST_FOX_ICON),
    (10, "涟漪豚", "水", RIPPLE_DOLPHIN_BATTLE, RIPPLE_DOLPHIN_ICON),
    (11, "灯火鳅", "水", LAMP_LOACH_BATTLE, LAMP_LOACH_ICON),
    (12, "花刃忍", "草", PETAL_NINJA_BATTLE, PETAL_NINJA_ICON),
    (13, "荆星芽", "草", BRIER_STAR_BATTLE, BRIER_STAR_ICON),
    (14, "雏羽啾", "风", CHICK_SPARROW_BATTLE, CHICK_SPARROW_ICON),
    (15, "夜幕翼", "暗", NIGHT_WING_BATTLE, NIGHT_WING_ICON),
    (16, "绒医团", "光", MEDIC_FLUFF_BATTLE, MEDIC_FLUFF_ICON),
    (17, "导线蛇", "雷", WIRE_SNAKE_BATTLE, WIRE_SNAKE_ICON),
    (18, "雷云团", "雷", STORM_CLOUD_BATTLE, STORM_CLOUD_ICON),
]

#: 精灵 id -> 战斗图 SpriteMatrix
CREATURE_BATTLE: dict[int, SpriteMatrix] = {}
#: 精灵 id -> 图标 SpriteMatrix
CREATURE_ICON: dict[int, SpriteMatrix] = {}
#: 精灵 id -> (名称, 属性)
CREATURE_INFO: dict[int, tuple[str, str]] = {}

SPRITES: list[SpriteMatrix] = []

for _sid, _name, _type, _battle_rows, _icon_rows in _CREATURES:
    _battle_sprite = SpriteMatrix(f"creature_{_sid}_battle", _battle_rows, PALETTE)
    _icon_sprite = SpriteMatrix(f"creature_{_sid}_icon", _icon_rows, PALETTE)
    CREATURE_BATTLE[_sid] = _battle_sprite
    CREATURE_ICON[_sid] = _icon_sprite
    CREATURE_INFO[_sid] = (_name, _type)
    SPRITES.append(_battle_sprite)
    SPRITES.append(_icon_sprite)
