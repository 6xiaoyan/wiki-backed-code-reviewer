---
domain: cpp
rule_id: cpp-no-reinterpret-c-cast
title: 禁止 reinterpret_cast 和 C 风格转换
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
  - [[cpp-no-cstyle-strings-arrays]]
  - [[cpp-no-macro-constants]]
---

# 禁止 reinterpret_cast 和 C 风格转换

## 规则条款
禁止使用 `reinterpret_cast` 和 C 风格类型转换（`(Type)value`）。应使用 `static_cast`、`dynamic_cast`、`const_cast` 等语义明确的 C++ 转换操作符。`reinterpret_cast` 与平台相关、不安全且绕过类型系统，C 风格转换意图不清、难以搜索定位。与 C 库互操作时允许 `reinterpret_cast` 并标注 `// NOLINT(C-11)`。

## 正确示例
```cpp
// 数值类型转换：static_cast
double d = 3.14;
int i = static_cast<int>(d);

// 基类到派生类（确保安全）：dynamic_cast
Base* base = getBase();
if (auto* derived = dynamic_cast<Derived*>(base)) {
    derived->specificMethod();
}

// void* 转换：static_cast
void* rawPtr = someApi();
auto* typedPtr = static_cast<MyType*>(rawPtr);

// 移除 const 属性：const_cast
const std::string& getConstRef();
auto& mutableRef = const_cast<std::string&>(getConstRef());

// 枚举与整数互转：static_cast
enum class Color { Red, Green, Blue };
int colorVal = static_cast<int>(Color::Red);
Color color = static_cast<Color>(colorVal);

// 指针与整数互转：reinterpret_cast + NOLINT（仅 C 库互操作）
// static_assert(sizeof(uintptr_t) >= sizeof(void*));
auto handle = reinterpret_cast<uintptr_t>(nativeHandle);  // NOLINT(C-11)
```

## 错误示例
```cpp
// C 风格转换
int value = (int)3.14;                    // 应使用 static_cast<int>
char* ptr = (char*)malloc(100);           // 应使用 static_cast<char*>
Base* base = (Base*)derived;              // 意图不明

// 函数指针上的 C 风格转换
using Callback = void(*)(int);
Callback cb = (Callback)dlsym(handle, "myFunc");  // 难以审查

// reinterpret_cast 的不当使用
auto ptr = reinterpret_cast<Derived*>(base);  // 应使用 dynamic_cast
int x = reinterpret_cast<int>(myObj);          // 完全错误，无 NOLINT

// reinterpret_cast 用于类型双关
float f = 1.0f;
int bits = reinterpret_cast<int&>(f);  // 应用 std::bit_cast（C++20）或 memcpy
```

## 检查方法
1. 正则检测：搜索 `reinterpret_cast` 关键字
   - 排除：后跟 `// NOLINT(C-11)` 的行
2. 正则检测：搜索 C 风格转换模式（括号包围类型名后跟表达式）
   - 模式较复杂，需要上下文分析区分函数调用和类型转换
   - 重点：`(int)`、`(double)`、`(char)`、`(void*)`、`(TypeName)` 等
3. 验证 C 风格转换无法用 `static_cast` 替代
4. `reinterpret_cast` 仅在 C 库互操作且标注 NOLINT 时允许

## 修复指南
1. `(Type)expr` → `static_cast<Type>(expr)`
2. 基类→派生类向下转换 → `dynamic_cast<Derived*>(base)`
3. 去除 const → `const_cast<Type>(expr)`
4. `void*` 转换 → `static_cast<Type*>(voidPtr)`
5. 类型双关（float?int）→ `std::bit_cast<T>(value)`（C++20）或 `std::memcpy`
6. 函数指针转换 → `reinterpret_cast` + `// NOLINT(C-11)`（C 库互操作）
7. 网络/文件序列化 → 使用 `std::memcpy` 或序列化库

## 审查清单
- [ ] 不存在 `reinterpret_cast`（C 库互操作且 NOLINT 除外）
- [ ] 不存在 C 风格转换 `(Type)value`
- [ ] `dynamic_cast` 返回指针时检查了 nullptr
- [ ] `const_cast` 的使用有充分理由
- [ ] 类型双关使用了 std::bit_cast 或 memcpy

## 关联页面
- [[cpp-no-cstyle-strings-arrays]] — 禁止 C 风格字符串和数组
- [[cpp-no-macro-constants]] — 禁止宏定义常量/函数
