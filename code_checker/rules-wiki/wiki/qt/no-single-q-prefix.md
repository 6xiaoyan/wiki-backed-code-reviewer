---
domain: qt
rule_id: qt-no-single-q-prefix
title: 自建类禁止以单个 Q 开头
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.2 类命名
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-class-semantic-noun]]
  - [[qt-ui-class-parent-suffix]]
---

# 自建类禁止以单个 Q 开头
## 规则条款

与 Qt 无关的自建类禁止以单个大写字母 "Q" 开头。仅当类的设计意图是封装为 Qt 风格模块（提供与 Qt 框架一致的 API 风格）时，才允许使用 "Q" 前缀。
## 正确示例

```cpp
// 自建业务类，不使用 Q 前缀
class DataProcessor : public QObject { };
class NetworkManager : public QObject { };
class UserSession : public QObject { };
class AppConfig : public QObject { };

// 与 Qt 模块的工具类，不使用 Q 前缀
class StringHelper { };
class FileUtils { };
class MathToolkit { };

// 封装为 Qt 风格模块 —— 允许使用 Q 前缀
// 该类提供与 Qt 框架风格一致的 API，作为 Qt 生态的扩展
class QCustomPlot : public QWidget { };
class QSerialBus : public QObject { };
class QFtpClient : public QObject { };
```

## 错误示例

```cpp
// 错误：普通业务类以 Q 开头class QUserManager : public QObject { };      // 应为 UserManager
class QDataCache : public QObject { };        // 应为 DataCache
class QLogger : public QObject { };           // 应为 Logger
class QConfigLoader : public QObject { };     // 应为 ConfigLoader

// 错误：工具类以 Q 开头class QFileHelper { };                        // 应为 FileHelper
class QStringUtils { };                       // 应为 StringUtils

// 错误：与 Qt 内置类名冲突或引起混淆class QWidgetEx : public QWidget { };         // 疑似 Qt 官方扩展，应为 CustomWidget
class QObjectBase : public QObject { };       // 疑似 Qt 基础类，应为 BaseObject
```

## 检查方法
使用正则表达式检测：

1. 提取项目自定义头文件中所有 `class` 定义。2. 检查类名是否匹配 `^Q[A-Z]`（以大写 Q 开头且第二个字符为大写字母）。3. 排除标准 Qt 头文件（`<Q...>`）中的类定义。4. 排除 `moc_` 生成文件中的代码。5. 匹配到的类名需人工审查：   - 如果是封装为 Qt 风格模块的库类，允许豁免。   - 如果是普通业务代码，标记为违规。
正则示例：`class\s+Q[A-Z]\w+`（在非 Qt 系统头文件中匹配）。
## 修复指南

1. 去掉类名前缀的 `Q`：   - `QUserManager` → `UserManager`
   - `QDataCache` → `DataCache`
2. 如果去掉 Q 后类名变得不够明确，适当调整命名：   - `QWidgetEx` → `EnhancedWidget` 或 `CustomWidget`
3. 同步更新文件名（遵循 Q-25 规则）。4. 更新项目内所有对该类的引用。5. 如果是真正的 Qt 风格模块扩展，添加文件级注释说明其使用 Q 前缀的合理性。
## 审查清单

- [ ] 无普通业务类以大写 Q 开头- [ ] 无工具类/辅助类以大写 Q 开头- [ ] 使用 Q 前缀的类确实封装为 Qt 风格模块
- [ ] 类名不与现有 Qt 类名冲突
- [ ] 相关引用和文件名已同步更新
## 关联页面

- [[qt-class-semantic-noun]] —— 类名需为名词短语- [[qt-ui-class-parent-suffix]] —— 界面类最后一个单词体现父类属性