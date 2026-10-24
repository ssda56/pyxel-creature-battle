"""纯逻辑约束测试（数据层 / 数值层不得依赖 Pyxel）。

本批任务的硬性约束：

1. src/data、src/battle、src/model 下的模块**不许 import pyxel 或任何 UI 模块**；
2. 它们必须是纯 Python 逻辑，能脱离 Pyxel 直接 import 与测试。

本文件用两种方式验证：

- **静态扫描**：逐个文件检查源码里不出现 pyxel / UI 包的 import；
- **干净子进程**：在一个全新解释器里 import 全部新模块，断言
  sys.modules 里没有 pyxel，也没有 src.ui / src.scenes / src.core / src.assets_gen。
"""

from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 受约束的包目录
PURE_PACKAGES = ("src/data", "src/battle", "src/model")

#: 不允许被数据层 / 数值层引用的 UI 相关包
FORBIDDEN_IMPORTS = ("pyxel", "src.ui", "src.scenes", "src.core", "src.assets_gen")

#: 标准库 / 无副作用模块白名单（数据层只允许依赖这些）
_STDLIB_OK = frozenset({
    "__future__", "math", "random", "dataclasses", "typing", "collections",
})

#: 本批新增的模块（子进程里逐个 import）
NEW_MODULES = (
    "src.data.species_data",
    "src.data.skill_data",
    "src.data.item_data",
    "src.battle.type_chart",
    "src.battle.damage_calc",
    "src.battle.catch_calc",
    "src.model.creature",
    "src.model.player",
)


def _python_files() -> list[Path]:
    """受约束目录下的全部 .py 文件。"""
    files: list[Path] = []
    for package in PURE_PACKAGES:
        files.extend(sorted((ROOT / package).rglob("*.py")))
    return files


def _imported_modules(path: Path) -> set[str]:
    """用 AST 解析出文件里真正 import 的模块名（不把 docstring 文字算进来）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if base:
                names.add(base)
            for alias in node.names:
                names.add(f"{base}.{alias.name}" if base else alias.name)
    return names


def _run_python(code: str) -> subprocess.CompletedProcess:
    """在项目根目录下的干净子进程里跑一段 Python 代码。"""
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


class StaticImportScanTest(unittest.TestCase):
    """静态扫描源码。"""

    def test_package_files_exist(self):
        self.assertTrue(_python_files(), "没找到数据层 / 数值层文件")

    def test_no_pyxel_import(self):
        """AST 级别确认：真的没有 import pyxel（docstring 里的文字不算）。"""
        for path in _python_files():
            for name in _imported_modules(path):
                self.assertFalse(
                    name == "pyxel" or name.startswith("pyxel."),
                    f"{path} 不许 import {name}",
                )

    def test_no_ui_package_import(self):
        for path in _python_files():
            for name in _imported_modules(path):
                for forbidden in FORBIDDEN_IMPORTS[1:]:
                    self.assertFalse(
                        name == forbidden or name.startswith(forbidden + "."),
                        f"{path} 不许 import {name}",
                    )

    def test_data_layer_only_imports_pure_modules(self):
        """数据层 / 数值层只能依赖标准库与自己的纯逻辑模块。"""
        for path in _python_files():
            for name in _imported_modules(path):
                top = name.split(".")[0]
                allowed = (
                    name.startswith(("src.data", "src.battle", "src.model"))
                    or top in _STDLIB_OK
                )
                self.assertTrue(allowed, f"{path} 引入了不允许的依赖 {name}")

    def test_every_new_module_is_covered(self):
        names = {p.relative_to(ROOT).as_posix()[:-3].replace("/", ".")
                 for p in _python_files()}
        for module in NEW_MODULES:
            self.assertIn(module, names, f"{module} 不在受约束目录里")


class CleanSubprocessTest(unittest.TestCase):
    """干净子进程验证 import 链。"""

    def test_import_chain_has_no_pyxel(self):
        lines = ["import sys"]
        lines += ["import " + module for module in NEW_MODULES]
        lines.append("assert 'pyxel' not in sys.modules, 'pyxel 被导入进来了'")
        lines.append(
            "leaked = [m for m in sys.modules "
            "if m.startswith(('src.ui', 'src.scenes', 'src.core', 'src.assets_gen'))]"
        )
        lines.append("assert not leaked, leaked")
        lines.append("print('CLEAN')")
        result = _run_python("\n".join(lines))
        self.assertEqual(result.returncode, 0,
                         f"子进程失败：{result.stdout}\n{result.stderr}")
        self.assertIn("CLEAN", result.stdout)

    def test_modules_work_without_pyxel(self):
        """脱离 Pyxel 也能正常算：导入即用。"""
        lines = [
            "from src.model.creature import Creature",
            "from src.model.player import Player",
            "from src.battle.damage_calc import damage",
            "from src.battle.catch_calc import catch_chance",
            "c = Creature(1)",
            "assert c.hp_max == 34 and c.attack == 19",
            "assert damage(19, 12, '火', 40, '草') >= 1",
            "assert abs(catch_chance(1, 34, 0.40) - 0.39176470588235296) < 1e-12",
            "assert Player.new_game(1).dollars == 300",
            "print('OK')",
        ]
        result = _run_python("\n".join(lines))
        self.assertEqual(result.returncode, 0,
                         f"子进程失败：{result.stdout}\n{result.stderr}")
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
