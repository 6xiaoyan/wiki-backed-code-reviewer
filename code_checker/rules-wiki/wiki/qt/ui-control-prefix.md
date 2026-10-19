---
domain: qt
rule_id: qt-ui-control-prefix
title: UI 控件变量命名前缀
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.4 变量命名"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-var-qclass-lowercase]]
  - [[qt-var-last-word-type]]
  - [[cpp-naming-variables]]
---

# UI 控件变量命名前缀

## 规则条款

UI 控件变量采用驼峰命名法，首单词为控件类名缩写。缩写应明确简练，在声明中使用 `m_<缩写><驼峰语义>` 格式。例如 `QLineEdit` 类型变量命名为 `m_edtPassword`，`QPushButton` 类型命名为 `m_btnSubmit`。

### UI 控件类名标准缩写表

| 控件类型 | 统一缩写 | 示例变量名 |
|--------|----------|-----------|
| `QLabel` | `lbl` | `m_lblName` |
| `QPushButton` | `btn` | `m_btnSubmit` |
| `QToolButton` | `tbtn` | `m_tbtnConfig` |
| `QGroupBox` | `grb` | `m_grbSettings` |
| `QLineEdit` | `edt` | `m_edtPassword` |
| `QSpinBox` | `spn` | `m_spnAge` |
| `QDoubleSpinBox` | `dspn` | `m_dspnWeight` |
| `QCheckBox` | `chb` | `m_chbRemember` |
| `QStackedWidget` | `stk` | `m_stkPages` |
| `QTableWidget` | `tblWgt` | `m_tblWgtData` |
| `QListWidget` | `lstWgt` | `m_lstWgtItems` |
| `QTreeWidget` | `treeWgt` | `m_treeWgtFiles` |
| `QScrollArea` | `scrArea` | `m_scrAreaContent` |
| `QDialog` | `dlg` | `m_dlgSettings` |
| `QTextBrowser` | `txb` | `m_txbLog` |
| `QWidget` | `wgt` | `m_wgtContainer` |

## 正确示例

```cpp
class MainWindow : public QWidget
{
    Q_OBJECT

    // 控件声明——m_ 前缀 + 控件缩写 + 驼峰语义
    QLabel        *m_lblName;
    QLabel        *m_lblStatus;
    QPushButton   *m_btnSubmit;
    QPushButton   *m_btnCancel;
    QToolButton   *m_tbtnBold;
    QGroupBox     *m_grbUserInfo;
    QLineEdit     *m_edtPassword;
    QLineEdit     *m_edtUsername;
    QSpinBox      *m_spnAge;
    QDoubleSpinBox *m_dspnWeight;
    QCheckBox     *m_chbRememberMe;
    QStackedWidget *m_stkMainPages;
    QTableWidget  *m_tblWgtRecords;
    QListWidget   *m_lstWgtDevices;
    QTreeWidget   *m_treeWgtFolders;
    QScrollArea   *m_scrAreaPreview;
    QDialog       *m_dlgSettings;
    QTextBrowser  *m_txbMessageLog;
    QWidget       *m_wgtHeader;
};
```

## 错误示例

```cpp
class MainWindow : public QWidget
{
    // 以下均为错误写法——控件名称不包含标准缩写前缀

    QLabel    *m_nameLabel;       // 应为 m_lblName
    QPushButton *m_submitButton;  // 应为 m_btnSubmit
    QLineEdit *m_passwordEdit;    // 应为 m_edtPassword
    QSpinBox  *m_ageSpinBox;      // 应为 m_spnAge
    QCheckBox *m_rememberCheckBox;// 应为 m_chbRememberMe

    // 使用了非标准缩写
    QPushButton *m_pbSubmit;      // pb 不在标准缩写表中，应为 m_btnSubmit
    QLineEdit   *m_lePassword;    // le 不在标准缩写表中，应为 m_edtPassword

    // 缺少 m_ 前缀
    QLabel    *lblName;           // 应为 m_lblName
};
```

## 检查方法
1. 使用正则表达式匹配控件声明：`(QLabel|QPushButton|QToolButton|QGroupBox|QLineEdit|QSpinBox|QDoubleSpinBox|QCheckBox|QStackedWidget|QTableWidget|QListWidget|QTreeWidget|QScrollArea|QDialog|QTextBrowser|QWidget)\s*\*\s*(m_\w+)`
2. 提取变量名的前缀部分（`m_` 之后、驼峰大写字母之前的部分）。
3. 对照标准缩写表校验前缀：
   - `lbl` 对应 `QLabel`
   - `btn` 对应 `QPushButton`
   - `tbtn` 对应 `QToolButton`
   - `grb` 对应 `QGroupBox`
   - `edt` 对应 `QLineEdit`
   - `spn` 对应 `QSpinBox`
   - `dspn` 对应 `QDoubleSpinBox`
   - `chb` 对应 `QCheckBox`
   - `stk` 对应 `QStackedWidget`
   - `tblWgt` 对应 `QTableWidget`
   - `lstWgt` 对应 `QListWidget`
   - `treeWgt` 对应 `QTreeWidget`
   - `scrArea` 对应 `QScrollArea`
   - `dlg` 对应 `QDialog`
   - `txb` 对应 `QTextBrowser`
   - `wgt` 对应 `QWidget`
4. 不匹配的标记为违规。

## 修复指南

1. 确定控件类型（如 `QPushButton`）。
2. 查表获取标准缩写（如 `btn`）。
3. 将变量名改为 `m_<缩写><驼峰语义>`：
   - `m_nameLabel` (QLabel) → `m_lblName`
   - `m_submitButton` (QPushButton) → `m_btnSubmit`
   - `m_passwordEdit` (QLineEdit) → `m_edtPassword`
   - `m_ageSpinBox` (QSpinBox) → `m_spnAge`
4. 同步更新头文件和源文件中所有对该成员的引用
5. 如使用 Qt Designer 和 `ui_*.h` 自动生成文件，需修改 UI 文件中控件的 `objectName`

## 审查清单

- [ ] 所有 UI 控件成员变量声明使用了 `m_` 前缀
- [ ] 控件类型前缀在标准缩写表中
- [ ] 前缀之后为驼峰命名的语义部分（首字母大写）
- [ ] 同一类型控件使用相同前缀（如所有 `QPushButton` 都以 `m_btn` 开头）
- [ ] 无自定义缩写偏离标准

## 关联页面

- [[qt-var-qclass-lowercase]]：Qt 类变量下划线命名
- [[qt-var-last-word-type]]：变量名末尾类型标识
- [[cpp-naming-variables]]：C++ 变量命名总体规范
