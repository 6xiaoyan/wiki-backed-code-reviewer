---
domain: cpp
rule_id: cpp-no-cstyle-strings-arrays
title: 禁止 C 风格字符串和数组
priority: main
source_file: rules/C++代码规范.md
source_section: "§7 明确禁止项"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-macro-constants]]
  - [[cpp-no-cstyle-variadic]]
---

# 禁止 C 风格字符串和数组

## 规则条款
禁止使用 C 风格字符串（`char*`、`char[]`）和 C 风格数组（`T[]`、`T*` 作为数组）。优先使用 `std::string`、`std::string_view` 管理字符串，使用 `std::vector`、`std::array` 管理数组。C 库 API 调用时允许使用 `char*` 并标注 `// NOLINT`。

## 正确示例
```cpp
// 字符串：使用 std::string
std::string name = "Hello";
std::string_view view = name;  // 非拥有型视图
const std::string& ref = name;  // 引用传递

// 动态数组：使用 std::vector
std::vector<int> values = {1, 2, 3, 4, 5};
values.push_back(6);

// 固定大小数组：使用 std::array
std::array<int, 5> fixedValues = {1, 2, 3, 4, 5};

// 字符缓冲区：使用 std::string
std::string buffer(MaxSize, '\0');
someCLibrary(buffer.data(), buffer.size());  // NOLINT(C-21)

// 字节缓冲区：使用 std::vector<std::byte>
std::vector<std::byte> byteBuffer(1024);

// 二维数组：使用嵌套 std::vector 或 std::array
std::array<std::array<int, 4>, 3> matrix{};
```

## 错误示例
```cpp
// C 风格字符串
char name[256] = "Hello";           // 固定大小，易溢出
char* dynamicName = new char[256];  // 手动管理内存
const char* text = "world";         // 应用 std::string_view

// C 风格数组
int values[100];                    // 大小不明，无边界检查
int* dynamicValues = new int[100];  // 裸 new[]，手动管理

// 函数签名中的 C 风格
void process(char* buffer, int size);     // 分离的 size 易出错
char** getListOfNames(int* count);        // 输出参数模式
void fillData(int arr[10]);               // 数组退化为指针

// 字符串连接
char result[256];
strcpy(result, "Hello ");           // 缓冲区溢出风险
strcat(result, "World");            // 无长度检查
```

## 检查方法
1. 正则检测：搜索 `char\s+\w+\[`（C 风格字符数组声明）
2. 正则检测：搜索 `\w+\s+\w+\[`（一般 C 风格数组声明）
3. 正则检测：搜索 `new\s+\w+\[`（C 风格动态数组分配）
4. 排除项：C 库 API 调用中的 `char*` 参数（需 `// NOLINT` 标注）
5. 排除项：`extern "C"` 块内的 C 接口声明

## 修复指南
1. `char name[N]` → `std::string name;` 或 `std::array<char, N> name;`
2. `const char* text` → `std::string_view text`（非拥有）或 `std::string text`（拥有）
3. `int values[N]` → `std::array<int, N> values{};`
4. `new T[N]` → `std::vector<T> v(N);` 或 `std::make_unique<T[]>(N)`
5. `void f(char* buf, int len)` → `void f(std::string& buf)` 或 `void f(std::span<char> buf)`
6. 函数返回 `char**` → `std::vector<std::string>`
7. C 库互操作处：保留 C 接口但添加 `// NOLINT(C-21)`

## 审查清单
- [ ] 不存在 `char[]` 或 `char*` 的字符串声明
- [ ] 不存在 `T arr[N]` 的 C 风格数组声明
- [ ] 不存在 `new T[]` 的动态数组分配
- [ ] C 库互操作的 C 风格用法已 NOLINT 标注
- [ ] 函数参数使用 std::string_view 或 const std::string&

## 关联页面
- [[cpp-no-macro-constants]] — 禁止宏定义常量/函数
- [[cpp-no-varargs]] — 禁止可变参数
