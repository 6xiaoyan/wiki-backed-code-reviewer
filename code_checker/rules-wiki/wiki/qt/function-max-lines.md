---
domain: qt
rule_id: qt-function-max-lines
title: 单个函数超过 2000 行必须拆分
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§4.1 代码行数限制"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-class-max-lines]]
  - [[qt-member-declaration-order]]
---

# 单个函数超过 2000 行必须拆分
## 规则条款

单个函数（包括成员函数、自由函数、lambda 表达式）的代码量超过 2000 行时，必须拆分为多个更小的函数。此规则为强制性要求，与 Q-37（类 1000 行评估拆分）不同，该规则没有"评估"余地。
## 正确示例

```cpp
// 函数短小精悍，职责单一
bool DocumentParser::parseSection(const QByteArray &data, Section &outSection)
{
    if (data.isEmpty()) {
        return false;
    }

    if (!validateHeader(data)) {
        setError(ErrorCode::InvalidHeader);
        return false;
    }

    if (!parseBody(data, outSection)) {
        setError(ErrorCode::ParseError);
        return false;
    }

    if (!validateChecksum(data, outSection)) {
        setError(ErrorCode::ChecksumMismatch);
        return false;
    }

    return true;
}

// 原始 2500 行的函数拆分为多个子函数
void DataPipeline::process(const InputData &input)
{
    auto raw = fetchRawData(input);        // ~300 行
    auto cleaned = cleanData(raw);          // ~400 行
    auto transformed = transformData(cleaned); // ~500 行
    auto validated = validateResult(transformed); // ~350 行
    writeOutput(validated);                 // ~300 行
    notifyCompletion();                     // ~150 行
}
// 总计：2000 行分散在 6 个函数中，每个不超过 500 行
```

## 错误示例

```cpp
// 错误：单个函数 2500+ 行，必须拆分
void MainWindow::handleAllUserActions(ActionType action)
{
    // 500 行文件操作代码
    // ...
    // 400 行数据库操作代码
    // ...
    // 300 行网络请求代码
    // ...
    // 200 行 UI 更新代码
    // ...
    // 350 行数据验证代码
    // ...
    // 250 行日志记录代码
    // ...
    // 200 行错误处理代码
    // ...
    // 300 行导出功能代码
    // ...
    // 总计 2500+ 行，严重违规
}
```

```cpp
// 另一个反例：超长 switch-case 导致函数膨胀
void EventDispatcher::dispatch(int eventCode, const QVariant &payload)
{
    switch (eventCode) {
    case EVENT_FILE_OPEN:
        // 300 行文件打开逻辑
        break;
    case EVENT_FILE_SAVE:
        // 350 行文件保存逻辑
        break;
    case EVENT_NETWORK_REQUEST:
        // 400 行网络请求逻辑
        break;
    // ... 15 个 event 分支，每个 100-400 行
    // 总计 3000+ 行
    }
}

// 正确做法：每个 case 委托给独立函数
void EventDispatcher::dispatch(int eventCode, const QVariant &payload)
{
    switch (eventCode) {
    case EVENT_FILE_OPEN:       handleFileOpen(payload); break;
    case EVENT_FILE_SAVE:       handleFileSave(payload); break;
    case EVENT_NETWORK_REQUEST: handleNetworkRequest(payload); break;
    // 每个分支一行，清晰简洁
    }
}
```

## 检查方法
可自动化检测：

1. 遍历所有 `.cpp` 和 `.h` 文件（头文件中的内联函数同样计入）。2. 对每个函数定义，统计从函数签名开头到匹配的 `}` 之间的行数。3. 排除纯空行和纯注释行（可选，保守检测可不排除）。4. 如果函数总行数 > 2000，标记为违规。
统计逻辑：- 定位函数定义的起始行（正则匹配函数签名模式）。- 根据大括号配对找到函数结束行。- 计算行数差值。
常用工具辅助：`cloc`、`tokei`、IDE 代码度量插件。
## 修复指南

1. 分析超长函数的逻辑块，识别可独立的子功能。2. 将每个子功能抽取为独立的私有函数：   - 每个子函数控制在 200 行以内。   - 子函数命名清晰，体现其职责（遵循 Q-29a 规则）。3. 在原始函数中按顺序调用子函数。4. 若原始函数为大型 `switch-case`，考虑使用策略模式或命令模式。5. 确保每个子函数有清晰的输入参数和返回值。6. 抽取后运行完整测试套件确保行为不变。
## 审查清单

- [ ] 已扫描所有函数的行数
- [ ] 无超过 2000 行的函数
- [ ] 拆分的子函数命名清晰、职责单一
- [ ] 拆分后代码更易理解和维护
- [ ] 所有测试通过，行为无变化

## 关联页面

- [[qt-class-max-lines]]：单个类超过 1000 行时评估拆分
- [[qt-member-declaration-order]]：类成员声明顺序