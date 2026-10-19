---
title: §1.1 命名约定 — 常量应使用 UPPER_CASE
rule_id: fix-pattern/1-1-命名约定-常量应使用-upper_case
priority: pattern
related_pages: []
---

# §1.1 命名约定 — 常量应使用 UPPER_CASE

## 关联规则
- §1.1 命名约定 — 常量应使用 UPPER_CASE

## 代码特征
- **变量声明模式**：存在 `static const` 或 `static constexpr` 修饰的变量，其变量名以字母 `k` 开头，且后续部分采用 camelCase 命名（例如 `kObfuscatedKey`、`kMaxBufferSize`）。
- **变量命名特征**：变量名未使用全大写 UPPER_CASE 格式（例如 `KOBFUSCATED_KEY`）。
- **作用域限定**：该变量通常为函数局部 `static const` 或文件级 `static const`，而非类成员常量。
- **可选模式**：常量类型为 C 风格数组（如 `unsigned char kXxx[32]`），可附带建议升级为 `constexpr std::array`。

## 修复步骤
1. **重命名常量**：将变量名从 camelCase（如 `kObfuscatedKey`）修改为全大写 UPPER_CASE 格式（如 `KOBFUSCATED_KEY`），确保所有字母大写，单词间使用下划线分隔。
2. **提升常量语义（可选）**：如果原始声明为 `static const`，可将其升级为 `static constexpr` 以明确表达编译期常量语义，类型和初始值保持不变。
3. **同步引用处**：搜索代码中所有对该常量的引用（包括声明处和使用处），将引用名称同步更新为新的 UPPER_CASE 名称。
4. **数组类型优化（可选）**：如果常量为 C 风格数组（如 `unsigned char name[32]`），建议将其类型替换为 `std::array<unsigned char, 32>`，并调整语法为大括号初始化列表。

**执行示例**：
- 旧代码：`static const unsigned char kObfuscatedKey[32] = { ... };`
- 新代码：`static constexpr std::array<unsigned char, 32> KOBFUSCATED_KEY = { ... };`
- 旧引用：`key[i] = static_cast<char>(kObfuscatedKey[i] ^ 0xAA);`
- 新引用：`key[i] = static_cast<char>(KOBFUSCATED_KEY[i] ^ 0xAA);`

## 来源
run: 20260728-104017-f51e3114, 迭代 3 轮, 最终 8/10
---