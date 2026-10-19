---
domain: cpp
rule_id: cpp-use-containers
title: 使用标准容器
priority: main
source_file: rules/C++编程规范.md
source_section: "2.2 内存泄漏预防"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-bare-new-delete]]
  - [[cpp-weak-ptr-cycles]]
---

# 使用标准容器

## 规则条款
使用标准容器（`std::vector`、`std::array`、`std::string`、`std::map` 等）管理
数据集合，禁止使用手动管理的 C 风格数组、手动 `new[]`/`delete[]`、`malloc`/`free`。

## 正确示例
```cpp
#include <vector>
#include <array>
#include <string>
#include <map>

// 动态数组 -> vector
std::vector<int> values;
values.reserve(100);
values.push_back(42);

// 定长数组 -> array
std::array<double, 3> coords = {0.0, 1.0, 2.0};

// 字符串 -> string
std::string name = "example";
name += ".txt";

// 键值对 -> map
std::map<std::string, int> scores;
scores["alice"] = 100;

// 多维数组 -> vector of vector 或扁平化
std::vector<std::vector<int>> matrix(10, std::vector<int>(10, 0));
```

## 错误示例
```cpp
// C 风格数组 -> 无边界检查
int values[100];

// 手动分配 -> 容易泄漏
int* arr = new int[100];
// ...
delete[] arr;  // 异常路径未覆盖

// C 风格字符串 -> 不安全
char name[256];
strcpy(name, "example");  // 缓冲区溢出风险

// malloc/free -> C 风格，不调用构造函数
Widget* w = (Widget*)malloc(sizeof(Widget));
free(w);
```

## 检查方法
使用正则表达式扫描：

1. 匹配 C 风格数组声明：`\w+\s+\w+\s*\[` `[^]]*\]\s*[=;]`（排除函数参数中的数组语法）。
2. 匹配 `new\s+\w+\s*\[`（数组 new）。
3. 匹配 `delete\s*\[\]`（数组 delete）。
4. 匹配 `malloc\s*\(` 和 `free\s*\(`（C 内存函数）。
5. 匹配 `char\s+\w+\s*\[`（C 风格字符串声明）。

## 修复指南
1. `T arr[N]` 定长数组替换为 `std::array<T, N> arr`。
2. `T* arr = new T[n]` 替换为 `std::vector<T> arr(n)`。
3. `char buf[SIZE]` 替换为 `std::string buf` 或 `std::array<char, SIZE> buf`。
4. `malloc`/`free` 替换为 `new`/`delete`（再进一步替换为智能指针）。
5. 多维数组使用嵌套 `vector` 或扁平化一维 `vector` 加索引计算。

## 审查清单
- [ ] 无 C 风格数组声明（`T arr[N]`）
- [ ] 无 `new T[n]` / `delete[]` 手动操作
- [ ] 无 `char[]` 裸字符数组
- [ ] 无 `malloc` / `free` / `calloc` / `realloc` 调用
- [ ] 所有集合均使用标准容器管理
- [ ] 涉及 C API 的必要转换已加 `// NOLINT(C-35)` 注释

## 关联页面
- [[cpp-no-bare-new-delete]] — 禁止裸 new/delete，统一使用智能指针
- [[cpp-weak-ptr-cycles]] — 循环引用场景下 weak_ptr 使用
