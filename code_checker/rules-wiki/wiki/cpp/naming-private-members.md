---
domain: cpp
rule_id: cpp-naming-private-members
title: 私有成员命名规范
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.1 命名约定"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-naming-classes]]
  - [[cpp-naming-functions]]
  - [[cpp-naming-variables]]
  - [[cpp-naming-constants]]
  - [[cpp-naming-namespaces]]
---

# 私有成员命名规范

## 规则条款

类的私有成员（成员变量和私有成员函数）必须添加特殊前缀或后缀，以区别于局部变量和公有成员。同一项目中必须统一选择一种风格，禁止混合使用。
两种允许的风格（二选一，项目内统一）：

- **方式 1（m_ 前缀）**：使用 `m_` 前缀 + camelCase，如 `m_userAge`（存储用户年龄）、`m_checkPermission`（内部校验权限）
- **方式 2（_ 后缀）**：使用 camelCase + `_` 后缀，如 `userAge_`（与 `m_userAge` 含义相同）、`checkPermission_`（与 `m_checkPermission` 含义相同）

公有成员不得使用 `m_` 前缀或 `_` 后缀，以明确区分访问级别。
## 正确示例

```cpp
// 方式 1：m_ 前缀（项目统一使用此后所有示例以此为准）
class UserManager {
public:
    void loadUsers();
    int totalCount;                     // 公有成员 — 无前缀

private:
    std::string m_userName;             // 私有成员 — m_ 前缀
    int m_userAge;                      // 私有成员 — m_ 前缀
    bool m_isAdmin;                     // 私有成员 — m_ 前缀

    bool m_checkPermission(int userId); // 私有方法 — m_ 前缀
};

// 方式 2：_ 后缀（项目选择此后缀风格时使用）
class DataCache {
public:
    void refresh();

private:
    std::vector<int> cachedIds_;        // 私有成员 — _ 后缀
    size_t maxSize_;                    // 私有成员 — _ 后缀
    bool isExpired_;                    // 私有成员 — _ 后缀

    void validate_();                   // 私有方法 — _ 后缀
};
```

## 错误示例

```cpp
// 错误：私有成员无前缀/后缀（无法区分私有和局部变量）
class BadExample {
private:
    std::string userName;            // 应为 m_userName 或 userName_
    int userAge;                     // 应为 m_userAge 或 userAge_
};

// 错误：公有成员使用了 m_ 前缀
class BadPublic {
public:
    int m_publicVar;                 // 公有成员不应有 m_ 前缀
};

// 错误：混合使用两种风格
class MixedStyle {
private:
    std::string m_userName;          // m_ 前缀
    int userAge_;                    // _ 后缀 — 同一项目禁止混用！
};

// 错误：匈牙利命名法前缀（不是 m_）
class HungarianStyle {
private:
    int iCount;                      // 应为 m_count 或 count_
    std::string strName;             // 应为 m_name 或 name_
};

// 错误：snake_case + m_ 前缀
class SnakeStyle {
private:
    std::string m_user_name;         // 应为 m_userName（camelCase 部分也需遵守）
};
```

## 检查方法
1. 扫描类定义中 `private:` / `protected:` 区域内的成员变量声明
2. 验证每个私有成员是否带有 `m_` 前缀或 `_` 后缀
3. 检查项目中是否存在两种风格混用（全局扫描 `m_[a-z]` 和 `[a-z]_` 模式）
4. 检查公有成员是否错误地使用了 `m_` 前缀或 `_` 后缀
5. 正则模式（m_ 前缀）：`private:\s*(?:\w+\s+)(m_[a-z][a-zA-Z0-9]*)\s*[;=]`
6. 正则模式（_ 后缀）：`private:\s*(?:\w+\s+)([a-z][a-zA-Z0-9]*_)\s*[;=]`
7. 反模式（公有成员带前缀）：`public:\s*(?:\w+\s+)(m_[a-z][a-zA-Z0-9]*)\s*[;=]`

## 修复指南

1. 为缺少标识的私有成员添加前缀/后缀：`userName` → `m_userName` 或 `userName_`
2. 移除公有成员的前缀/后缀：`m_publicVar` → `publicVar`
3. 统一项目风格：若项目已使用 `m_` 前缀，将所有 `_` 后缀改为 `m_` 前缀（反之亦然）
4. 去除匈牙利命名法前缀：`iCount` → `m_count` 或 `count_`
5. 将 snake_case 部分转为 camelCase：`m_user_name` → `m_userName`
6. 注意：修改私有成员名需要同时修改类内部所有引用点（成员函数内 `this->` 或直接引用）

## 审查清单

- [ ] 所有私有成员变量带有 m_ 前缀或 _ 后缀
- [ ] 所有私有成员函数带有 m_ 前缀或 _ 后缀
- [ ] 公有成员没有 m_ 前缀或 _ 后缀
- [ ] 项目内风格统一（要么全用 m_ 前缀，要么全用 _ 后缀）
- [ ] 前缀/后缀后的部分仍遵守 camelCase 规范
- [ ] 无匈牙利命名法前缀（i、str、b 等）
- [ ] 无 snake_case 组合（m_user_name 应为 m_userName）

## 关联页面

- [[cpp-naming-classes]] — 类命名（PascalCase，不用 m_ 前缀）
- [[cpp-naming-functions]] — 公有函数命名（camelCase，无 m_ 前缀）
- [[cpp-naming-variables]] — 变量命名（camelCase，公有成员遵守此规则）
- [[cpp-naming-constants]] — 常量命名（UPPER_CASE，与私有成员命名完全不同）
- [[cpp-naming-namespaces]] — 命名空间命名（全小写点分隔）
