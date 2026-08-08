# SearXNGforWindows 升级方案（UPGRADE GUIDE）

> 本文档记录如何把 <https://github.com/searxng/searxng> 的最新代码合并进本仓库，供下次升级照做。

## 一、本仓库与上游的关系（为什么不能直接 git merge）

本仓库把上游 searx **源码镜像**进 `python/Lib/site-packages/searx/`（嵌入式 Python 的包目录），
配置放在 `config/`，启动脚本 `SearXNG for Windows.bat` 直接跑 `searx/webapp.py`。

上游的 `searx/` 在仓库根目录、历史与本地不关联 → **无法 `git merge upstream/master`**，
采用「tarball 同步 + 本地补丁重放」策略。已配置 `upstream` remote 便于 diff 对比（方案 B）。

## 二、上游信息

| 项 | 值 |
|----|----|
| 上游仓库 | https://github.com/searxng/searxng |
| 分支 | `master`（searxng 不打 release tag，版本号即日期，如 `2026.08.06`） |
| 本地 remote | `git remote add upstream https://github.com/searxng/searxng`（已配置） |
| 本地基线 | 2026-08-06（b023a28bab），记录于 `python/Lib/site-packages/searx/version_frozen.py` |
| PyPI | **不可用**：PyPI 上的 `searxng` 是 `0.0.0.dev0` 占位包，不能 pip 升级 |

## 三、升级总流程（每次照此执行）

1. **准备**：确认实例已停止；`git status` 干净（有未提交改动先提交为检查点）。
2. **获取上游源码**：
   ```bash
   # 方式一：tarball（推荐，不需要 git 历史）
   curl -sL https://github.com/searxng/searxng/archive/master.tar.gz -o /tmp/master.tgz
   mkdir -p /tmp/sx-master && tar xzf /tmp/master.tgz -C /tmp/sx-master --strip-components=1

   # 方式二：git fetch（用于 diff 对比）
   git fetch upstream
   ```
3. **评估差异**（可选但建议）：
   ```bash
   diff -rq --strip-trailing-cr /tmp/sx-master/searx python/Lib/site-packages/searx | head -60
   ```
   ⚠️ Windows 的 CRLF 会让 diff 全部报 differ，**必须加 `--strip-trailing-cr`**。
4. **同步 + 重放补丁**（一条命令搞定）：
   ```bash
   python scripts/upgrade/sync_searx.py /tmp/sx-master/searx
   ```
   脚本会：镜像覆盖 + 删除本地独有文件（保留 version_frozen.py）+ 重放全部 Windows 补丁 + ast 语法校验。
5. **配置清理**：启动一次（或看启动日志），若出现
   `Cannot load engine "xxx" ... FileNotFoundError: ... engines\xxx.py`，
   说明 master 已删除该引擎 → 从 `config/settings.yml` **删除对应条目**
   （注意：`disabled: true` 的引擎也会被 import，删条目是唯一干净办法）。
6. **依赖检查**：新引擎可能需要新 pip 包（例：bilibili 需要 `tzdata`，Windows 无系统时区库）。
   对比上游 `requirements.txt` 与 `config/requirements.txt`，用嵌入式 Python 安装：
   `./python/python.exe -m pip install <包>`，并同步更新 `config/requirements.txt`。
7. **版本与文档**：更新 `python/Lib/site-packages/searx/version_frozen.py`（VERSION_STRING 改为新版本）、
   README 徽章与版本表（含“Windows 兼容性修改”补丁表）。
8. **验证**：
   ```bash
   ./python/python.exe -c "import searx; from searx.version import VERSION_STRING; print(VERSION_STRING)"
   ./python/python.exe python/Lib/site-packages/searx/webapp.py   # 另开终端
   curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8888/   # 期望 200
   ```
   再开浏览器验证搜索出结果。
9. **提交与推送**：
   ```bash
   git add -A && git commit -m "升级到 SearXNG master (<新版本>)"
   git push origin main
   ```

## 四、Windows 适配补丁清单（sync_searx.py 自动重放）

| 文件 | 补丁内容 | 说明 |
|------|---------|------|
| `settings_loader.py` | `DEFAULT_SETTINGS_FILE` 指向 `CWD/config/settings.yml` | 配置体系核心，必保 |
| `limiter.py` | `limiter.toml` 路径 → `config/`；补 `import os` | |
| `favicons/__init__.py` | `favicons.toml` 路径 → `config/`；补 `import os` | |
| `network/client.py` | 补 `import sys`；win32 下 `WindowsSelectorEventLoopPolicy` | Windows asyncio 兼容 |
| `valkeydb.py` | 去掉 `import pwd`；改用 `os.getenv('USERNAME')` | `pwd` 是 Unix-only |
| `version.py` | `LC_ALL`/`LANGUAGE` 仅非 win32 注入；补 `import sys` | Windows 下 git 子进程环境 |
| `webutils.py` | 静态文件路径 `os.sep` → `/`（2 处） | 模板/静态资源加载 |
| `engines/__init__.py` | disabled 引擎也注册 logger + 补默认分类 | 偏好页可见性 |
| `botdetection/trusted_proxies.py` | `trusted_proxies` 为空时跳过判断 | 防误报直连 IP |

**已弃用的旧补丁（不要重放）**：`utils.py` 的 `searx_useragent()` / `gen_gsa_useragent()`
——上游已删除 `gsa_useragents.txt`，且唯一调用方 `stract.py` 已被上游删除。

## 五、踩坑记录

1. **CRLF**：diff 必须 `--strip-trailing-cr`；python 读写用 `newline=''` 保留原行尾；
   patch 工具会把「CRLF + 中文」的 README 判为 binary → 用 python 脚本做字符串替换。
2. **docstring 陷阱**：向文件插 `import` 时，简单扫描 `from xxx` 会把 docstring 里的
   `from the :ref:`botdetection`:` 误判为 import → 插进 docstring → 运行期 `NameError`。
   `ensure_import` 必须先定位 docstring 结束位置再找 import 块。
3. **死引擎**：2026-05-29 → 2026-08-06 间上游删除了 `aol`、`presearch`、`reddit`、`svgrepo`；
   config 条目必须删（disabled 也会被 import 并报错）。
4. **tzdata**：Windows 无系统时区库，`ZoneInfo("Asia/Shanghai")` 等调用需要 pip 包 `tzdata`
   （2026-08-06 升级已装入嵌入式 Python，版本 2026.3，已写入 config/requirements.txt）。
5. **MSYS 路径**：git-bash 中把 `/tmp/...`、`/e/...` 传给 python.exe 不会被自动转换，
   需 `cygpath -w` 显式转换（`sync_searx.py` 内部用绝对路径，从仓库根运行即可）。
6. **CAPTCHA 不是版本问题**：duckduckgo（suspended_time=0）与 baidu（suspended_time=3600）
   的 CAPTCHA 是 IP 反爬，升级代码不解决。缓解手段：
   - 百度悬挂时长：`config/settings.yml` 的 `search.suspended_times.SearxEngineCaptcha`（当前 3600）调小；
   - DDG 刷屏：接受（IP 滑窗约 1 小时自动解封，浏览器同 IP 手动搜一次立即解封），
     或把 `duckduckgo.py` 的 `suspended_time=0` 改为 `None` 让它跟随 settings 值（注意：这是新补丁，升级要重放）；
   - 换出口 IP：searxng 支持 per-engine `proxies` 配置（如给 baidu 配国内住宅代理）。

## 六、当前升级记录

**2026-08-06 升级**：上游 `b023a28bab` → 本地提交 `94f26d4`
- 镜像同步 searx 源码（978 files changed, +23497/−12903）
- 重放 9 个文件补丁；弃用 utils.py 两个旧补丁
- config/settings.yml 删除 9 个死引擎条目（aol×3 / presearch×4 / reddit / svgrepo）
- 新增依赖 `tzdata==2026.3`；version_frozen.py 2026.08.06；README 更新
- 验证：import OK、webapp HTTP 200、搜索返回真实结果、启动日志无引擎加载错误
