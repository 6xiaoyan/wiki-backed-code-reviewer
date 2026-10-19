---
domain: qt
rule_id: qt-no-virtual-on-override
title: 重写虚函数时头文件中不添加 virtual 关键字
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.8"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 重写虚函数时头文件中不添加 virtual 关键字
## 规则条款

在派生类中**重写（override）基类虚函数**时，**头文件声明中不添加 `virtual` 关键字**，仅使用 `override` 关键字（C++11）或 `Q_DECL_OVERRIDE`（Qt 5 兼容写法，已废弃）。这是 Qt 项目的编码规范，规则原因：- `override` 已明确表达「这是重写基类虚函数」，再写 `virtual` 是冗余的
- 减少屏幕噪音，使代码更整洁- 遵循 C++ Core Guidelines C.128

## 正确示例

```cpp
class BaseWidget {
public:
    virtual void paintEvent(QPaintEvent *event);
    virtual QSize sizeHint() const;
};

class DerivedWidget : public BaseWidget {
public:
    void paintEvent(QPaintEvent *event) override;  // 正确：仅 override，无 virtual
    QSize sizeHint() const override;                // 正确：仅 override，无 virtual

protected:
    void mousePressEvent(QMouseEvent *event) override;
    void keyPressEvent(QKeyEvent *event) override;
};
```

## 错误示例

```cpp
class DerivedWidget : public BaseWidget {
public:
    virtual void paintEvent(QPaintEvent *event) override;  // 错误：virtual 和 override 重复
    virtual QSize sizeHint() const override;                // 错误：virtual 冗余

    virtual void mousePressEvent(QMouseEvent *event) override;  // 错误：应省略 virtual
};

class AnotherWidget : public QWidget {
    virtual void closeEvent(QCloseEvent *e) override;  // 错误：virtual 冗余
};
```

## 检查方法
1. 解析类声明中的成员函数声明。2. 检测同时出现 `virtual` 和 `override`（或 `Q_DECL_OVERRIDE`、`final`）的声明行。3. 标记 `virtual ... override` 的组合为违规。
正则表达式：`virtual\s+.*\boverride\b` 匹配同一行中同时有 `virtual` 和 `override` 的声明。
## 修复指南

1. 删除 `virtual` 关键字，保留 `override`。2. 如果使用了 `Q_DECL_OVERRIDE`，建议升级为 C++11 标准的 `override`。3. 示例修复：   ```cpp
   // 修改前：   virtual void paintEvent(QPaintEvent *event) override;
   // 修改后：   void paintEvent(QPaintEvent *event) override;
   ```
4. 使用 clang-tidy：`modernize-use-override` 检查，并手动删除 `virtual`。5. Qt Creator：`Tools > Options > C++ > Code Model > Clang-Tidy` 启用 `modernize-use-override`。
## 审查清单

- [ ] 所有重写函数的声明中无 `virtual` 关键字- [ ] 所有重写函数均使用了 `override` 关键字- [ ] Qt 5 兼容代码中使用了 `Q_DECL_OVERRIDE`（无 `virtual`）- [ ] 新建代码统一使用 C++11 `override`

## 关联页面

（无直接关联页面）