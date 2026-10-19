---
domain: cpp
rule_id: cpp-no-user-code-under-lock
title: 持锁不调用户代码
priority: main
source_file: rules/C++代码规范.md
source_section: "§6.2 原子操作与锁"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-lock-guard]]
  - [[cpp-scoped-lock]]
  - [[cpp-avoid-datarace-deadlock]]
---

# 持锁不调用户代码

## 规则条款
避免在持有锁时调用用户代码（回调、虚函数、外部传入的函数对象）或执行耗时操作（I/O、网络请求、磁盘操作）。持锁调用外部代码可能导致死锁（外部代码尝试获取同一把锁）、性能瓶颈或不可预测的行为。

## 正确示例
```cpp
class EventDispatcher {
public:
    // 先收集数据（持锁），再分发事件（不持锁）
    void dispatchEvents() {
        std::vector<Handler> handlersToCall;

        {
            std::lock_guard<std::mutex> lock(m_mutex);
            handlersToCall = m_handlers;  // 复制出来
        }  // 锁在此释放

        // 在不持锁的情况下调用用户回调
        for (const auto& handler : handlersToCall) {
            handler();  // 安全：用户代码可能获取自己的锁
        }
    }

    void registerHandler(Handler h) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_handlers.push_back(std::move(h));
    }

private:
    std::mutex m_mutex;
    std::vector<Handler> m_handlers;
};
```

## 错误示例
```cpp
class EventDispatcher {
public:
    // 持锁调用用户回调 → 死锁风险
    void dispatchEventsBad() {
        std::lock_guard<std::mutex> lock(m_mutex);
        for (const auto& handler : m_handlers) {
            handler();  // 危险：handler 可能尝试调用 registerHandler()
        }
    }

    // 持锁执行虚拟函数
    virtual void onDataChanged() = 0;

    void updateData(int newValue) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_data = newValue;
        onDataChanged();  // 危险：派生类的实现可能获取其他锁
    }

    // 持锁执行文件 I/O
    void saveState() {
        std::lock_guard<std::mutex> lock(m_mutex);
        std::ofstream file("state.dat");  // 耗时操作在锁内
        file << m_data;
    }

private:
    std::mutex m_mutex;
    int m_data = 0;
    std::vector<Handler> m_handlers;
};
```

## 检查方法
1. LLM 扫描锁作用域内的代码
2. 识别锁作用域内的以下模式：
   - 虚函数调用
   - 回调/函数对象调用
   - `std::function` 调用
   - 文件 I/O、网络 I/O
   - 系统调用（可能阻塞）
3. 检查是否存在跨模块的函数调用（可能获取未知的锁）

## 修复指南
1. 将需要在持锁期间调用的操作改为数据收集 + 释放锁后处理
2. 对于回调场景：将回调列表复制到栈上，释放锁后再逐个调用
3. 对于虚函数：先收集所需数据，然后在非虚辅助函数中处理
4. 对于 I/O：在锁外进行读写，锁定仅保护内存数据
5. 如确需在锁内调用外部代码，需在文档中明确标注约束条件

## 审查清单
- [ ] 锁作用域内是否存在虚函数调用
- [ ] 锁作用域内是否存在 lambda 或 std::function 调用
- [ ] 锁作用域内是否存在 I/O 操作
- [ ] 锁作用域内是否存在跨模块调用
- [ ] 是否存在"复制-释放-处理"的替代方案

## 关联页面
- [[cpp-lock-guard]] — lock_guard 优先
- [[cpp-scoped-lock]] — scoped_lock 多锁获取
- [[cpp-avoid-datarace-deadlock]] — 避免数据竞争与死锁
