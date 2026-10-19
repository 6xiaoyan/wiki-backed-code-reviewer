---
domain: cpp
rule_id: cpp-operator-spacing
title: 运算符与指针/引用间距
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.3 代码格式"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-indentation]]
  - [[cpp-line-width]]
  - [[cpp-parameter-alignment]]
---

# 运算符与指针/引用间距

## 规则条款

C++ 代码中的空格使用规则分为两类：

### 运算符空格
所有二元、三元运算符前后必须有空格：

- 算术运算符：`+` `-` `*` `/` `%`
- 比较运算符：`==` `!=` `<` `<=` `>` `>=`
- 逻辑运算符：`&&` `||`
- 位运算符：`&` `|` `^` `~` `<<` `>>`
- 赋值运算符：`=` `+=` `-=` `*=` `/=` `%=` `&=` `|=` `^=` `<<=` `>>=`
- 三元运算符：`?` `:`

一元运算符（`!`、`++`、`--`、`+`（正号）、`-`（负号））与操作数之间不加空格。

### 指针和引用符号
指针符号 `*` 和引用符号 `&` 必须**紧跟类型名**，而非紧跟变量名。符号与类型名之间不加空格，符号与变量名之间有一个空格。
- `char* x;` 而非 `char *x;`
- `const std::string& name` 而非 `const std::string &name`

这条规则与某些 C 风格指南（将 `*` 紧跟变量名）相反，本项目采用 C++ 惯用风格：类型信息（包括指针/引用修饰）应紧密绑定在一起。

## 正确示例

```cpp
// binary operators — spaces on both sides
int result = a + b * c;
bool isValid = (x > 0) && (y < maxValue);
int masked = value & 0xFF;
value |= 0x10;

// assignment operators
sum += currentValue;
count = baseCount + extra;

// ternary operator
auto label = (value > 0) ? "positive" : "non-positive";

// comma operator in for loop
for (int i = 0, j = n - 1; i < j; ++i, --j) {
    // ...
}

// unary operators — no space
if (!isEmpty) {
    ++counter;
}
int negative = -positiveValue;

// pointer and reference — symbol next to type
char* buffer = new char[size];
const std::string& name = getName();
void process(const DataPacket* packet, ResultWriter& writer);

// function return type with pointer
NetworkManager* createManager();
const Settings& getSettings();

// template parameters with pointers
std::vector<Connection*> activeConnections;
std::unique_ptr<DatabaseHandle> dbHandle;
```

## 错误示例

```cpp
// no spaces around binary operators — hard to read
int result=a+b*c;
bool isValid=(x>0)&&(y<maxValue);

// pointer symbol next to variable name (C-style, forbidden)
char *buffer;
const std::string &name;

// mixed style — inconsistent
char* buffer1;       // correct
char *buffer2;       // wrong
char * buffer3;      // wrong (spaces on both sides)

// reference symbol spacing wrong
void process(const DataPacket &packet, ResultWriter &writer);

// function return type spacing wrong
NetworkManager * createManager();

// spaces around unary operators — wrong
if (! isEmpty) {     // no space between ! and operand
    ++ counter;      // no space between ++ and operand
}
```

## 检查方法

### 运算符间距检查
1. 检测缺少空格的二元运算符，正则模式（匹配 `a+b` 这类紧凑写法）：
   ```
   \w\s*([+\-*/%&|^]|[=!<>]=|[<>]{2})\s*\w
   ```
   但需排除：
   - 指针/引用声明中的 `*` 和 `&`（这些由另一下面的规则处理）
   - 数字字面量中的符号
   - 头文件路径和 `#include` 中的符号
   - `operator*`、`operator&` 等函数名中的文字

2. 检测一元运算符误加空格：
   ```
   [!]\s{1,}\w          # ! 后有空格
   \+\+\s{1,}\w         # ++ 后有空格
   \w\s{1,}\+\+         # ++ 前有空格
   ```

### 指针/引用间距检查
3. 检测指针符号紧跟变量名（违规），正则模式：
   ```
   \w\s+\*\s*\w         # type *var — wrong
   \w\s+&\s*\w          # type &var — wrong (注意排除逻辑与)
   ```
   需排除上下文中的乘法和按位与。

4. 验证正确格式（指针符号紧跟类型），正则模式：
   ```
   \w\*\s+\w            # type* var — correct
   \w&\s+\w             # type& var — correct
   ```

5. 对双指针的情况，同样应用此规则：
   ```
   char** ptr;           # correct: char** ptr
   char **ptr;           # wrong: char **ptr
   ```

## 修复指南

### 运算符间距修复
1. 使用 `clang-format` 自动处理（设置 `SpaceBeforeAssignmentOperators: true` 等）。
2. 手动在运算符前后各加一个空格。
3. 移除一元运算符前后的多余空格。

### 指针/引用符号修复

1. **查找**：搜索模式 `\w\s+\*\s*\w` 和 `\w\s+&\s*\w` 定位不规范的指针/引用声明。
2. **替换规则**：
   - `char *x` → `char* x`
   - `const std::string &name` → `const std::string& name`
   - `DataPacket *packet` → `DataPacket* packet`
   - `ResultWriter &writer` → `ResultWriter& writer`
3. **clang-format 配置**：
   ```yaml
   PointerAlignment: Left        # char* x (指针符号紧跟类型)
   ReferenceAlignment: Left      # Type& ref (引用符号紧跟类型)
   ```
4. **注意**：如果同一行声明多个变量，此规则不适用——应避免一行声明多个指针变量：
   ```cpp
   // ambiguous — avoid this entirely
   // char* x, *y;  -- don't do this
   
   // use separate lines instead
   char* x;
   char* y;
   ```

## 审查清单

- [ ] 所有二元运算符前后是否有空格
- [ ] 一元运算符与操作数之间是否无空格
- [ ] 指针符号 `*` 是否紧跟类型名
- [ ] 引用符号 `&` 是否紧跟类型名
- [ ] 同一文件内指针/引用间距风格是否一致
- [ ] 是否一行只声明一个指针变量

## 关联页面

- [[cpp-indentation]]
- [[cpp-line-width]]
- [[cpp-braces]]
- [[cpp-parameter-alignment]]
- [[cpp-typing-conventions]]
