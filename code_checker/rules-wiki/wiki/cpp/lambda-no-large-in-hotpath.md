---
domain: cpp
rule_id: cpp-lambda-no-large-in-hotpath
title: Lambda 性能考量
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.3 Lambda"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-lambda-over-bind]]
  - [[cpp-lambda-explicit-capture]]
  - [[cpp-lambda-small-scope]]
  - [[cpp-lambda-explicit-return]]
---

# Lambda 性能考量

## 规则条款
避免在频繁调用的代码路径（热路径）中使用大型 lambda。大型 lambda 在热路径中可能导致以下问题：
- **内联失败**：编译器可能因 lambda 体过大而放弃内联，丧失 lambda 零开销抽象的初衷
- **代码膨胀**：每个 lambda 生成一个唯一闭包类型，大型 lambda 会显著增加二进制体积
- **缓存友好性受损**：大型函数体不易放入指令缓存，热路径中反复调用可能导致 I-cache miss

对于热路径中的复杂逻辑，应提取为具名函数并考虑手动优化或通过 PGO（Profile-Guided Optimization）指导编译器。

## 正确示例
```cpp
#include <vector>
#include <algorithm>
#include <numeric>

// 热路径中的 lambda：保持简洁，编译器容易内联
void processHotPath(std::vector<int>& data) {
    // 简短的 lambda，内联无阻碍
    std::transform(data.begin(), data.end(), data.begin(),
                   [](int x) { return x * 2 + 1; });

    // 轻量 lambda 适合热路径
    int threshold = computeThreshold();
    auto it = std::remove_if(data.begin(), data.end(),
                             [threshold](int x) { return x < threshold; });
    data.erase(it, data.end());
}

// 复杂的转换逻辑：提取为具名函数
int complexTransform(int input) {
    int result = input;
    // 假设这里有多步骤的数据处理逻辑（20+ 行）
    // ... 复杂计算 ...
    return result;
}

// 热路径中调用具名函数，编译器可针对性地优化
void optimizedHotPath(std::vector<int>& data) {
    std::transform(data.begin(), data.end(), data.begin(), complexTransform);
}

// lambda 中大量捕获也可能影响性能
// 推荐：初始化捕获减少闭包大小
void captureOptimization() {
    std::vector<double> largeVector(10000);
    // 不佳：引用捕获大型对象，可能阻碍别名分析
    // auto bad = [&largeVector](int i) { return largeVector[i]; };

    // 更优：提取关键数据
    double* rawData = largeVector.data();
    auto good = [rawData](int i) { return rawData[i]; };
}
```

## 错误示例
```cpp
#include <vector>
#include <string>
#include <map>
#include <algorithm>

// 热路径中嵌入大型 lambda——违规
void processFramesHotPath(std::vector<Frame>& frames) {
    std::for_each(frames.begin(), frames.end(),
                  [](Frame& f) {  // 热路径中包含 50+ 行的 lambda
                      // 大量图像处理逻辑...
                      if (f.type == FrameType::KeyFrame) {
                          // ... 10 行处理 ...
                      } else {
                          // ... 10 行处理 ...
                      }
                      // 纹理采样
                      for (int y = 0; y < f.height; ++y) {
                          for (int x = 0; x < f.width; ++x) {
                              // 嵌套循环中的像素操作...
                              auto pixel = f.getPixel(x, y);
                              // ... 更多操作 ...
                          }
                      }
                      // 后处理
                      f.applyFilter();
                      f.computeHistogram();
                      f.encode();
                  });
}

// 热路径中捕获大量数据，闭包对象过大
void gameUpdateLoop(std::vector<Entity>& entities,
                    const GameState& state,
                    const PhysicsWorld& world) {
    // 违规：lambda 捕获整个 GameState 和 PhysicsWorld，闭包尺寸巨大
    // 且 lambda 体量也较大
    std::for_each(entities.begin(), entities.end(),
                  [&state, &world](Entity& e) {
                      // 30 行物理和 AI 逻辑...
                      auto pos = e.getPosition();
                      auto collisions = world.checkCollisions(pos, e.getBounds());
                      for (auto& col : collisions) {
                          e.applyForce(col.normal * col.impulse);
                      }
                      // ... 更多 AI 决策逻辑 ...
                      e.updateAI(state, world);
                  });
}

// 大量唯一 lambda 类型导致代码膨胀
void registerCallbacks(EventBus& bus) {
    // 每个 lambda 生成一个唯一类型，大量注册导致二进制体积增长
    for (int i = 0; i < 1000; ++i) {
        bus.subscribe([i](const Event&) { handleEvent(i); });
    }
    // 更优方案：使用函数对象或模板参数
}
```

## 检查方法
由 LLM 进行分析，重点关注：
1. **体量阈值**：lambda 体超过 20 行时标记警告
2. **上下文分析**：lambda 是否位于已知的热路径函数中（如游戏主循环、渲染循环、网络数据包处理、信号处理等）
3. **闭包大小**：lambda 捕获了大量变量或大型对象
4. **嵌套循环**：lambda 体内包含多层循环或复杂控制流
5. **重复实例化**：模板上下文中大型 lambda 导致多次实例化

## 修复指南
1. **提取函数**：将热路径中的大型 lambda 逻辑提取为独立的具名函数或静态函数
2. **减少捕获**：仅捕获 lambda 实际需要的数据，使用初始化捕获缩小闭包尺寸
3. **考虑函数对象**：对于需要多次复用的可调用对象，考虑手写函数对象以获得更精确的控制
4. **性能剖析**：使用 profiler 验证 lambda 是否真的是瓶颈，避免过早优化
5. **PGO 辅助**：对提取后的函数运行 PGO，让编译器根据实际调用模式优化

## 审查清单
- [ ] 热路径中无体量超过 20 行的 lambda
- [ ] 循环/渲染/网络等性能敏感代码中的 lambda 保持简洁
- [ ] lambda 闭包尺寸适中（捕获变量数量和体积受控）
- [ ] 复杂逻辑已提取为具名函数
- [ ] 大量唯一 lambda 类型不会导致代码膨胀

## 关联页面
- [[cpp-lambda-over-bind]] — Lambda 优先于 std::bind
- [[cpp-lambda-explicit-capture]] — Lambda 显式捕获
- [[cpp-lambda-small-scope]] — Lambda 适用范围
- [[cpp-lambda-explicit-return]] — Lambda 显式返回类型
