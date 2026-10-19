---
domain: cpp
rule_id: cpp-indentation
title: 缩进规范
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.3 代码格式"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-braces]]
  - [[cpp-line-width]]
  - [[cpp-operator-spacing]]
  - [[cpp-parameter-alignment]]
---

# 缩进规范

## 规则条款

所有 C++ 源代码文件必须使用**4 个空格**进行缩进，严格禁止使用制表符（Tab 字符 `\t`）。
具体要求：
- 每一个逻辑嵌套层级增加 4 个空格
- 不得使用 Tab 字符替代空格缩进
- 不得使用 2 个空格或其他非 4 倍数的空格数作为缩进单位
- 预处理指令（`#include`、`#define`、`#ifdef` 等）顶格书写，不缩进
- `public:`、`protected:`、`private:` 访问控制标签与 `class` 关键字对齐（或在某些风格中缩进 1 个层级），项目中推荐缩进 1 个层级（4 空格）
- `case` 标签与 `switch` 关键字对齐（或在某些风格中缩进 1 个层级），项目中推荐缩进 1 个层级（4 空格）
## 正确示例

```cpp
#include <string>
#include <vector>

namespace myproject {
namespace network {

class HttpClient {
public:
    HttpClient(const std::string& host, int port);

    void sendRequest(const std::string& data);
    std::string receiveResponse();

private:
    static constexpr int DEFAULT_TIMEOUT = 30;

    std::string m_host;
    int m_port;
};

void processItems(const std::vector<int>& items) {
    for (const auto& item : items) {
        if (item > 0) {
            handlePositive(item);
        } else {
            handleNonPositive(item);
        }
    }

    switch (items.size()) {
    case 0:
        logWarning("empty list");
        break;
    case 1:
        logInfo("single item");
        break;
    default:
        logInfo("multiple items");
        break;
    }
}

} // namespace network
} // namespace myproject
```

## 错误示例

```cpp
// 2-space indent — wrong
class HttpClient {
  public:
    HttpClient(const std::string& host, int port);
  private:
    std::string m_host;
};

// 8-space indent — wrong
void processItems(const std::vector<int>& items) {
        for (const auto& item : items) {
                if (item > 0) {
                        handlePositive(item);
                }
        }
}

// tab characters — wrong (shown as \t here)
void sendData() {
\tif (isConnected()) {
\t\ttransferData();
\t}
}
```

## 检查方法
1. 对每个源代码文件（`.h`、`.hpp`、`.cpp`、`.cc`），逐行扫描行首空白。
2. **Tab 检查**：扫描文件中是否包含 `\t` 字符（任何位置）。正则：`\t`。若匹配，立即标记违规。
3. **缩进深度检查**：对每行非空行，提取行首连续空格数。
   - 每级缩进 = 4 的倍数。若空格数为 `n`，则 `n % 4 != 0` 时标记为违规。
   - 正则辅助：`^ {1,3}(?=\S)`、`^ {5,7}(?=\S)`、`^ {9,11}(?=\S)` 等非 4 倍数的缩进。
4. **预处理指令检查**：若行以 `#` 开头（预处理指令），行首不应有缩进空格（允许在 `#` 前无空格）。正则：`^\s+#\s*(include|define|ifdef|ifndef|if|else|elif|endif|pragma|error|warning)`，标记警告（某些旧代码允许 `#` 前有空格的写法）。
5. **混合检查**：同一文件内同时出现 Tab 和空格缩进，标记为严重违规。
## 修复指南

1. **统一转换为 4 空格**：
   - VS Code：`Ctrl+Shift+P` → "Convert Indentation to Spaces"，设置 Tab Size 为 4。
   - Visual Studio：Edit → Advanced → Untabify Selected Lines。
   - 命令行：使用 `expand -t 4` 将 Tab 转换为 4 空格。
2. **调整缩进深度**：使用 IDE 的自动缩进功能重新格式化整个文件。
3. **配置编辑器**：将 Tab 键设置为插入 4 个空格（而不是 Tab 字符），设置 Tab Size = Indent Size = 4。
4. **项目级配置**：在项目根目录放置 `.editorconfig` 文件：
   ```ini
   [*.{cpp,h,hpp}]
   indent_style = space
   indent_size = 4
   tab_width = 4
   ```

## 审查清单

- [ ] 文件中是否不存在 Tab 字符（`\t`）
- [ ] 每行缩进空格数是否为 4 的倍数
- [ ] 同一文件内缩进宽度是否一致（不是 2/4/8 混用）
- [ ] 预处理指令是否顶格
- [ ] 项目是否有 `.editorconfig` 配置文件统一设置

## 关联页面

- [[cpp-braces]]
- [[cpp-line-width]]
- [[cpp-operator-spacing]]
- [[cpp-parameter-alignment]]
