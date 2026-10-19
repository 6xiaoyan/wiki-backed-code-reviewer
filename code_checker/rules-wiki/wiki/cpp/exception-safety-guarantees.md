---
domain: cpp
rule_id: cpp-exception-safety-guarantees
title: 异常安全保证等级
priority: main
source_file: rules/C++代码规范.md
source_section: "§4.2 异常安全"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-exception-prefer-strong]]
  - [[cpp-exception-raii-safety]]
---

# 异常安全保证等级

## 规则条款
函数应提供以下三种异常安全保证之一：
1. **不抛保证（nothrow）**：函数绝不抛出异常，通常通过 `noexcept` 声明。
2. **强异常安全保证**：操作失败时状态完全回滚，不影响程序状态。类似于事务的原子性——要么全部成功，要么全部不变。
3. **基本异常安全保证**：操作失败时程序处于有效状态，无资源泄漏。对象可能被部分修改，但仍是可析构的合法状态。

函数必须提供上述保证之一；完全不考虑异常安全的代码（无保证）是不被允许的。

## 正确示例
```cpp
// 不抛保证：使用 noexcept 声明
void swapData(Data& other) noexcept {
    buffer.swap(other.buffer);
    std::swap(size, other.size);
}

// 强异常安全保证：先操作临时副本，再通过不抛的 swap 提交
std::vector<int>& operator=(const std::vector<int>& other) {
    if (this != &other) {
        auto temp = other;       // 可能抛异常，但 this 未受影响
        data.swap(temp.data);    // 不抛的 swap
    }
    return *this;
}

// 基本异常安全保证：RAII 确保资源释放
void processFile(const std::string& path) {
    FileHandle file(path);          // RAII 管理句柄
    auto config = parseConfig();    // 可能抛异常
    file.write(config);             // 可能抛异常，但 file 会被正确关闭
}
```

## 错误示例
```cpp
// 无异常安全保证：抛异常时资源泄漏
void badProcessFile(const char* path) {
    FILE* f = fopen(path, "r");     // 手动管理资源
    auto config = parseConfig();    // 抛异常 → f 永远不会被 fclose
    processWith(f, config);
    fclose(f);
}

// 无异常安全保证：抛异常时对象处于损坏状态
void badAssign(const std::vector<int>& other) {
    clear();                        // 先清空 this
    for (auto& item : other) {
        append(item);               // 如果中途抛异常，this 半空且无法恢复
    }
}
```

## 检查方法
1. 对每个公开函数，确认其文档或注释中是否声明了异常安全保证等级。
2. 检查 `noexcept` 声明与函数实际行为是否一致——声明了 `noexcept` 但内部可能抛异常的函数为违规。
3. 审查可能抛异常的操作（内存分配、IO、容器操作）前后的状态管理：如果异常发生在部分修改之后、是否能安全回滚或至少不泄漏。
4. 通过 LLM 审查函数体逻辑，分析异常路径上的资源管理和状态一致性。

## 修复指南
- **从不抛保证开始**：优先将简单操作标记为 `noexcept`（如 swap、移动构造、析构函数）。
- **复制-交换（copy-and-swap）惯用法**：对赋值运算符等修改操作，先在栈上构造完整副本，再用不抛的 swap 替换内部数据。
- **分段操作**：将对多个对象的修改拆分为独立的步骤，确保每步失败只影响本步，并在 catch 块中撤销已完成步骤。
- **最低限度**：如果无法实现强保证，至少用 RAII 确保基本保证——资源在异常发生时也能被正确释放。

## 审查清单
- [ ] 每个 `noexcept` 函数内部是否确实不会抛出异常？
- [ ] 修改类的公开函数是否提供强保证或基本保证？
- [ ] 析构函数是否隐式或显式声明为 `noexcept`（C++ 默认行为）？
- [ ] 资源获取是否使用 RAII 包装？
- [ ] 是否存在 `new` 后可能抛异常导致裸指针泄漏的路径？

## 关联页面
- [[cpp-exception-prefer-strong]] — 异常安全保证等级的选择优先级
- [[cpp-exception-raii-safety]] — 使用 RAII 实现异常安全
