---
domain: qt
rule_id: qt-class-semantic-noun
title: 类名需为意思明确的名词短语
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§3.2 类命名"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-ui-class-parent-suffix]]
  - [[qt-no-single-q-prefix]]
  - [[qt-file-naming]]
---

# 类名需为意思明确的名词短语

## 规则条款

类名必须是意思明确的名词短语，可以使用缩写。禁止以动词、形容词结尾的类名（接口/抽象类以 `-able`、`-Interface` 结尾的约定除外）。
## 正确示例

```cpp
// 名词短语，意思明确
class FileManager : public QObject { };
class NetworkConfiguration : public QObject { };
class DataSerializer : public QObject { };
class ImageCache : public QObject { };

// 使用常见缩写，语义清晰
class HttpRequest : public QObject { };
class XmlParser : public QObject { };
class UIManager : public QObject { };
class SQLDatabase : public QObject { };

// Qt 风格界面类
class LoginDialog : public QDialog { };
class UserTableWidget : public QTableWidget { };
class SettingsPanel : public QWidget { };

// 设计模式相关命名
class DataObserver : public QObject { };
class EventDispatcher : public QObject { };
```

## 错误示例

```cpp
// 错误：动词结尾，类名应表示"是什么"而非"做什么"
class ParseData : public QObject { };      // 应为 DataParser
class HandleEvent : public QObject { };    // 应为 EventHandler
class ConnectServer : public QObject { };  // 应为 ServerConnector
class ValidateInput : public QObject { };  // 应为 InputValidator

// 错误：形容词结尾
class Configurable : public QObject { };   // 应为 Configuration 或 ConfigManager
class Readable : public QObject { };       // 应为 DataReader 或 ReadableMixin
class Visible : public QObject { };        // 应为 VisibilityController

// 错误：语义不明，含义模糊
class Data : public QObject { };           // 太泛，应为 UserData / SensorData
class Manager : public QObject { };        // 管什么？应为 ProjectManager
class Handler : public QObject { };        // 处理什么？应为 SignalHandler
class Info : public QObject { };           // 什么信息？应为 DeviceInfo
class Util : public QObject { };           // 什么工具？应为 StringUtil
```

## 检查方法
此规则依赖 LLM 语义分析，无法用纯正则可靠检测：

1. 提取所有类定义中的类名。2. 用 LLM 判断该类名是否为名词短语且语义明确。3. 检查要点：
   - 核心词是否为名词（非动词、非形容词）。   - 名称是否足以表达类的职责和用途。   - 缩写是否是领域内公认的（如 HTTP、XML、SQL、UI）。4. 标记以常见动词（如 parse、handle、connect、validate、execute、process 等）结尾且不作为名词使用的类名。5. 标记过于泛化、语义不明的类名（如 Data、Info、Util、Manager 且无修饰语）。
例外：以 `-able` 结尾的接口/特质类（如 `Serializable`）、以 `Interface` 结尾的接口、以及 `*Factory`、`*Visitor` 等设计模式约定命名不受此规则限制。
## 修复指南

1. 确认类的核心职责：这个类"是什么"而非"做什么"。2. 用名词或名词短语重新命名：   - `ParseData` → `DataParser`
   - `HandleEvent` → `EventHandler`
   - `ConnectServer` → `ServerConnector`
3. 过于泛化的名称添加修饰语使其明确：   - `Data` → `SensorData` 或 `UserData`
   - `Manager` → `ProjectManager` 或 `TaskManager`
4. 重命名类后同步更新文件名（遵循 Q-25 规则）。5. 更新所有引用该类的代码和文档。
## 审查清单

- [ ] 类名核心词是名词（非动词、非形容词）
- [ ] 类名足以表达类的职责范围
- [ ] 缩写是领域内公认的常用缩写
- [ ] 与 Qt 原生类的命名不与 Qt 内置类名冲突
- [ ] 文件名已随类名同步更新
## 关联页面

- [[qt-ui-class-parent-suffix]]：界面类最后一个单词体现父类属性
- [[qt-no-single-q-prefix]]：自建类禁止以单个 Q 开头
- [[qt-file-naming]]：文件名使用类名全小写
