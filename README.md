# SearXNG for Windows

[![SearXNG](https://img.shields.io/badge/SearXNG-2026.05.29-blue)](https://github.com/searxng/searxng)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-orange)](LICENSE)

**SearXNG for Windows** — 原生 Windows 移植版，无需 WSL、Docker 或虚拟机，开箱即用。

> 本仓库基于 [SearXNG](https://github.com/searxng/searxng) 官方最新版本 **[`2026.05.29` (0037d43)](https://github.com/searxng/searxng)** 深度适配 Windows 环境。
> 相较于原始仓库（基于旧版 SearXNG 的私有修改），这是一次**完整的跨大版本升级**：源码全部替换为官方最新版，引擎全面更新，配置体系重构，并修复了所有已知的 Windows 兼容性问题。

---

## 仓库介绍

### 目录结构

| 目录/文件 | 说明 |
|-----------|------|
| `python/` | 内置 Python 3.11.9 embeddable 环境 + 全部依赖 |
| `config/` | 配置文件目录（`settings.yml`, `limiter.toml`, `requirements.txt`） |
| `searxng.ico` | SearXNG 图标 |
| `SearXNG for Windows.lnk` | 启动快捷方式（带 SearXNG 图标） |
| `SearXNG for Windows.bat` | 命令行启动脚本 |

### 版本说明

| 项目 | 版本 |
|------|------|
| SearXNG 源码 | **[`2026.05.29`](https://github.com/searxng/searxng/commit/0037d43)** — 官方最新稳定版 |
| Python | 3.11.9 embeddable (win_amd64) |

### 25 种搜索引擎已就绪

出厂默认启用了 23 种搜索引擎，覆盖常用类别：

- **Google** 系：google, google images, google news, google video
- **Bing** 系：bing, bing images, bing news, bing video
- **DuckDuckGo** 系：duckduckgo, duckduckgo images, duckduckgo videos, duckduckgo news
- **百度**：baidu
- **学术**：google scholar, arxiv, pubmed, semantic scholar
- **IT 技术**：github, stackoverflow, wikipedia, ask ubuntu
- **社交**：reddit

> 可在 Web 界面的「首选项」页面自由启用/禁用更多搜索引擎（共 280+ 引擎）。

---

## 快速开始

双击 **`SearXNG for Windows.lnk`**（或运行 `SearXNG for Windows.bat`），启动后访问：

```
http://localhost:8888
```

### 启动效果示例

```
 * Serving Flask app 'searx.webapp'
 * Debug mode: off
 * Running on http://0.0.0.0:8888
```

---

## 使用本地 Python 环境

如果不想使用内置的 embedded Python，也可以用系统安装的 Python：

```bash
pip install -r config/requirements.txt
python ./python/Lib/site-packages/searx/webapp.py
```

---

## 代理配置

编辑 `config/settings.yml` 的 `outgoing` 部分：

```yaml
outgoing:
  proxies: "http://127.0.0.1:7897"   # 替换为你的代理地址
  request_timeout: 10.0
  max_retries: 3
```

---

## Windows 兼容性修改

相比官方版本，本仓库做了以下适配修改，确保在原生 Windows 环境下正常运行：

| 文件 | 修改内容 |
|------|---------|
| `searx/settings_loader.py` | 配置文件路径改为 `config/` 目录 |
| `searx/favicons/__init__.py` | 图标缓存路径改为 `config/` 目录 |
| `searx/version.py` | 兼容 Windows 下无 `LC_ALL`/`LANGUAGE` 环境变量 |
| `searx/network/client.py` | 设置 `WindowsSelectorEventLoopPolicy` 避免事件循环兼容性问题 |
| `searx/webutils.py` | 修复路径分隔符（`os.sep` → `/`），确保模板文件正常加载 |
| `searx/engines/__init__.py` | 禁用状态的引擎跳过 `setup()` 初始化，避免启动时非关键报错 |
| `searx/limiter.py` | 限流配置文件路径改为 `config/limiter.toml` |
| `searx/utils.py` | 兼容 `searx_useragent()` 旧函数名（部分引擎依赖） |
| `searx/valkeydb.py` | 移除 `pwd` 模块依赖（Unix-only），改用 `os.getenv('USERNAME')` |

---

## 从旧版本升级

如果你正在使用基于老版 SearXNG 的 `SearXNGforWindows`，本仓库的升级要点：

1. ✅ **源码全面替换** — 从旧版私有分支升级到官方 `2026.05.29`（0037d43）
2. ✅ **引擎全量更新** — 280+ 引擎全部替换为新版，23 个常用引擎默认启用
3. ✅ **配置重构** — 配置改存 `config/` 目录，与源码解耦
4. ✅ **依赖升级** — 所有 Python 依赖同步官方最新版本
5. ✅ **原生 Windows** — 纯 Python 实现，无需 WSL/Docker
6. ✅ **安全提升** — `safe_search` 默认开启（中等过滤），`autocomplete` 自带 Bing 建议

---

## 相关链接

- 官方 SearXNG 仓库：https://github.com/searxng/searxng
- 问题反馈：https://github.com/dcjk2010/SearXNGforWindows/issues
- 公共实例列表：https://searx.space
- 官方文档：https://docs.searxng.org/

---

## 许可证

[AGPL-3.0](LICENSE)
