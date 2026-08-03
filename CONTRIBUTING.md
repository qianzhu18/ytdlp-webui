# Contributing to Muku

感谢你愿意改进幕库。Bug 修复、平台适配、测试、文档和使用反馈都很有价值。

## 开始之前

- 搜索现有 Issue，避免重复讨论
- Bug 请提供最小复现、系统、Python 版本和 `muku doctor --json` 中不含密钥的相关字段
- 新平台或较大功能请先开 Issue，说明输入、预期产物、认证方式和维护成本
- 不要提交 API Key、Cookies、`.env`、私人下载内容或生成产物

## 本地开发

```bash
git clone https://github.com/qianzhu18/Muku.git
cd Muku
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -e . pytest
python -m pytest -q
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -e . pytest
python -m pytest -q
```

## 改动原则

- 保持 Python `3.10+` 兼容
- 优先复用现有 CLI、配置和产物契约
- 行为改动应补测试；修复回归时测试需要能覆盖原始失败场景
- 不要把某个平台的临时绕过扩散到通用链路
- 用户可见命令、配置或默认值变化时同步更新 README 或 `docs/`
- 新依赖必须说明用途、体积和维护风险

## 提交 Pull Request

PR 请保持单一目标，并写清：

- 问题与用户影响
- 实现方式和取舍
- 验证命令及结果
- 是否改变 CLI、配置、产物格式或平台行为

提交前至少运行：

```bash
python -m pytest -q
python -m webui.cli doctor --json
docker compose config --quiet
```

涉及打包时还需要构建 wheel，并在仓库外执行 `scripts/smoke-installed-package.py`。CI 会在 Ubuntu、macOS、Windows 上继续验证。

## 行为与安全

参与项目即表示同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全漏洞不要公开提交，请按 [SECURITY.md](SECURITY.md) 报告。
