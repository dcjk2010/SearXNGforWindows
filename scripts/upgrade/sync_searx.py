#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SearXNGforWindows 升级同步脚本

用法:
    python scripts/upgrade/sync_searx.py <上游searx源码目录>

示例（先下载上游 tarball 并解压）:
    curl -sL https://github.com/searxng/searxng/archive/master.tar.gz -o /tmp/master.tgz
    mkdir -p /tmp/sx-master && tar xzf /tmp/master.tgz -C /tmp/sx-master --strip-components=1
    python scripts/upgrade/sync_searx.py /tmp/sx-master/searx

作用:
  1. 镜像同步：把上游 searx/ 全部文件拷入 python/Lib/site-packages/searx/（覆盖），
     删除本地有而上游没有的文件（保留 version_frozen.py；清理 __pycache__）
  2. 重放全部 Windows 适配补丁（settings_loader / limiter / favicons / network-client /
     valkeydb / version / webutils / engines-init / trusted_proxies）
  3. 对补丁后的文件做 ast 语法校验

注意:
  - 必须在仓库根目录运行（dst_root 为相对路径）
  - 运行前请确认实例已停止
  - 脚本自动处理 CRLF/LF：读入时归一化为 LF，写出时恢复原行尾
"""
import ast
import io
import os
import re
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST_ROOT = os.path.join(REPO_ROOT, "python", "Lib", "site-packages", "searx")
KEEP = {"version_frozen.py"}  # 本地特有文件，同步时保留


def ensure_import(text: str, mod: str) -> str:
    """在 docstring 之后的 import 块末尾插入 `import <mod>`（docstring 安全版）"""
    lines = text.split("\n")
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    # 跳过模块 docstring
    if i < len(lines) and (lines[i].lstrip().startswith('"""') or lines[i].lstrip().startswith("'''")):
        q = lines[i].lstrip()[:3]
        if lines[i].count(q) >= 2:
            i += 1
        else:
            i += 1
            while i < len(lines) and q not in lines[i]:
                i += 1
            i += 1
    last = None
    for j in range(i, min(i + 80, len(lines))):
        if re.match(r"^(from|import) [A-Za-z_]", lines[j]):
            last = j
    assert last is not None, "找不到 import 块，无法插入 import %s" % mod
    lines.insert(last + 1, "import " + mod)
    return "\n".join(lines)


def apply_patch(relpath: str, pairs, imports=()) -> None:
    """对 dst_root/relpath 做字符串替换 + 追加 import（自动处理 CRLF）"""
    p = os.path.join(DST_ROOT, relpath)
    with io.open(p, encoding="utf-8", newline="") as fh:
        raw = fh.read()
    eol = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    for old, new in pairs:
        assert old in text, "PATCH MISS %s: %r" % (relpath, old[:70])
        text = text.replace(old, new, 1)
    for mod in imports:
        text = ensure_import(text, mod)
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("\n", eol))
    ast.parse(open(p, encoding="utf-8").read())  # 语法校验
    print("PATCHED", relpath)


def sync(src_root: str) -> None:
    # 1. 删除本地独有文件/目录（保留 KEEP；跳过 __pycache__）
    for dirpath, dirnames, filenames in os.walk(DST_ROOT, topdown=False):
        if "__pycache__" in dirpath.split(os.sep):
            continue
        rel = os.path.relpath(dirpath, DST_ROOT)
        src_dir = src_root if rel == "." else os.path.join(src_root, rel)
        for f in filenames:
            if f in KEEP or os.path.exists(os.path.join(src_dir, f)):
                continue
            os.remove(os.path.join(dirpath, f))
            print("DEL", os.path.join(rel, f))
        for d in dirnames:
            if d == "__pycache__" or os.path.exists(os.path.join(src_dir, d)):
                continue
            shutil.rmtree(os.path.join(dirpath, d))
            print("DELDIR", os.path.join(rel, d))
    # 2. 清理全部 __pycache__
    for dirpath, dirnames, _ in os.walk(DST_ROOT):
        if "__pycache__" in dirnames:
            shutil.rmtree(os.path.join(dirpath, "__pycache__"))
    # 3. 拷入上游全部文件
    count = 0
    for dirpath, dirnames, filenames in os.walk(src_root):
        rel = os.path.relpath(dirpath, src_root)
        dst_dir = DST_ROOT if rel == "." else os.path.join(DST_ROOT, rel)
        os.makedirs(dst_dir, exist_ok=True)
        for f in filenames:
            shutil.copy2(os.path.join(dirpath, f), os.path.join(dst_dir, f))
            count += 1
    print("COPIED", count)


def replay_patches() -> None:
    # --- 配置路径指向 config/ ---
    apply_patch("settings_loader.py", [(
        "DEFAULT_SETTINGS_FILE = Path(searx_dir) / SETTINGS_YAML",
        '# DEFAULT_SETTINGS_FILE = Path(searx_dir) / SETTINGS_YAML\n'
        'DEFAULT_SETTINGS_FILE = Path(os.getcwd()) / "config" / SETTINGS_YAML',
    )])
    apply_patch("limiter.py", [(
        'cfg_file = (settings_loader.get_user_cfg_folder() or Path("/etc/searxng")) / "limiter.toml"',
        'cfg_file = (settings_loader.get_user_cfg_folder() or Path(os.getcwd()) / "config") / "limiter.toml"',
    )], imports=("os",))
    apply_patch("favicons/__init__.py", [(
        'cfg_file = (settings_loader.get_user_cfg_folder() or pathlib.Path("/etc/searxng")) / "favicons.toml"',
        'cfg_file = (settings_loader.get_user_cfg_folder() or pathlib.Path(os.getcwd()) / "config") / "favicons.toml"',
    )], imports=("os",))
    # --- Windows asyncio 兼容 ---
    apply_patch("network/client.py", [
        ("import typing as t\nfrom types import TracebackType\n\nimport asyncio",
         "import typing as t\nfrom types import TracebackType\nimport sys\n\nimport asyncio"),
        ("def init():\n    # log",
         "def init():\n    # Windows asyncio compatibility\n"
         "    if sys.platform == 'win32':\n"
         "        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n\n"
         "    # log"),
    ])
    # --- valkeydb：去掉 Unix-only 的 pwd ---
    apply_patch("valkeydb.py", [
        ("import pwd\n", ""),
        ("        _pw = pwd.getpwuid(os.getuid())\n"
         '        logger.exception("[%s (%s)] can\'t connect valkey DB ...", _pw.pw_name, _pw.pw_uid)',
         "        _pw_name = os.getenv('USERNAME', 'unknown')\n"
         "        _pw_uid = os.getpid()\n"
         '        logger.exception("[%s (%s)] can\'t connect valkey DB ...", _pw_name, _pw_uid)'),
    ])
    # --- version.py：LC_ALL/LANGUAGE 仅非 win32 ---
    apply_patch("version.py", [
        ('    "LC_ALL": "C",\n    "LANGUAGE": "",\n}\n',
         "}\n\n"
         "if sys.platform != 'win32':\n"
         '    SUBPROCESS_RUN_ENV["LC_ALL"] = "C"\n'
         '    SUBPROCESS_RUN_ENV["LANGUAGE"] = ""\n'),
    ], imports=("sys",))
    # --- webutils.py：路径分隔符归一化 ---
    apply_patch("webutils.py", [
        ("                file_list.append(str(f.relative_to(static_path)))",
         "                # Normalize to forward slashes (Linux code uses / in concatenation)\n"
         "                file_list.append(str(f.relative_to(static_path)).replace(os.sep, '/'))"),
        ("                result_templates.add(f)",
         "                # Normalize to forward slashes (Linux code uses / in concatenation)\n"
         "                result_templates.add(f.replace(os.sep, '/'))"),
    ])
    # --- engines/__init__.py：disabled 引擎也注册 logger + 补默认分类 ---
    apply_patch("engines/__init__.py", [(
        "    trait_map.set_traits(engine)\n\n    if not is_engine_active(engine):",
        "    trait_map.set_traits(engine)\n\n"
        "    if getattr(engine, 'disabled', False):\n"
        "        # Disabled engines: register for preferences visibility, skip setup\n"
        "        set_loggers(engine, engine_name)\n"
        "        if not any(cat in settings['categories_as_tabs'] for cat in engine.categories):\n"
        "            engine.categories.append(DEFAULT_CATEGORY)\n"
        "        return engine\n\n"
        "    if not is_engine_active(engine):",
    )])
    # --- trusted_proxies：空列表保护 ---
    apply_patch("botdetection/trusted_proxies.py", [(
        "        if not x_forwarded_for and not x_real_ip:",
        "        if trusted_proxies and not x_forwarded_for and not x_real_ip:",
    )])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    src = os.path.abspath(sys.argv[1])
    assert os.path.isfile(os.path.join(src, "webapp.py")), \
        "%s 不是有效的 searx 源码目录（缺少 webapp.py）" % src
    print("SRC :", src)
    print("DST :", DST_ROOT)
    sync(src)
    replay_patches()
    print("DONE. 请继续: 检查启动日志中 'Cannot load engine'（死引擎需从 config/settings.yml 删除条目），"
          "更新 version_frozen.py / README，冒烟测试后提交推送。详见 UPGRADE.md")
