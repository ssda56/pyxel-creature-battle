"""8 只精灵的**成品字符画**（方案 D：程序化字符画，批 4 重绘）。

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
# 2 水滴滴（水）—— 水滴形身体，白色高光在左上，两侧浅蓝小鳍，底部三朵小水花
# 战斗图用色索引：[1, 2, 5, 7, 12, 14]
# 图标用色索引：  [1, 2, 5, 7, 12]
# ======================================================================
WATER_DROP_BATTLE = [
    "................................",
    "................K...............",
    "................BK..............",
    "................BK..............",
    "...............KBBK.............",
    "...........WW.KBBBBK............",
    "...........WWWKBBBBK............",
    "..........WWWWBBBBBBK...........",
    "...........WWWBBBBBBBK..........",
    "..........WWWWWBBBBBBK..........",
    "...........WWWBBBBBBBBK.........",
    "..........KWWWBBBBBBBBBK........",
    ".........KBWWWBBBBBBBBBBK.......",
    "..K.....KBBBWBBBBBBBBBBBBK......",
    ".KBK...KBBBBBBBBBBBBBBBBBBK...K.",
    "..KBK.KBBBBBBBBBBBBBBBBBBBBK.KB.",
    "..KBWBBBBBWWWWWBBBWWWWWBBBBBBWB.",
    "..KBBWBBBBWWWEWBBBWWWEWBBBBBWBB.",
    "..KBBWBBBBWEEEWBBBWEEEWBBBBBWBB.",
    "...KBWWBBBWEEEWBBBWEEEWBBBBWWBK.",
    "...KBBWBBBWEEEWBBBWEEEWBBBNWBBK.",
    "...KBBWBBBWWWWWPBBPWWWWBBBNNBBK.",
    "...KBBWBBBBBBBBBNNBBBBBBBNNNBBK.",
    "...KBKKKBBBBBBBBBBBBBBBBBNNNNBK.",
    "....K...KWBBBBBBBBBBBBBBNNNNKK..",
    "........KKWBBBBBBBBBBBBNNNNNK...",
    ".....KKKBKKBBBBBBBBBBNNNNBNKK...",
    "....KBBBBBBBKBBBBBBNNNBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBBBBBBBBBK.",
    "....KBBBBBBBBBBBBBBBBBBBBBBBBK..",
    ".....KKKBKKBBBBBBBBBBBBKKBKKK...",
    "................................",
]

WATER_DROP_ICON = [
    "................",
    ".......KBK......",
    ".....K.KBK......",
    "....KWKBBBK.....",
    "....KWKBBBKK....",
    "...KWWWBBBBBK...",
    "...KBWBBBBBBBK..",
    "..KBBWBBBBBBBBK.",
    "..KWWEWBWWEWBBK.",
    ".KBWEEWBWEEWBBB.",
    "..KWEEWBWEEWBNK.",
    "..KWWWWBWWWWBNN.",
    "..KBBBBNNBBBBNK.",
    "...KBBBBBBBBNNK.",
    "....KBBBBBBNKK..",
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
