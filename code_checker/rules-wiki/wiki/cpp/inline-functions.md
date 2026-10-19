---
domain: cpp
rule_id: cpp-inline-functions
title: 内联函数定义规范
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.2 头文件规范"
status: active
check_method: none
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-templates-in-headers]]
  - [[cpp-forward-declarations]]
  - [[cpp-typing-conventions]]
---

# 内联函数定义规范

## 规则条款

内联函数（`inline`）定义应当放在头文件中，但需谨慎使用。`inline` 关键字的主要作用是允许函数在多个翻译单元中被定义而不违反 ODR（单一定义规则），而不仅是提示编译器进行内联展开。
使用 `inline` 函数的指南：

- 短小的、频繁调用的函数（如 getter/setter、简单运算符重载）适合作为内联函数
- 10 行以上的函数不建议标记为 `inline`
- 包含循环或递归的函数不建议标记为 `inline`
- 虚函数不建议标记为 `inline`（编译器通常忽略此类提示）
- `inline` 函数定义应放在头文件中，否则其他翻译单元无法内联展开

对于在类定义内部直接定义的成员函数，它们隐式地是 `inline` 的，不需要额外添加 `inline` 关键字。
**注意**：此规则为建议性质（`checkability: advisory_only`），不强制要求所有短函数都必须内联，也不强制禁止长函数的内联声明。
## 正确示例

```cpp
// file: geometry/point.h
#ifndef PROJECT_GEOMETRY_POINT_H_
#define PROJECT_GEOMETRY_POINT_H_

namespace geometry {

class Point {
public:
    Point(double x, double y) : m_x(x), m_y(y) {}

    // simple getters — implicitly inline (defined in class body)
    double x() const { return m_x; }
    double y() const { return m_y; }

    // moderately simple — explicitly inline in header
    inline double distanceTo(const Point& other) const {
        double dx = m_x - other.m_x;
        double dy = m_y - other.m_y;
        return std::sqrt(dx * dx + dy * dy);
    }

private:
    double m_x;
    double m_y;
};

// short standalone utility — inline in header, appropriate
inline bool nearlyEqual(double a, double b, double epsilon = 1e-9) {
    return std::abs(a - b) < epsilon;
}

} // namespace geometry

#endif // PROJECT_GEOMETRY_POINT_H_
```

## 错误示例

```cpp
// file: geometry/point.h
#ifndef PROJECT_GEOMETRY_POINT_H_
#define PROJECT_GEOMETRY_POINT_H_

namespace geometry {

class Point {
public:
    // long function with loop — bad candidate for inline in header
    inline bool isInsidePolygon(const std::vector<Point>& polygon) const {
        int count = 0;
        for (size_t i = 0; i < polygon.size(); ++i) {
            const auto& p1 = polygon[i];
            const auto& p2 = polygon[(i + 1) % polygon.size()];
            if ((p1.y() > m_y) != (p2.y() > m_y)) {
                double intersect = (p2.x() - p1.x()) * (m_y - p1.y())
                                 / (p2.y() - p1.y()) + p1.x();
                if (m_x < intersect) {
                    ++count;
                }
            }
        }
        return count % 2 == 1;
    }

private:
    double m_x;
    double m_y;
};

} // namespace geometry

#endif // PROJECT_GEOMETRY_POINT_H_
```

## 检查方法
此规则为建议级别（`advisory_only`），仅提供报告性分析，不阻断构建或审查。检查思路：
1. 识别头文件中的 `inline` 关键字的函数定义以及类内联定义。
2. 对每个内联函数，统计有效代码行数（排除空白和纯注释行）：
   - 超过 10 行的标记为"建议审查"
   - 超过 20 行的标记为"强烈建议拆分"
3. 检测内联函数体中是否包含：
   - `for` / `while` / `do...while` 循环，标记为"不推荐"
   - 递归调用自身，标记为"不推荐"
   - `switch` 语句，标记为"审查"
4. 正则辅助模式：
   - 内联函数定义：`\binline\s+\w[\w\s*&:<>,]*\([^)]*\)\s*(?:const\s*)?\{`
   - 检测循环：`\b(for|while|do)\b`
   - 检测递归（需函数名上下文匹配，正则只能做初步筛选）

## 修复指南

1. 对外部可用的、较长的 `inline` 函数，考虑将实现移到 `.cpp` 文件中，移除 `inline` 声明。
2. 对包含循环或复杂逻辑的内联函数，优先重构为非内联函数。
3. 如果函数确实是热点路径且性能关键，保留内联但添加注释说明原因。
4. 对于模板函数（隐式 inline），如果过大，考虑将部分逻辑提取到非模板辅助函数中。
## 审查清单

- [ ] 内联函数体是否超过 10 行
- [ ] 内联函数是否包含循环或递归
- [ ] 内联函数是否包含 switch 语句
- [ ] 性能关键的内联函数是否有注释说明
- [ ] 是否存在仅用于编译期分发的内联函数（这种情况是合理的）
## 关联页面

- [[cpp-templates-in-headers]]
- [[cpp-forward-declarations]]
- [[cpp-typing-conventions]]
- [[cpp-parameter-alignment]]
