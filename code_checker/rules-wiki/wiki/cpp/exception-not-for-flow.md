---
domain: cpp
rule_id: cpp-exception-not-for-flow
title: 异常不用于控制流
priority: main
source_file: rules/C++代码规范.md
source_section: "§4.1 异常使用规范"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-exception-throw-by-value]]
  - [[cpp-exception-inherit-std]]
  - [[cpp-no-throw-dtor]]
---

# 异常不用于控制流

## 规则条款
异常仅用于表示真正无法在本地处理的异常情况（如资源耗尽、无效状态、前置条件违反等）。禁止使用异常机制实现正常的程序控制流，也禁止使用异常替代条件判断或返回值。

## 正确示例
```cpp
#include <stdexcept>
#include <fstream>
#include <string>

// 异常用于真正的异常情况：文件无法打开
std::string readConfig(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open config file: " + path);
    }
    std::string content;
    // ... 读取内容 ...
    return content;
}

// 正常控制流使用返回值或条件判断
std::optional<int> parseInt(const std::string& s) {
    try {
        return std::stoi(s);
    } catch (const std::invalid_argument&) {
        return std::nullopt;  // 用 optional 表示转换失败
    }
}

// 循环终止使用条件，不用异常
void processItems(const std::vector<int>& items) {
    for (const auto& item : items) {
        if (item < 0) {
            continue;  // 跳过，不抛异常
        }
        doWork(item);
    }
}
```

## 错误示例
```cpp
// 用异常实现正常的查找逻辑 — 反模式
int findValue(const std::vector<int>& vec, int target) {
    try {
        for (size_t i = 0; i < vec.size(); ++i) {
            if (vec[i] == target) {
                throw i;  // 错误：用异常返回索引
            }
        }
        throw std::runtime_error("not found");  // 错误：找不到不是异常
    } catch (size_t index) {
        return static_cast<int>(index);
    }
}

// 用异常控制循环 — 反模式
void processQueue(std::queue<Task>& tasks) {
    try {
        while (true) {
            if (tasks.empty()) {
                throw 0;  // 错误：用异常退出循环
            }
            auto task = tasks.front();
            tasks.pop();
            task.run();
        }
    } catch (int) {
        // "正常" 退出
    }
}
```

## 检查方法
LLM 辅助检查（非确定性）：

1. 扫描 `throw` 语句的上下文，判断是否用于正常的业务逻辑分支。
2. 识别异常被捕获后继续正常执行的模式（`try { ... throw ... } catch { /* 继续正常流程 */ }`）。
3. 检查是否存在用异常替代 `break`、`continue`、`return` 的模式。
4. 检查 `catch` 块是否在同一函数内且紧跟 `throw`，暗示异常用于函数内部跳转。

## 修复指南
1. 用 `std::optional<T>` 替代抛出"未找到"异常。
2. 用 `std::expected<T, E>`（C++23）或 `std::variant<T, Error>` 替代将错误信息编码到异常中。
3. 用 `break`、`continue`、`return` 替代用异常控制循环和分支。
4. 用错误码返回（`std::error_code`）替代常规可预见的失败情况。
5. 保留异常仅用于：构造函数失败、前置条件违反、资源不可用、不可恢复的运行时错误。

## 审查清单
- [ ] 所有 `throw` 语句表示真正的异常情况
- [ ] 没有用异常实现查找/循环/分支逻辑
- [ ] 没有同一函数内 try-throw-catch 的 self-contained 异常使用
- [ ] 可预见的失败用 `optional`、`expected` 或错误码表示
- [ ] 异常的消耗路径与正常路径明确分离

## 关联页面
- [[cpp-exception-throw-by-value]] — 异常的抛出与捕获规范
- [[cpp-exception-inherit-std]] — 自定义异常继承自 std::exception
- [[cpp-no-throw-dtor]] — 析构函数禁止抛异常
