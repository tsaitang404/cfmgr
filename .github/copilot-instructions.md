# GitHub Copilot 工作指导

## 项目上下文

参考以下文件了解项目详情：
- `.github/PROJECT.md` - 项目具体指导文件
- `docs/api/*.md` - API 规范文档 除特殊说明，一般遵循Restful设计原则
- `docs/database/*.md` - 数据库结构规范

## 开发环境

- **Python**: 使用 `pyenv` 管理版本，使用 `venv` 或 `uv` 管理虚拟环境
- **Node.js**: 使用 `nvm` 管理版本

## 代码规范

### Python 代码
- 遵循 PEP 8 编码规范
- 使用类型注解 (Type Hints)
- 函数和类必须有 docstring (Google 风格)
- 最大行长度: 100 字符
- 使用 `black` 进行代码格式化
- 使用 `ruff` 进行代码检查

示例:
```python
def process_data(items: list[str], limit: int = 10) -> dict[str, any]:
    """处理数据项并返回结果。
    
    Args:
        items: 要处理的字符串列表
        limit: 处理的最大数量
        
    Returns:
        包含处理结果的字典
        
    Raises:
        ValueError: 当 items 为空时
    """
    pass
```

### JavaScript/TypeScript 代码
- 使用 ESLint 推荐规则
- 优先使用 `const`，必要时使用 `let`
- 使用 async/await 而非 Promise.then()
- 文件名使用 kebab-case

### 通用规范
- 变量命名: 使用有意义的描述性名称
- 注释: 使用中文，解释"为什么"而非"是什么"
- 错误处理: 必须有适当的错误处理和日志记录
- 安全性: 避免硬编码密钥、验证所有输入

## 能力边界

专注一次只处理一个主要任务，避免同时处理多个复杂需求。
如果用户请求超出当前任务范围，礼貌地指出并建议分开处理。

## 工作步骤

### 1. 理解需求
- 阅读用户请求和相关文档
- 确认需要修改的文件范围
- 识别潜在的依赖关系

### 2. 设计方案
- 思考最简洁的实现方式
- 考虑错误处理和边界情况
- 评估对现有代码的影响

### 3. 实现代码
- 按照代码规范编写
- 添加必要的类型注解和文档
- 包含适当的错误处理
- 使用注释说明复杂逻辑

### 4. 测试验证
- 建议相应的测试用例
- 考虑单元测试和集成测试
- 提供测试运行命令

### 5. 文档更新
- 更新相关 README 或文档
- 添加使用示例
- 记录 API 变更

## 引用工具

### 开发工具
- **pyenv**: Python 版本管理 (`pyenv local 3.11`)
- **nvm**: Node.js 版本管理 (`nvm use`)
- **black**: Python 代码格式化 (`black src/`)
- **ruff**: Python 代码检查 (`ruff check src/`)
- **pytest**: Python 测试框架 (`pytest tests/`)


### 版本控制
- **git**: 版本控制
  - 提交前运行测试: `pytest`
  - 提交前格式化: `black src/ && ruff check src/`

## 测试要求

### 单元测试
- 覆盖率目标: 80%+
- 测试文件命名: `tests/test_*.py`
- 使用 pytest fixtures 管理测试数据
- Mock 外部依赖

示例:
```python
# tests/test_d1_manager.py
import pytest
from unittest.mock import Mock
from src.d1_manager import D1Manager

@pytest.fixture
def mock_d1():
    return Mock()

def test_query_success(mock_d1):
    """测试成功查询数据库"""
    manager = D1Manager(mock_d1)
    # ... 测试实现
```

### 集成测试
- 使用测试数据库和存储桶
- 测试完整的 API 流程
- 验证错误处理和边界情况

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_d1_manager.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 提交规范

### Commit Message 格式

遵循 Conventional Commits 规范:

```
<类型>: <描述>

[可选的正文]

[可选的脚注]
```

### 类型 (Type)
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构（不是新功能也不是修复）
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动
- `perf`: 性能优化



### 示例

```bash
# 新功能
feat: 添加批量查询支持

实现批量查询功能以提高性能，支持一次查询多个表。

Closes #123

# Bug 修复
fix: 修复文件上传时的编码问题

修正了非 ASCII 文件名上传失败的问题。

# 文档更新
docs: 更新 API 使用示例

添加了 R2 上传的完整代码示例。

# 重构
refactor: 简化路由匹配逻辑

使用正则表达式替代字符串匹配，提高可维护性。
```



## 进度追踪

当前阶段: **环境配置和项目初始化**

- [x] 验证项目需求
- [x] 创建项目文档结构
- [ ] 安装必要的依赖
- [ ] 配置开发工具
- [ ] 实现核心功能模块
- [ ] 编写单元测试
- [ ] 集成测试验证
- [ ] 部署配置
- [ ] 文档完善

参考 `.github/PROJECT.md` 查看详细的功能需求和实现计划。
