#!/bin/bash
#
# Pre-commit Hook 安装脚本
# 
# 使用方法：
#   ./scripts/install-hooks.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Installing Git pre-commit hooks..."
echo ""

# 检查是否在 Git 仓库中
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ Error: Not a Git repository"
    exit 1
fi

# 复制 pre-commit 钩子
HOOK_SOURCE="$PROJECT_ROOT/.git/hooks/pre-commit"
if [ -f "$HOOK_SOURCE" ]; then
    echo "✅ Pre-commit hook already exists at: $HOOK_SOURCE"
else
    echo "❌ Pre-commit hook not found"
    echo "   Expected location: $HOOK_SOURCE"
    exit 1
fi

# 确保钩子可执行
chmod +x "$HOOK_SOURCE"
echo "✅ Pre-commit hook is executable"

# 检查虚拟环境
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo ""
    echo "⚠️  Virtual environment not found"
    echo "   Creating virtual environment..."
    cd "$PROJECT_ROOT"
    python -m venv .venv
    echo "✅ Virtual environment created"
fi

# 激活虚拟环境并安装工具
echo ""
echo "📦 Installing development tools..."
cd "$PROJECT_ROOT"
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

pip install -q --upgrade pip
pip install -q black ruff mypy pytest pytest-asyncio

echo "✅ Development tools installed"

# 测试工具
echo ""
echo "🧪 Testing tools..."
black --version | head -1
ruff --version
mypy --version

echo ""
echo "✅ Pre-commit hook installation completed!"
echo ""
echo "📝 Usage:"
echo "   - Hooks will run automatically on 'git commit'"
echo "   - To skip hooks: git commit --no-verify"
echo "   - To run manually: .git/hooks/pre-commit"
echo ""
echo "⚙️  Configuration:"
echo "   - Edit .pre-commit-config to customize behavior"
echo "   - Edit pyproject.toml for tool-specific settings"
echo ""
