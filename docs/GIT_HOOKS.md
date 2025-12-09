# Git Pre-commit Hook 使用指南

## 概述

项目配置了 Git pre-commit 钩子，在每次提交前自动执行代码质量检查，确保代码符合规范。

## 自动执行的检查

### 1. Black 代码格式化 ✨
- 自动格式化 Python 代码
- 统一代码风格
- 行长度限制：100 字符
- 修改后自动 `git add`

### 2. Ruff 代码质量检查 🔍
- 检查代码风格问题
- 自动修复可修复的问题
- 检查导入顺序
- 类型注解升级（Python 3.13+）
- 修复后自动 `git add`

### 3. MyPy 类型检查 🔎
- 静态类型检查
- **非阻塞**（仅显示警告）
- 帮助发现潜在类型错误

## 安装

### 方法 1: 使用安装脚本（推荐）

```bash
./scripts/install-hooks.sh
```

### 方法 2: 手动配置

```bash
# 确保钩子可执行
chmod +x .git/hooks/pre-commit

# 安装开发工具
pip install black ruff mypy pytest pytest-asyncio
```

## 使用

### 正常提交

钩子会自动运行：

```bash
git add .
git commit -m "feat: add new feature"
```

输出示例：
```
🔍 Running pre-commit checks...

📝 Step 1/3: Formatting code with Black...
✅ Code formatting is correct

🔍 Step 2/3: Checking code with Ruff...
✅ Code quality check passed

🔎 Step 3/3: Type checking with MyPy...
✅ Type checking passed

✅ All pre-commit checks passed!
```

### 跳过钩子

紧急情况下可以跳过检查：

```bash
git commit --no-verify -m "hotfix: urgent fix"
```

⚠️ **不推荐经常使用**，会降低代码质量。

### 手动运行检查

在提交前手动测试：

```bash
# 运行完整检查
.git/hooks/pre-commit

# 或分别运行
black src/ tests/
ruff check src/ --fix
mypy src/
```

## 配置

### .pre-commit-config

自定义钩子行为：

```ini
[black]
enabled = true
line-length = 100

[ruff]
enabled = true
blocking = true  # 失败时阻止提交

[mypy]
enabled = true
blocking = false  # 仅警告，不阻止提交

[general]
auto-install = true  # 自动安装工具
auto-add = true      # 自动 git add 修改的文件
```

### pyproject.toml

配置工具行为：

```toml
[tool.black]
line-length = 100
target-version = ['py313']

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.13"
ignore_missing_imports = true
```

## 常见问题

### Q: 钩子执行失败怎么办？

**A**: 查看错误输出并修复问题：

```bash
# Black 格式化失败 -> 代码会自动格式化
# Ruff 检查失败 -> 查看错误并手动修复
# MyPy 失败 -> 仅警告，不会阻止提交
```

### Q: 如何临时禁用某个检查？

**A**: 编辑 `.pre-commit-config` 文件：

```ini
[ruff]
enabled = false  # 禁用 Ruff 检查
```

### Q: 钩子运行很慢？

**A**: 
- 只检查 `src/` 目录，已排除 `python_modules/`
- 使用虚拟环境缓存工具
- 正常情况下 < 5 秒

### Q: 如何更新钩子？

**A**: 重新运行安装脚本：

```bash
./scripts/install-hooks.sh
```

### Q: 团队其他成员如何使用？

**A**: 克隆项目后运行：

```bash
# 设置环境
pyenv local 3.13
python -m venv .venv
source .venv/bin/activate

# 安装钩子
./scripts/install-hooks.sh

# 完成！
git commit -m "test"
```

## 最佳实践

1. **提交前先测试**: 运行 `pytest` 确保测试通过
2. **小步提交**: 每次提交一个功能，减少冲突
3. **有意义的消息**: 使用规范的 commit message
4. **及时修复警告**: 不要忽略 MyPy 的类型警告
5. **不要跳过检查**: 除非绝对必要

## 工作流示例

```bash
# 1. 修改代码
vim src/d1_manager.py

# 2. 运行测试
pytest tests/test_d1_manager.py -v

# 3. 提交（自动检查）
git add src/d1_manager.py
git commit -m "feat: add new query method"

# 4. 如果检查失败，修复后重新提交
git add .
git commit -m "feat: add new query method"

# 5. 推送
git push
```

## 故障排除

### 虚拟环境未激活

```bash
# 错误: command not found: black
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### 工具未安装

```bash
pip install black ruff mypy pytest pytest-asyncio
```

### 权限问题

```bash
chmod +x .git/hooks/pre-commit
chmod +x scripts/install-hooks.sh
```

## 相关资源

- [Black 文档](https://black.readthedocs.io/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [MyPy 文档](https://mypy.readthedocs.io/)
- [Git Hooks 文档](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)

---

**维护者**: [@tsaitang404](https://github.com/tsaitang404)  
**最后更新**: 2025年12月9日
