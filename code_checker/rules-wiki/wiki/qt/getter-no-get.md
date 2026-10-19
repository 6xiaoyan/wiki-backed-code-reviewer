---
domain: qt
rule_id: qt-getter-no-get
title: 获取属性不使用 get 前缀
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§3.3 方法命名"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-method-verb-phrase]]
  - [[qt-method-no-classname]]
---

# 获取属性不使用 get 前缀

## 规则条款

遵循 Qt 风格：获取属性的方法不添加 `get` 前缀，直接使用属性名（如 `widget->width()`）。设置属性的方法添加 `set` 前缀（如 `widget->setWidth(int)`）。计算型获取（返回非直接属性的计算结果）可以添加 `get` 前缀。
## 正确示例

```cpp
class UserProfile : public QObject
{
    Q_OBJECT

public:
    // getter：直接属性获取，不加 get 前缀
    QString name() const;
    int age() const;
    bool isActive() const;
    QPixmap avatar() const;
    QDateTime createdAt() const;

    // setter：加 set 前缀
    void setName(const QString &name);
    void setAge(int age);
    void setActive(bool active);
    void setAvatar(const QPixmap &avatar);

    // 计算型获取：非直接属性的计算结果，允许 get 前缀
    QString getDisplayName() const;       // 组合 firstName + lastName
    double getAverageScore() const;       // 从成绩列表计算平均分
    int getTotalPageCount() const;        // 从数据量和页大小计算
    QSize getRequiredSize() const;        // 根据内容计算的所需尺寸

signals:
    void nameChanged(const QString &name);
    void ageChanged(int age);
};
```

## 错误示例

```cpp
class UserProfile : public QObject
{
    Q_OBJECT

public:
    // 错误：直接属性获取加了 get 前缀
    QString getName() const;              // 应为 name()
    int getAge() const;                   // 应为 age()
    QPixmap getAvatar() const;            // 应为 avatar()
    QDateTime getCreatedAt() const;       // 应为 createdAt()

    // 错误：bool 型获取加 get 前缀（Qt 风格用 isXxx）
    bool getActive() const;               // 应为 isActive()
    bool getEnabled() const;             // 应为 isEnabled()

    // 错误：getter 不加 get，但 setter 名称不匹配
    void setName(const QString &name);    // getter 应为 name()，而非 getName()
    void setAge(int age);                 // getter 应为 age()，而非 getAge()

    // 错误：非计算型的直接属性加了不必要的 get
    QString getFilePath() const;          // filePath() 即可（直接属性）
};
```

```cpp
// 对比表：Qt 风格 vs 非 Qt 风格
// Qt 风格 (正确)                    非 Qt 风格 (错误)
// widget->width()                    widget->getWidth()
// button->text()                     button->getText()
// model->rowCount()                  model->getRowCount()
// item->isSelected()                 item->getSelected()
// dialog->result()                   dialog->getResult()
```

## 检查方法
使用正则表达式检测：

1. 提取类中所有 public 成员函数声明。2. 匹配以 `get` 开头且首字母大写的函数，正则：`\bget[A-Z]\w*`。3. 对于匹配到的函数，检查其实现是否为计算型获取：   - 计算型：函数体内包含非平凡计算逻辑（如组合多个成员、数据库查询、数学运算等）。   - 直接型：仅是 `return m_xxx;` 这类直接返回成员变量。4. 直接型的 `getXxx()` 标记为违规。5. bool 返回值的 `getXxx()` 如可与 `isXxx()` 互换，标记为违规并建议用 `is` 前缀。
## 修复指南

1. 直接属性获取：去掉 `get` 前缀，首字母改小写：
   - `getName()` → `name()`
   - `getAge()` → `age()`
   - `getFilePath()` → `filePath()`
2. bool 类型获取：`getActive()` → `isActive()`、`getEnabled()` → `isEnabled()`。3. 确保 setter 名称与 getter 匹配：getter `name()` 对应 setter `setName()`。4. 计算型获取（返回非直接属性）：保留 `get` 前缀或在注释中说明计算性质。5. 更新所有调用处的函数名。
## 审查清单

- [ ] 直接属性 getter 不加 `get` 前缀
- [ ] bool 型 getter 使用 `is` 前缀
- [ ] setter 与 getter 名称对应（如 `name()` / `setName()`）
- [ ] 有 `get` 前缀的方法确实是计算型获取
- [ ] 所有调用处已同步更新
## 关联页面

- [[qt-method-verb-phrase]]：普通方法名需为动词或动宾短语
- [[qt-method-no-classname]]：方法名禁止包含当前类名