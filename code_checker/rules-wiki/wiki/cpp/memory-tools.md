---
domain: cpp
rule_id: cpp-memory-tools
title: 内存检测工具
priority: main
source_file: rules/C++代码规范.md
source_section: "§3.2 内存泄漏预防"
status: active
check_method: regex
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-bare-new-delete]]
  - [[cpp-use-containers]]
---

# 内存检测工具

## 规则条款
在开发过程中应定期使用内存检测工具对代码进行运行时分析，以发现内存泄漏、越界访问、使用已释放内存（use-after-free）、双重释放等内存错误。推荐工具包括 Valgrind（Linux/macOS）和 AddressSanitizer（跨平台，集成于 GCC/Clang/MSVC）。

## 正确示例
```bash
# AddressSanitizer — 编译时启用
g++ -fsanitize=address -g -O1 main.cpp -o app
./app

# Valgrind — 对已编译程序运行
valgrind --leak-check=full --show-leak-kinds=all ./app

# CMake 配置 AddressSanitizer
# CMakeLists.txt:
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -fsanitize=address")
```

```cpp
// 测试代码中故意引入问题的示例 — 工具应能捕获
void problematicCode() {
    int* p = new int(42);  // 泄漏：没有 delete
    // AddressSanitizer 或 Valgrind 会在退出时报告
}
```

## 错误示例
```bash
# 从不运行内存检测 — 泄漏和越界可能留到生产环境
g++ main.cpp -o app
./app  # 直接运行，没有工具包裹
```

## 检查方法
此规则为咨询性检查（advisory only），无法通过静态正则匹配判定：

1. 检查 CI/CD 配置中是否包含内存检测步骤（如 `.github/workflows/*.yml` 中是否有 `-fsanitize=address` 或 `valgrind`）。
2. 检查 CMakeLists.txt 或构建脚本中是否定义了带 sanitizer 的构建配置。
3. 审查时询问开发者是否在本地运行过内存检测。
4. 检查是否有定期运行的自动化内存检测流水线。

## 修复指南
1. 在 Debug 构建配置中添加 `-fsanitize=address -g -O1` 编译选项。
2. 建立 CI 流水线步骤，在 AddressSanitizer 下运行测试套件。
3. 对于 Linux 项目，添加 Valgrind 运行脚本到 `scripts/` 目录。
4. 将内存检测结果纳入代码审查前检查清单。
5. 对检测到的内存问题建立缺陷跟踪并设定修复优先级。

## 审查清单
- [ ] 项目构建配置包含 AddressSanitizer 或 Valgrind 选项
- [ ] CI 流水线包含内存检测步骤
- [ ] 开发者了解如何使用内存检测工具
- [ ] 最近一次内存检测结果无新增问题
- [ ] 历史内存问题已修复或记录在案

## 关联页面
- [[cpp-no-bare-new-delete]] — 从编码层面消除裸指针分配
- [[cpp-use-containers]] — 优先使用容器而非手动管理内存
