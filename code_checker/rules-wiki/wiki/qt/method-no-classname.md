---
domain: qt
rule_id: qt-method-no-classname
title: 方法名禁止包含当前类名
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
  - [[qt-getter-no-get]]
---

# 方法名禁止包含当前类名
## 规则条款

方法名禁止包含当前类名。因为调用时已经通过对象或指针明确了类归属（如`obj->method()`），在方法名中重复类名是冗余的。
## 正确示例

```cpp
class QMotionAdvWgt : public QWidget
{
    Q_OBJECT

public:
    // 正确：方法名不含类名，简洁明了    void setName(const QString &name);
    void setSpeed(int speed);
    void startMotion();
    void resetPosition();
    QString currentStatus() const;

    // 构造函数可以有与类名相同的函数名（这不是违规）
    // explicit QMotionAdvWgt(QWidget *parent = nullptr);  // 构造，不受此规则约束};
```

## 错误示例

```cpp
class QMotionAdvWgt : public QWidget
{
    Q_OBJECT

public:
    // 错误：方法名包含了类名"MotionAdvWgt"
    void setMotionAdvWgtName(const QString &name);  // 应为 setName()
    void initMotionAdvWgtUI();                      // 应为 initUI()
    void resetMotionAdvWgtState();                  // 应为 resetState()

    // 错误：包含了类名的部分（同样是冗余）
    int getMotionAdvWgtSpeed() const;               // 应为 speed()
    void updateMotionAdvWgtDisplay();               // 应为 updateDisplay()
};

class UserProfileDialog : public QDialog
{
public:
    // 错误：方法名包含类名
    void showUserProfileDialog();                   // 应为 show()
    void closeUserProfileDialog();                  // 应为 close() (QDialog 已有)

    // 正确：方法名不含类名
    void loadProfileData();
    void saveChanges();
};
```

## 检查方法
使用正则表达式检测：

1. 提取每个类定义中的类名（`class ClassName` 中的 `ClassName`）。2. 提取该类中所有成员函数声明的方法名。3. 对类名做大小写不敏感的匹配，检查方法名是否包含类名的全部或显著部分。4. 考虑类名的常见变体：
   - 完整类名：`MotionAdvWgt`
   - 类名的camelCase：`motionAdvWgt`
   - 去掉前缀的类名：`AdvWgt`
5. 排除构造函数和析构函数（它们必须与类名相同）。
正则思路（按类名片段匹配）：对于如`QMotionAdvWgt`，其方法名不应包含`MotionAdvWgt`、`motionAdvWgt`、`AdvWgt` 等核心词汇
## 修复指南

1. 从方法名中移除类名或其变体部分。2. 保持剩余部分的语义完整性：
   - `setMotionAdvWgtName()` → `setName()`（调用者已知道是MotionAdvWgt 对象。   - `initMotionAdvWgtUI()` → `initUI()`
   - `resetMotionAdvWgtState()` → `resetState()`
3. 如果去掉类名后方法名与其他父类方法或同名方法冲突，考虑添加功能域前缀而非类名。4. 更新所有调用处。
## 审查清单

- [ ] 成员函数名不包含定义它的类名
- [ ] 成员函数名不包含类名的任何显著变体- [ ] 去掉冗余后方法名语义仍然清晰
- [ ] 所有调用处已同步更新
## 关联页面

- [[qt-method-verb-phrase]]：普通方法名需为动词或动宾短语
- [[qt-getter-no-get]]：getter 不加 get 前缀
