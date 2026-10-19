---
domain: cpp
rule_id: cpp-naming-functions
title: 函数/方法命名规范
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.1 命名约定"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
related_pages:
  - [[cpp-naming-classes]]
  - [[cpp-naming-variables]]
  - [[cpp-naming-constants]]
  - [[cpp-naming-private-members]]
  - [[cpp-naming-namespaces]]
---

# 函数/方法命名规范

## 规则条款

函数和方法必须使用**camelCase**（首字母小写，后续每个单词的首字母大写），无空格或符号分隔。命名必须以动词开头，清晰表达函数所执行的操作。

**测试函数例外**：QTest 框架的 `private slots` 方法和 Google Test 的 `TEST`/`TEST_F`/`TEST_P` 宏不受 camelCase 限制。测试函数名允许使用 snake_case 的 `Method_Scenario_Expected` 格式（如 `processData_EmptyInput_ReturnsEmpty`），这是 Google Test 官方推荐和 Qt Test 通用惯例。

按用途分类：

- **获取数据**：使用`get` / `fetch` 开头，如`getUserList`（获取用户列表）、`fetchOrderDetail`（获取订单详情）
- **操作数据**：使用`update` / `delete` / `create` / `add` 等动词开头，如`updatePassword`（更新密码）、`deleteInvalidFile`（删除无效文件）
- **计算/处理**：使用`calculate` / `format` / `process` / `convert` 等动词开头，如`calculateDiscount`（计算折扣）、`formatDateTime`（格式化日期时间）
## 正确示例

```cpp
// 获取数据 — get/fetch 开头
UserList getUserList();
OrderDetail fetchOrderDetail(int orderId);

// 操作数据 — 动词开头，表达动作
void updatePassword(const std::string& newPassword);
bool deleteInvalidFile(const std::string& path);
void createAccount(const AccountInfo& info);

// 计算/处理 — 动词开头，表达处理逻辑
double calculateDiscount(double price, int level);
std::string formatDateTime(const DateTime& dt);
bool validateEmail(const std::string& email);
```

## 错误示例

```cpp
// 错误：PascalCase（应为 camelCase）
void ProcessData();              // 应为 processData
int GetUserList();               // 应为 getUserList

// 错误：snake_case
void process_data();             // 应为 processData
void get_user_list();            // 应为 getUserList

// 错误：全小写无分隔
void processdata();              // 应为 processData

// 错误：名词开头（缺少动词）
void data();                     // 应为 processData 或 loadData
int userList();                  // 应为 getUserList

// 错误：无意义名称
void f1();                       // 应使用有意义名称
void doSomething();              // 应明确具体操作
```

## 检查方法
1. 扫描所有函数/方法声明（含类成员函数、自由函数）
2. **跳过测试函数**：QTest `private slots` 方法、Google Test `TEST`/`TEST_F`/`TEST_P` 宏不检查 camelCase
3. 验证名称首字母是否小写
4. 验证名称是否为动词开头
5. 验证名称中无下划线或连字符（测试函数除外）
6. 验证名称是否有明确含义（非单字符或模糊名称）
7. 正则模式（声明）：`(?:void|int|bool|double|std::\w+|auto|[\w:]+)\s+[a-z][a-zA-Z0-9]*\s*\(`
8. 正则模式（定义，含类限定符）：`(?:void|int|bool|double|std::\w+|auto|[\w:]+)\s+(?:\w+::)?[a-z][a-zA-Z0-9]*\s*\(`

## 修复指南

1. 将 PascalCase 转换为 camelCase：`ProcessData` → `processData`，`GetUserList` → `getUserList`
2. 将 snake_case 转换为 camelCase：`process_data` → `processData`
3. 补充缺失的动词前缀：`data()` → `getData()` 或 `loadData()`
4. 对无意义的名称重新命名以表达函数的具体职责
5. 注意：修改函数声明时需要同步更新所有调用点、声明和定义

## 审查清单

- [ ] 所有普通函数名使用 camelCase（首字母小写）
- [ ] 所有普通方法名使用 camelCase（首字母小写）
- [ ] 测试函数（QTest private slots、GTest TEST 宏）豁免 camelCase，允许 snake_case
- [ ] 所有函数名以动词开头（get/fetch/update/delete/create/calculate 等）
- [ ] 函数名清晰表达了具体操作
- [ ] 无 PascalCase、snake_case 或全小写函数名（测试函数除外）
- [ ] 无单字符或"doSomething" 等模糊名称

## 关联页面

- [[cpp-naming-classes]] — 类命名（PascalCase，注意与函数 camelCase 的区别）
- [[cpp-naming-variables]] — 变量命名（同为 camelCase，但以名词/形容词为主）
- [[cpp-naming-constants]] — 常量命名（UPPER_CASE，与函数命名完全不同）
- [[cpp-naming-private-members]] — 私有成员方法命名（m_ 前缀 + camelCase）
- [[cpp-naming-namespaces]] — 命名空间命名（全小写点分隔）
