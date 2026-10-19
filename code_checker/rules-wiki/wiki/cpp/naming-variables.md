---
domain: cpp
rule_id: cpp-naming-variables
title: 变量命名规范
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.1 命名约定"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: [qt-var-qclass-lowercase]
related_pages:
  - [[cpp-naming-classes]]
  - [[cpp-naming-functions]]
  - [[cpp-naming-constants]]
  - [[cpp-naming-private-members]]
  - [[cpp-naming-namespaces]]
  - [[qt-var-qclass-lowercase]]
---

# 变量命名规范

## 规则条款

变量必须使用 **camelCase**（首字母小写，后续每个单词的首字母大写），无空格或符号分隔。命名应清晰表达变量所存储的数据，分为以下两类：
- **名词类变量**：用名词表示变量存储的"事物"，如 `userName`（存储用户名）、`orderId`（存储订单 ID）、`productPrice`（存储商品价格）
- **形容词/状态类变量**：用形容词或状态描述词表示变量的"状态属性"，常用于布尔值，如 `isValid`（是否有效）、`hasStock`（是否有库存）、`isConnected`（是否已连接）

禁止使用无意义的名称（如 `a`、`b`、`temp`、`data`、`info` 等），除非是短期循环变量（如 `i`、`j`、`k`）。

**跨域覆盖**：本规则是公共 C++ 硬约束（最高优先级），覆盖 Qt 域 `qt-var-qclass-lowercase`。Qt 下划线风格变量命名（如 `user_name`、`submit_button`）直接违反本规则 camelCase 要求。Qt 项目中的变量命名必须遵循 camelCase，不得使用 snake_case 风格。详情见 [[qt-var-qclass-lowercase]]。
## 正确示例

```cpp
// 名词类型 — 存储具体事物
std::string userName;        // 用户名
int orderId;                 // 订单 ID
double productPrice;         // 商品价格
std::vector<int> userIdList; // 用户 ID 列表

// 形容词/状态类 — 存储布尔状态
bool isValid;                // 是否有效
bool hasStock;               // 是否有库存
bool isConnected;            // 是否已连接
bool canEdit;                // 是否可编辑

// 循环变量 — 短期使用允许短名称
for (int i = 0; i < count; ++i) {
    // i 是合法的短期循环变量
}
```

## 错误示例

```cpp
// 错误：snake_case
std::string user_name;           // 应为 userName
int order_id;                    // 应为 orderId

// 错误：PascalCase
std::string UserName;            // 应为 userName（PascalCase 用于类名）
int OrderId;                     // 应为 orderId

// 错误：匈牙利命名法前缀
int iCount;                      // 应为 count 或 itemCount
std::string strName;             // 应为 name
bool bValid;                     // 应为 isValid

// 错误：无意义名称
int a;                           // 应使用有意义名称
std::string temp;                // 应为具体名称，如 tempFilePath
void* data;                      // 应为具体名称，如 rawImageData

// 错误：全大写（UPPER_CASE 仅用于常量）
int MAX_COUNT;                   // 非常量变量应为 maxCount
```

## 检查方法
1. 扫描所有局部变量、成员变量（非私有）、全局变量声明
2. 验证变量名首字母是否小写
3. 验证变量名中无下划线（私有成员 `m_` 前缀除外）
4. 验证变量名是否有明确含义（排除 `a`、`b`、`temp`、`data`、`info` 等）
5. 区分常量与变量：变量使用 camelCase，常量使用 UPPER_CASE
6. 正则模式：`(?:int|bool|double|std::\w+|[\w:]+(?:<[^>]*>)?)\s+[a-z][a-zA-Z0-9]*\s*[=;]`

## 修复指南

1. 将 snake_case 转换为 camelCase：`user_name` → `userName`
2. 将 PascalCase 转换为 camelCase：`UserName` → `userName`（注意区别于类名的 PascalCase）
3. 去掉匈牙利前缀：`iCount` → `count`，`strName` → `name`
4. 将无意义名称替换为描述性名称：`a` → `selectedIndex`，`temp` → `tempFilePath`
5. 为布尔变量补充 `is`/`has`/`can` 前缀：`valid` → `isValid`
6. 注意：重命名变量时需同步修改所有引用点

## 审查清单

- [ ] 所有变量名使用 camelCase（首字母小写）
- [ ] 名词类变量使用明确的名词命名
- [ ] 布尔类型变量使用 `is`/`has`/`can` 等前缀
- [ ] 无 snake_case 变量名（私有成员后缀 `_` 除外）
- [ ] 无 PascalCase 变量名
- [ ] 无匈牙利命名法前缀（i、str、b 等）
- [ ] 无无意义名称（排除短期循环变量 i、j、k）

## 关联页面

- [[cpp-naming-classes]] — 类命名（PascalCase，与变量 camelCase 有明显区别）
- [[cpp-naming-functions]] — 函数命名（同为 camelCase，但以动词开头）
- [[cpp-naming-constants]] — 常量命名（UPPER_CASE，与变量 camelCase 完全不同）
- [[cpp-naming-private-members]] — 私有成员命名（m_ 前缀 + camelCase 或 camelCase_ 后缀）
- [[cpp-naming-namespaces]] — 命名空间命名（全小写点分隔）
