---
domain: cpp
rule_id: cpp-no-throw-dtor
title: 析构函数禁止抛异常
priority: main
source_file: rules/C++代码规范.md
source_section: "§3.2 内存泄漏预防 / §4.1 异常使用规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-noexcept-spec]]
  - [[cpp-no-throw-spec]]
  - [[cpp-exception-not-for-flow]]
---

# 析构函数禁止抛异常

## 规则条款
禁止在析构函数中抛出异常。C++11 起析构函数默认为 `noexcept(true)`，在析构函数中抛出异常会导致 `std::terminate()` 被调用，引发程序异常终止。此外，在栈展开过程中如果析构函数抛出第二个异常，同样会直接终止程序。

## 正确示例
```cpp
#include <string>
#include <fstream>
#include <iostream>

class SafeResource {
public:
    ~SafeResource() noexcept {  // 显式 noexcept 或依赖默认
        try {
            // 可能失败的操作
            if (file.is_open()) {
                file.close();
            }
        } catch (const std::exception& e) {
            // 吞下异常并记录，绝不重新抛出
            std::cerr << "Destructor warning: " << e.what() << std::endl;
        }
    }

private:
    std::ofstream file;
};

class BetterResource {
public:
    // 提供显式 close/cleanup，让调用方有机会处理错误
    void close() {
        file.close();  // 调用方可捕获异常
    }

    ~BetterResource() noexcept {
        // 析构仅做最低限度的清理，不再尝试可能失败的操作
        if (file.is_open()) {
            file.close();  // close 在析构中一般不会失败
        }
    }

private:
    std::ofstream file;
};
```

## 错误示例
```cpp
class DangerousResource {
public:
    ~DangerousResource() {  // 默认 noexcept(true)，但实际可能抛异常
        if (needsCleanup) {
            throw std::runtime_error("cleanup failed");  // 触发 std::terminate()
        }
    }
    bool needsCleanup = true;
};

class DoubleFaultRisk {
    std::vector<DangerousResource> resources;
    // 如果一个 DangerousResource 析构抛异常，
    // 后续元素的析构可能造成双异常 → std::terminate()
};
```

## 检查方法

1. 正则扫描析构函数体内是否包含 `throw\s` 语句。
2. 正则扫描析构函数内是否调用了可能抛出异常且未被 try-catch 包裹的函数。
3. 检查析构函数是否未标记 `noexcept` 且包含可能抛异常的操作。

正则参考：
```
~\s*\w+\s*\(\s*\).*\{  # 匹配析构函数签名
# 在匹配体内搜索：
\bthrow\s
```

## 修复指南
1. 如果析构函数中调用的函数可能抛异常，用 try-catch 包裹并吞下异常。
2. 将可能失败的操作移到显式的 `close()`/`cleanup()`/`shutdown()` 方法中，让调用方可以主动处理错误。
3. 析构函数中仅做保证不失败的清理工作。
4. 在析构函数上显式标注 `noexcept`，使意图明确。
5. 捕获的异常至少应记录日志，便于排查问题。

## 审查清单
- [ ] 所有析构函数中没有未捕获的异常路径
- [ ] 析构函数显式或隐式为 `noexcept`
- [ ] 可能在析构中失败的操作已封装在独立的 cleanup 方法中
- [ ] 析构中捕获的异常有适当的日志记录
- [ ] 无析构函数直接调用 `throw`

## 关联页面
- [[cpp-noexcept-spec]] — noexcept 规范的正确使用
- [[cpp-no-throw-spec]] — 禁止废弃的 throw() 异常规范
- [[cpp-exception-not-for-flow]] — 异常不应用于控制流
