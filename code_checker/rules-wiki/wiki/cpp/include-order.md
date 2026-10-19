---
domain: cpp
rule_id: cpp-include-order
title: "#include 包含顺序"
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.2 头文件规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: [qt-include-order]
overrides: []
related_pages:
  - [[cpp-header-guards]]
  - [[cpp-forward-declarations]]
  - [[cpp-templates-in-headers]]
  - [[cpp-typing-conventions]]
  - [[qt-include-order]]
---

# #include 包含顺序

## 规则条款

`#include` 指令必须按照以下顺序分组，各组之间用空行分隔：
1. 关联头文件（当前 `.cpp` 对应的 `.h`，若有）
2. C 标准库头文件
3. C++ 标准库头文件
4. 第三方库头文件
5. 项目内部头文件
每组内部按字母顺序排列。这样做的目的是避免隐藏的依赖问题，确保每个头文件都能独立编译。
**跨域冲突**：本规则与 Qt 的 `qt-include-order` 存在冲突（Qt 将自动生成文件 `ui_*.h` 单独放在最前，分组顺序不同）。公司规范未对此做出硬性规定，属于项目级裁决冲突。在同时遵循 C++ 和 Qt 规范的项目中，需明确选择一种顺序。详情见 [[qt-include-order]]。
## 正确示例

```cpp
// associated header (this file's own header)
#include "network/base_connection.h"

// C standard library headers
#include <cstdint>
#include <cstring>

// C++ standard library headers
#include <memory>
#include <string>
#include <vector>

// third-party library headers
#include <boost/asio.hpp>
#include <openssl/ssl.h>

// project headers
#include "network/connection_pool.h"
#include "network/socket_utils.h"
#include "utils/string_helper.h"
```

## 错误示例

```cpp
// 项目头文件在系统头文件之前，顺序错误
#include "network/base_connection.h"

// 系统头文件与项目头文件混在一起
#include <string>
#include "utils/string_helper.h"
#include <vector>
#include "network/socket_utils.h"
#include <memory>
```

## 检查方法
1. 收集文件中所有 `#include` 行，按它们在源文件中出现的顺序排列。
2. 识别每一行所属的分组：C 标准库（`<c*.h>`、`<*.h>` C 风格）、C++ 标准库（`<string>`、`<vector>`、`<memory>` 等，无 `.h` 后缀）、第三方库（不在标准库中且不以项目前缀开头的 `<>` 包裹路径）、项目头文件（`""` 包裹的路径）。
3. 验证分组顺序：关联头文件（若有）在最前，然后是 C 标准库、C++ 标准库、第三方库、项目头文件。任何跨组错序视为违规。
4. 正则辅助模式（用于分拣而非定义顺序）：
   - 标准 C/C++ 头：`#include\s+<(c?(assert|ctype|errno|float|limits|locale|math|setjmp|signal|stdarg|stddef|stdio|stdlib|string|time|wchar|wctype|algorithm|array|atomic|bitset|chrono|codecvt|complex|condition_variable|deque|exception|forward_list|fstream|functional|future|initializer_list|iomanip|ios|iosfwd|iostream|istream|iterator|list|map|memory|mutex|new|numeric|ostream|queue|random|ratio|regex|scoped_allocator|set|shared_mutex|sstream|stack|stdexcept|streambuf|string|strstream|system_error|thread|tuple|type_traits|typeindex|typeinfo|unordered_map|unordered_set|utility|valarray|vector))>`
   - 第三方库头：`#include\s+<[^">]+>`
   - 项目头：`#include\s+"[^"]+"`
5. 用上述模式给每个 `#include` 打标签后，验证标签序列是否符合 C→C++→第三方→项目的单调非递减顺序。
## 修复指南

1. 将所有 `#include` 行按规则分组重新排列。
2. 使用 IDE 的 "Sort Lines" 功能或 `clang-format`（设置 `SortIncludes: true`）自动排序。
3. 确保每组之间保留一个空行。
4. 重新编译验证：如果排序后出现编译错误，说明存在循环依赖或缺失 `#include`，需在对应头文件中补上缺失的依赖，而不是将 include 放回错误位置。
## 审查清单

- [ ] 是否存在关联头文件且位于最前
- [ ] C 标准库头文件是否成组且在 C++ 标准库之前
- [ ] 第三方库头文件是否成组且在项目头文件之前
- [ ] 各组之间是否有空行分隔
- [ ] 每组内部是否按字母排序
## 关联页面

- [[cpp-header-guards]]
- [[cpp-forward-declarations]]
- [[cpp-templates-in-headers]]
- [[cpp-inline-functions]]
- [[cpp-typing-conventions]]
- [[qt-include-order]] — Qt 的 include 顺序变体（存在冲突）
