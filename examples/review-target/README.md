# 示例审查目标（C++ / Qt / SQLite）

这是 `wiki-backed-code-reviewer` 的最小示例仓库内容，用来演示 PR diff 审查：

- `src/main.cpp` —— 触发一次 PR 修改的入口文件；
- `src/db.h` / `src/db.cpp` —— 使用 SQLCipher 的 SQLite 访问示例（基线上符合规则）；
- `src/widget.h` / `src/widget.cpp` —— 一个小型 Qt 类；
- `src/legacy.cpp` —— **故意保留**一个历史 Tab 缩进问题，用来验证
  “PR 只报本次改动、不把历史问题算作新增”的过滤逻辑；
- `CMakeLists.txt` —— 示例构建文件（不属于审查支持的文件类型，会被明确排除）。

## 演示方式

1. 在基线（`main`）上修改 `src/main.cpp`，例如新增一个函数，
   函数体内使用 **Tab 缩进**（违反“禁止 Tab 缩进”稳定规则）；
2. 提交并创建 PR；
3. Actions 的 analyze 任务会读取 `merge_base → head` 的 diff，
   只把改动文件与改动片段交给审查程序；
4. publish 任务在 PR 中创建/更新一条汇总评论，报告包含
   文件、行号、代码证据、规则 ID、说明与“未执行验证”的修复建议。

把同一个改动再推送一次（或推送新的修复），评论会被更新而不是重复创建。

> 本示例不参与 CI 构建，也不需要 Qt/SQLite 开发库；它只是被审查的数据。
> 请不要把真实凭据放进示例或 PR。
