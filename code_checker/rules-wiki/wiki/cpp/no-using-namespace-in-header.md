---
domain: cpp
rule_id: cpp-no-using-namespace-in-header
title: 头文件禁止 using namespace
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
  - [[cpp-no-macro-constants]]
  - [[cpp-no-global-variables]]
---

# 头文件禁止 using namespace

## 规则条款
禁止在头文件（`.h`、`.hpp`、`.hxx`）的全局作用域中使用 `using namespace` 指令。`using namespace` 会将整个命名空间的所有名称污染到当前作用域，头文件被包含后，这种污染会级联传播到所有包含该头文件的翻译单元，导致命名冲突和不可预测的编译错误。

## 正确示例
```cpp
// mymodule.h — 头文件
#pragma once

#include <string>
#include <vector>

namespace MyModule {

// 不使用 using namespace，完全限定名称
class DataProcessor {
public:
    void process(const std::vector<std::string>& items);
    std::string getResult() const;

private:
    std::vector<std::string> m_items;
};

// 允许在头文件内部、受限作用域中使用 using 声明（非指令）
namespace Detail {
    using StringList = std::vector<std::string>;  // 类型别名，允许
}

} // namespace MyModule
```

```cpp
// mymodule.cpp — 源文件中可以使用
#include "mymodule.h"

using namespace MyModule;      // 源文件允许
using std::string;              // using 声明，允许
using std::vector;              // using 声明，允许

// 实现代码
void DataProcessor::process(const std::vector<std::string>& items) {
    m_items = items;
}
```

## 错误示例
```cpp
// mymodule.h — 头文件
#pragma once

#include <string>
#include <vector>

using namespace std;  // 错误：污染所有包含此头文件的翻译单元

namespace MyModule {

using namespace std;  // 错误：即使在命名空间内，仍然污染 MyModule

class DataProcessor {
public:
    void process(const vector<string>& items);  // 依赖了 using namespace
    string getResult() const;
};

} // namespace MyModule
```

## 检查方法
1. 正则检测：在头文件（`*.h`、`*.hpp`、`*.hxx`）中搜索 `using namespace`
   - 模式：`using\s+namespace\s+\w+`
2. 标记所有在头文件中出现的 `using namespace` 为违规
3. 源文件（`.cpp`、`.cc`、`.cxx`）中的 `using namespace` 不在此规则范围内
4. 注意：`using` 类型别名声明（`using X = Y`）和 `using` 成员声明不受此规则限制

## 修复指南
1. 删除头文件中的 `using namespace` 指令
2. 在头文件的所有函数签名和类型声明中使用完全限定名
3. 过长的命名空间可用命名空间别名：`namespace fs = std::filesystem;`（在头文件的受限作用域内）
4. 在源文件（`.cpp`）中自由使用 `using namespace`
5. 如需缩短类型名，在头文件命名空间内使用类型别名：
   ```cpp
   namespace MyModule {
       using StringVector = std::vector<std::string>;  // OK
   }
   ```

## 审查清单
- [ ] 头文件中不存在 `using namespace` 指令
- [ ] 头文件类型声明使用完全限定名
- [ ] 类型别名未引入命名空间污染
- [ ] 源文件中的 using namespace 使用合理

## 关联页面
- [[cpp-no-macro-constants]] — 禁止宏定义常量/函数
- [[cpp-no-global-variables]] — 禁止全局变量
