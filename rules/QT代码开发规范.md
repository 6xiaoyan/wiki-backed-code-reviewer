# QT代码开发规范

## 一、规范目的与适用范围

### 1.1 规范目的

统一软件编程风格，提升源程序的可读性、可靠性与可重用性，降低维护成本，提高软件产品生产力，具体遵循以下原则：

*   为开发者提供明确开发依据，提升开发效率
    
*   简化代码交流与维护流程
    
*   优化代码美观度，降低阅读难度
    
*   清晰代码逻辑，便于理解
    
*   规范公司软件开发设计流程
    

### 1.2 适用范围

适用于使用Qt框架开发的所有软件。

## 二、Qt标准代码规范

代码规范主要参考Qt官网[Qt Coding Style - Qt Wiki](https://wiki.qt.io/Qt_Coding_Style)要求，符合常规的C++与Qt代码开发规范需求。

### 2.1 缩进规则

*   采用4个空格作为缩进单位
    
*   仅使用空格，禁止使用TAB键
    

### 2.2 变量声明规范

*   每行仅声明一个变量
    
*   避免使用短变量名（如"a"、"rbarr"、"nughdeget"）
    
*   单字符变量仅用于临时变量或循环计数
    
*   变量延迟定义，在真正需要使用时再声明
    

```c++
// Wrong（错误示例）
int a, b;
char *c, *d;

// Correct（正确示例）
int height;
int width;
char *nameOfThis;
char *nameOfThat;

```

*   变量名采用驼峰命名法：以小写字符开头，后续单词首字母大写
    
*   避免使用缩写，保持变量名语义清晰
    

```c++
// Wrong（错误示例）
short Cntr;
char ITEM_DELIM = '';

// Correct（正确示例）
short counter;
char itemDelimiter = '';

```

*   类名命名规则：首字母大写；Qt公有类以"Q"开头（如QRgb），Qt公有函数通常以"q"开头（如qRgb）
    

### 2.3 空白字符规范

*   利用空行对语句进行合理分组，提升代码层次感
    
*   空行仅保留1行，禁止连续空多行
    
*   关键字与后续括号之间、括号与大括号之间需加1个空格
    

```c++
// Wrong（错误示例）
if(foo){
}

// Correct（正确示例）
if (foo) {
}

```

*   指针与引用符号规范：指针/引用符号紧跟类型，与 C++ 规范一致（参见 C++ 规范 1.3 节）
    

```c++
char* x;
const QString& myString;
const char* const y = "hello";

```

*   二元操作符（如+、-、\*、/、==等）前后需加空白字符
    
*   类型转换后不加空白字符
    
*   避免使用C风格类型转换，优先使用C++风格转换
    

```c++
// Wrong（错误示例）
char* blockOfMemory = (char* ) malloc(data.size());

// Correct（正确示例）
char *blockOfMemory = reinterpret_cast<char*>(malloc(data.size()));

```

### 2.4 大括号使用规范

*   基本原则：左大括号与语句同行，不单独换行
    

```c++
// Wrong（错误示例）
if (codec)
{
}

// Correct（正确示例）
if (codec) {
}

```

*   例外场景1：函数定义与类定义中，左大括号单独占一行
    

```c++
// 函数定义示例
static void foo(int g)
{
    qDebug("foo: %i", g);
}

// 类定义示例
class Moo
{
};

```

*   例外场景2：控制语句体仅1行代码时，不使用大括号
    

```c++
// Wrong（错误示例）
if (address.isEmpty()) {
    return false;
}

for (int i = 0; i < 10; ++i) {
    qDebug("%i", i);
}

// Correct（正确示例）
if (address.isEmpty())
    return false;

for (int i = 0; i < 10; ++i)
    qDebug("%i", i);

```

*   例外场景3：父语句跨多行时，必须使用大括号
    

```c++
// Correct（正确示例）
if (address.isEmpty() || !isValid()
    || !codec) {
    return false;
}

```

*   例外场景4：if-else结构中，任意一支跨多行时，两侧均需使用大括号
    

```c++
// Wrong（错误示例）
if (address.isEmpty())
    return false;
else {
    qDebug("%s", qPrintable(address));
}

// Correct（正确示例）
if (address.isEmpty()) {
    return false;
} else {
    qDebug("%s", qPrintable(address));
}

// Wrong（错误示例）
if (a)
    if (b)
        …
    else
        …

// Correct（正确示例）
if (a) {
    if (b)
        …
    else
        …
}

```

*   例外场景5：控制语句体为空时，使用空大括号（禁止仅写分号）
    

```c++
// Wrong（错误示例）
while (a);

// Correct（正确示例）
while (a) {}

```

### 2.5 圆括号使用规范

*   复杂表达式需用圆括号分组，明确运算优先级
    

```c++
// Wrong（错误示例）
if (a && b || c)
a + b & c

// Correct（正确示例）
if ((a && b) || c)
(a + b) & c

```

### 2.6 Switch语句规范

*   case标签与switch关键字对齐（同一缩进层级）
    
*   每个case分支需包含break/return语句，或用注释说明"fall through"（穿透）逻辑
    

```c++
switch (myEnum) {
case Value1:
    doSomething();
    break;
case Value2:
    doSomethingElse();
    // fall through（注释说明穿透逻辑）
default:
    defaultHandling();
    break;
}

```

### 2.7 代码断行规范

*   每行代码长度不超过100个字符，超长时需断行
    
*   断行规则：逗号置于行尾，操作符置于下一行开头（便于识别断行位置）
    

```c++
// Correct（正确示例）
if (longExpression
    + otherLongExpression
    + otherOtherLongExpression) {
}

// Wrong（错误示例）
if (longExpression +
    otherLongExpression +
    otherOtherLongExpression) {
}

```

### 2.8 继承与virtual关键字规范

*   重写虚函数时，头文件中不添加virtual关键字（仅在基类声明时使用）
    

### 2.9 通用例外原则

*   若严格遵循规则导致代码可读性下降，可灵活调整（以代码清晰为首要目标）
    

*   语句右括号不单独换行；函数实现、类定义的左大括号单独换行（与Qt标准一致）
    
*   缩进长度统一为4个字符，TAB键自动转换为空格（Qt Creator默认功能可满足）
    
*   每行代码最大长度扩展为120个字符（兼容复杂业务逻辑场景）
    
*   命名对齐规则：类名首字母大写，函数名首字母小写（与Qt保持一致；若项目已采用全大写风格，以项目现有风格为准）
    
*   大括号省略限制：仅当if语句体为1行且无else分支时，可省略大括号（格式：`if (xx) xx;`）
    
*   空行使用原则：代码简洁优先，不提倡冗余空行；可通过注释补充代码逻辑说明（界面程序重点保证函数逻辑清晰，实现细节次要）
    

## 三、命名规范

因Qt库在项目中占比高，为避免命名混乱，制定以下建议命名规范

### 3.1 文件命名规范

*   采用Qt Creator默认命名风格：类名直接转为小写，无下划线等分隔符（如类名`InsWidget`对应文件名`inswidget.h`/`inswidget.cpp`）
    

### 3.2 类名命名规范

*   类名语义：需为意思明确的名词短语，可使用缩写（禁止以动词、形容词结尾）
    
*   界面类命名：最后一个单词体现父类属性（如`LoginDialog`、`UserTableWidget`）；全新概念子类可自主命名，无需强制包含父类信息
    
*   自定义类限制：与Qt无关的自建类禁止以单个"Q"开头（避免与Qt类混淆；仅当封装为Qt风格模块时，可使用"Q"前缀）
    

### 3.3 方法名命名规范

*   方法名语义：普通方法为动词或动宾短语（体现动作含义）；属性相关方法遵循Qt风格
    
    *   获取属性：不添加"get"前缀（如`widget->width()`）
        
    *   设置属性：添加"set"前缀（如`widget->setWidth(int width)`）
        
    *   计算型获取：可添加"get"前缀（适用于非直接属性的计算结果）
        
*   方法名冗余限制：禁止包含当前类名（调用时已明确类归属，无需重复）
    

#### 3.3.1 基本原则示例

*   名词类+名词方法：`int Apple::coreNum()`（苹果的核数）、`void Apple::setCoreNum(int num)`（设置苹果的核数）
    
*   名词类+动词方法：`bool Apple::beEaten(human::Mouth *mouth)`（苹果被人吃）、`bool Apple::beEaten(monkey::Mouth *mouth)`（函数重载）
    

#### 3.3.2 信号命名规范

*   禁止在信号名中添加"signal"标识（通过头文件查看信号列表）
    
*   信号名语义：体现类的状态变化（动词短语的完成时），参考Qt信号风格：
    
    *   `void customContextMenuRequested(const QPoint &pos)`（自定义上下文菜单被请求）
        
    *   `void windowIconChanged(const QIcon &icon)`（窗口图标已变更）
        
    *   `void windowTitleChanged(const QString &title)`（窗口标题已变更）
        

#### 3.3.3 槽函数命名规范

*   禁止在槽函数名中添加"slot"标识（Qt Creator通过图标区分信号/槽/成员函数）
    
*   槽函数语义：体现具体操作（动宾短语），参考Qt槽函数风格：
    
    *   `void hide()`（隐藏窗口）
        
    *   `void setEnabled(bool)`（设置启用状态）
        
    *   `void showMaximized()`（最大化显示）
        
*   特殊槽函数：`on_obj_signal()`格式函数（Qt自动关联）仅用作内部实现，不对外暴露（此类函数偏向过程化，可读性较低）
    

### 3.4 变量名命名规范

*   普通变量：使用Qt类名去掉"Q"后的小写形式，下划线分隔单词（如`QString`变量名`user_name`）
    
*   无独立概念变量：变量名最后一个单词为类名（体现变量类型）
    
*   UI控件变量：采用驼峰命名法，首单词为控件类名缩写（需明确简练）
    

#### 3.4.1 UI控件类名缩写表

| 基础控件类名 | 统一缩写 | 使用率 |
| --- | --- | --- |
| QLabel | lbl | 常用 |
| QWidget | wgt | 常用 |
| QPushButton | btn | 常用 |
| QToolButton | tbtn | 很少 |
| QGroupBox | grb | 常用 |
| QLineEdit | edt | 常用 |
| QSpinBox | spn | 常用 |
| QDoubleSpinBox | dspn | 常用 |
| QCheckBox | chb | 常用 |
| QStackedWidget | stk | 常用 |
| QTableWidget | tblWgt | 常用 |
| QListWidget | lstWgt | 偶尔 |
| QTreeWidget | treeWgt | 特殊用 |
| QScrollArea | scrArea | 少 |
| QDialog | dlg | \- |
| QTextBrowser | txb | 少 |

*   其他控件：可内部自定义缩写，需在项目内保持统一
    

## 四、代码内容约定

### 4.1 代码行数限制

*   类实现文件：单个类代码量达1000行时，评估是否拆分（避免文件过大导致阅读困难）
    
*   函数实现：单个函数代码量超2000行时，必须拆分（拆分逻辑关联度低的代码块）
    

### 4.2 代码顺序规范

#### 4.2.1 头文件包含顺序

1.  自动生成的必要文件（如Qt UI文件对应的`.h`）
    
2.  第三方库头文件（如`#include "boost/xxx.h"`）
    
3.  项目公共库头文件（如`#include <project/common.h>`）
    
4.  工程内其他头文件（如`#include "userinfo.h"`）
    

#### 4.2.2 类成员声明顺序

1.  public成员
    
    *   构造函数、析构函数
        
    *   普通成员函数
        
    *   信号（signals）
        
    *   槽函数（slots）
        
2.  protected成员（顺序同上）
    
3.  private成员（顺序同上）
    
4.  成员变量（按public→protected→private顺序）
    

*   实现文件（`.cpp`）中函数顺序，建议与头文件（`.h`）声明顺序保持一致
    

### 4.3 Qt库引用规范

*   引用Qt库头文件时，使用无`.h`后缀的格式（Qt标准风格）
    

```c++
// 正确写法
#include <QPushButton>

// 错误写法
#include <qpushbutton.h>

```

### 4.4 内存管理规范

*   Qt对象内存管理：优先通过"父类管理子类"机制（设置父对象后，父对象析构时自动销毁子类），避免内存泄漏
    
*   普通指针管理：遵循"谁new谁delete"原则；不建议日常使用boost智能指针（与Qt内存管理思路存在差异，必要时可特殊使用）
    

## 5、命名与实现示例

### 5.1 推荐示例

*   类名：`InsWidget`（合理使用缩写，体现控件属性）
    
*   方法名：`void ClientPlayer::addCard(const Card *card, Place place)`（语义清晰，无冗余信息）
    
*   变量名：`QHash<QString, autogen::GrabParam> m_param_hash`（符合命名规范，类型明确）
    

### 5.2 不推荐示例及优化方案

#### 示例1：类名`OffsOrReltool`

*   问题：概念模糊，未体现父类属性
    
*   优化方案：重新定义类逻辑，明确类职责后命名（如`OffsetRelateToolWidget`）
    

#### 示例2：类名`QMotionAdvWgt : public QDialog`

*   问题：以"Q"开头（非Qt官方类），类名后缀`Wgt`（暗示父类为QWidget）与实际父类`QDialog`冲突
    
*   优化方案：修改父类为`QWidget`，或重命名为`MotionAdvDialog`（去掉"Q"前缀，后缀与父类匹配）
    

#### 示例3：方法名`void QMotionAdvWgt::SetBtnMotinoSupEnable(bool state)`

*   问题：拼写错误（`Motino`应为`Motion`）、缩写模糊（`Sup`含义不明确）、参数语义弱（`state`未说明true/false对应含义）
    
*   优化方案：`void MotionAdvWgt::enableMotionSup(bool isEnable)`（修正拼写，明确参数语义，去掉冗余"Btn"）
    

#### 示例4：方法名`bool QCalibrationWidget::FromCalibrationToOther()`

*   问题：语义不规范（中文语序问题）、包含冗余类名（`Calibration`与类名重复）
    
*   优化方案：`bool CalibrationWidget::switchOut()`（简化语义，去掉冗余信息）
    

#### 示例5：变量名`QList<QString> *m_list_conveyor_name`

*   问题：使用指针存储列表（无必要）、未使用Qt封装类（`QStringList`替代`QList<QString>`）、变量名后缀顺序不合理（`list`应置于最后）
    
*   优化方案：`QStringList m_conveyor_names`或`QStringList m_conveyor_name_list`
    

## 六、版本管理规范

### 6.1 主分支定义

#### 6.1.1 master分支

*   定位：对外发布版本分支（稳定版本）
    
*   代码提交规则：需经过代码审查（CR）后才能合并，确保代码质量
    
*   版本保存：每个发布版本需打tag标记（如`v1.0.0`），便于追溯
    

#### 6.1.2 dev分支

*   定位：日常开发分支（最新开发版本）
    
*   代码提交规则：
    
    *   基于现有代码开发，且不影响其他模块运行的功能，无需代码审查（开发者自行测试维护）
        
    *   鼓励版本兼容性开发，禁止同时维护多个不兼容版本（降低维护成本）
        


