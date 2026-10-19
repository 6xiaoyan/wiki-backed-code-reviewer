"""
deterministic_checker — 确定性正则检查节点。

核心设计变更（相对旧架构）：
  旧：LLM 在 ReAct 循环中"决定"调用 check_header_guard 等工具，
      可能遗忘、漏调、被 L4 压缩打断检查计划。
  新：Python 主流程对所有文件强制执行所有正则检查，
      结果写入 deterministic_violations（must_keep=True），
      LLM 无权删除或覆盖这些违规。

位于 repo_scanner 之后、四路 checker agent 扇出之前。
纯 Python 执行，零 LLM 调用，零 token 消耗。

与 coverage ledger 联动：
  - 每执行一个检查 → mark_check_completed(ledger, file, check)
  - 全部完成后 → assert_coverage_complete(ledger) 验证无遗漏
"""

import os
from code_checker.state import AgentState
from code_checker.coverage import (
    build_coverage_ledger,
    mark_check_completed,
    assert_coverage_complete,
)
from code_checker.config import (
    CXX_EXTENSIONS, QT_SPECIAL_EXTENSIONS, QT_MARKERS, SQLITE_MARKERS,
)


def _get_file_content(file_path: str, file_contents: dict) -> str | None:
    """获取文件内容（优先精确匹配，其次文件名匹配）。"""
    if file_path in file_contents:
        return file_contents[file_path]
    for fp, content in file_contents.items():
        if os.path.basename(fp) == file_path or file_path in fp:
            return content
    return None


def _run_deterministic_checks(
    file_list: list[str],
    file_contents: dict[str, str],
    ledger: dict | None = None,
) -> list[dict]:
    """对所有文件强制执行所有确定性正则检查。

    每个检查函数直接内联（不通过 @tool 装饰器），
    确保结果完全由 Python 控制，不经过 LLM。

    Returns:
        violations with must_keep=True and source_kind="deterministic"
    """
    import re
    violations: list[dict] = []

    def _add(violation: dict, check_name: str) -> None:
        """标准化记录一条违规。"""
        violation["source_kind"] = "deterministic"
        violation["must_keep"] = True
        violation["check_id"] = check_name
        violations.append(violation)

    for fp in file_list:
        ext = os.path.splitext(fp)[1].lower()
        content = file_contents.get(fp, "")
        if not content:
            continue
        lines = content.split("\n")

        # ================================================================
        # C++ 通用检查（所有 .cpp/.h/.hpp/.cc）
        # ================================================================
        if ext not in CXX_EXTENSIONS:
            continue

        # ── check_tab_indentation ──
        if ledger:
            mark_check_completed(ledger, fp, "check_tab_indentation")
        for i, line in enumerate(lines, 1):
            if "\t" in line:
                _add({
                    "file": fp, "line": i, "rule": "禁止 Tab 缩进",
                    "severity": "critical",
                    "current": line.strip()[:120],
                    "expected": "将 Tab 替换为 4 个空格",
                    "reason": f"第 {i} 行包含 Tab 字符",
                    "source": "cpp",
                }, "check_tab_indentation")

        # ── check_line_width (C++ = 100) ──
        if ledger:
            mark_check_completed(ledger, fp, "check_line_width")
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip("\r")
            if len(stripped) > 100:
                _add({
                    "file": fp, "line": i, "rule": "行宽 ≤ 100 字符",
                    "severity": "warning",
                    "current": stripped[:120],
                    "expected": "将超长行拆分为多行",
                    "reason": f"第 {i} 行宽度 {len(stripped)} 字符，超过 100 限制",
                    "source": "cpp",
                }, "check_line_width")

        # ── check_define_macro ──
        if ledger:
            mark_check_completed(ledger, fp, "check_define_macro")
        define_re = re.compile(r"^\s*#define\s+(\w+)\s+(.*)")
        prev_line = ""
        for i, line in enumerate(lines, 1):
            m = define_re.match(line)
            if not m:
                prev_line = line
                continue
            if re.match(r"^\s*#ifndef\s+", prev_line):
                prev_line = line
                continue
            prev_line = line
            _add({
                "file": fp, "line": i, "rule": "禁止 #define 常量/函数",
                "severity": "warning",
                "current": line.strip(),
                "expected": "使用 constexpr/const 替代",
                "reason": f"第 {i} 行用 #define 定义 '{m.group(1)}'",
                "source": "cpp",
            }, "check_define_macro")

        # ── check_c_style_array ──
        if ledger:
            mark_check_completed(ledger, fp, "check_c_style_array")
        c_array_re = re.compile(
            r"\b(char|int|float|double|long|short|bool|wchar_t|"
            r"unsigned|signed|size_t|uint\d+_t|int\d+_t)\s+"
            r"[\w*&:<>\s]+\s*\[[^\]]*\]\s*[;=]"
        )
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            if "main(" in stripped and "argv" in stripped:
                continue
            if "std::array" in line or "operator[]" in line:
                continue
            if c_array_re.search(line):
                _add({
                    "file": fp, "line": i, "rule": "禁止 C 风格数组",
                    "severity": "warning",
                    "current": stripped,
                    "expected": "使用 std::array / std::vector",
                    "reason": f"第 {i} 行使用了 C 风格数组声明",
                    "source": "cpp",
                }, "check_c_style_array")

        # ── check_throw_spec ──
        if ledger:
            mark_check_completed(ledger, fp, "check_throw_spec")
        for i, line in enumerate(lines, 1):
            if re.search(r"throw\s*\(\s*\)", line):
                _add({
                    "file": fp, "line": i, "rule": "禁止 throw() 异常规范",
                    "severity": "warning",
                    "current": line.strip(),
                    "expected": "使用 noexcept 替代",
                    "reason": f"第 {i} 行使用了 throw() 动态异常规范",
                    "source": "cpp",
                }, "check_throw_spec")

        # ── check_default_lambda_capture ──
        if ledger:
            mark_check_completed(ledger, fp, "check_default_lambda_capture")
        default_cap_re = re.compile(r"\[\=\]|\[\&\]")
        for i, line in enumerate(lines, 1):
            if default_cap_re.search(line):
                if re.search(r"\[\=\s*,\s*&?\w+\]", line) or re.search(r"\[\&\s*,\s*\w+\]", line):
                    continue
                _add({
                    "file": fp, "line": i, "rule": "禁止默认 lambda 捕获",
                    "severity": "critical",
                    "current": line.strip(),
                    "expected": "显式列出每个捕获变量",
                    "reason": f"第 {i} 行 lambda 使用默认捕获",
                    "source": "cpp",
                }, "check_default_lambda_capture")

        # ── check_reinterpret_cast ──
        if ledger:
            mark_check_completed(ledger, fp, "check_reinterpret_cast")
        for i, line in enumerate(lines, 1):
            if re.search(r"\breinterpret_cast\b", line):
                _add({
                    "file": fp, "line": i, "rule": "禁止 reinterpret_cast",
                    "severity": "critical",
                    "current": line.strip(),
                    "expected": "使用 static_cast 或标记 NOLINT",
                    "reason": f"第 {i} 行使用了 reinterpret_cast",
                    "source": "cpp",
                }, "check_reinterpret_cast")

        # ── check_virtual_override ──
        if ledger:
            mark_check_completed(ledger, fp, "check_virtual_override")
        for i, line in enumerate(lines, 1):
            if re.search(r"\bvirtual\b.*\boverride\b", line):
                _add({
                    "file": fp, "line": i, "rule": "override 不重复 virtual",
                    "severity": "warning",
                    "current": line.strip(),
                    "expected": "删除 virtual，保留 override",
                    "reason": f"第 {i} 行 override 重复写了 virtual",
                    "source": "cpp",
                }, "check_virtual_override")

        # ── check_c_variadic ──
        if ledger:
            mark_check_completed(ledger, fp, "check_c_variadic")
        c_variadic_re = re.compile(r"(?<=[,\(])\s*\.\.\.\s*(?=\))")
        for i, line in enumerate(lines, 1):
            if "catch" in line or "template" in line:
                continue
            if c_variadic_re.search(line):
                _add({
                    "file": fp, "line": i, "rule": "禁止 C 风格 ... 可变参数",
                    "severity": "warning",
                    "current": line.strip(),
                    "expected": "使用模板参数包替代",
                    "reason": f"第 {i} 行使用了 C 风格可变参数",
                    "source": "cpp",
                }, "check_c_variadic")

        # ── 头文件专项：check_header_guard ──
        if ext in (".h", ".hpp"):
            if ledger:
                mark_check_completed(ledger, fp, "check_header_guard")
            guard_re = re.compile(
                r"^#ifndef\s+([A-Z][A-Z0-9]*(?:_[A-Z][A-Z0-9]*)+_H_)\s*$"
            )
            ifndef_line = -1
            ifndef_name = ""
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                    continue
                if stripped.startswith("#ifndef"):
                    m = guard_re.match(stripped)
                    if m:
                        ifndef_name = m.group(1)  # 完整宏名，如 PROJECT_MODULE_FILE_H_
                    else:
                        _add({
                            "file": fp, "line": i + 1,
                            "rule": "头文件保护宏格式",
                            "severity": "critical",
                            "current": stripped,
                            "expected": "格式: #ifndef PROJECT_MODULE_FILENAME_H_",
                            "reason": "保护宏格式不正确",
                            "source": "cpp",
                        }, "check_header_guard")
                    ifndef_line = i
                    break

            if ifndef_line >= 0:
                for i in range(ifndef_line + 1, min(ifndef_line + 4, len(lines))):
                    stripped = lines[i].strip()
                    if not stripped or stripped.startswith("//"):
                        continue
                    if stripped.startswith("#define"):
                        parts = stripped.split()
                        if len(parts) >= 2 and ifndef_name and parts[1] != ifndef_name:
                            _add({
                                "file": fp, "line": i + 1,
                                "rule": "头文件保护宏格式",
                                "severity": "critical",
                                "current": stripped,
                                "expected": f"#define {ifndef_name}",
                                "reason": f"#define 与 #ifndef '{ifndef_name}' 不匹配",
                                "source": "cpp",
                            }, "check_header_guard")
                        break

            # ── 头文件专项：check_using_namespace_in_header ──
            if ledger:
                mark_check_completed(ledger, fp, "check_using_namespace_in_header")
            for i, line in enumerate(lines, 1):
                if re.search(r"using\s+namespace\s+\w+", line):
                    _add({
                        "file": fp, "line": i,
                        "rule": "头文件禁止 using namespace",
                        "severity": "critical",
                        "current": line.strip(),
                        "expected": "将 using namespace 移至 .cpp 文件",
                        "reason": f"头文件第 {i} 行包含 using namespace",
                        "source": "cpp",
                    }, "check_using_namespace_in_header")

        # ================================================================
        # Qt 检查
        # ================================================================
        is_qt = False
        if ext in QT_SPECIAL_EXTENSIONS:
            is_qt = True
        elif ext in CXX_EXTENSIONS and QT_MARKERS.search(content):
            is_qt = True

        if is_qt:
            # ── check_qt_include_dot_h ──
            if ledger:
                mark_check_completed(ledger, fp, "check_qt_include_dot_h")
            qt_include_re = re.compile(r'#include\s*<Q\w+\.h\s*>')
            for i, line in enumerate(lines, 1):
                if qt_include_re.search(line):
                    _add({
                        "file": fp, "line": i,
                        "rule": "Qt include 不加 .h",
                        "severity": "warning",
                        "current": line.strip(),
                        "expected": "去掉 .h 后缀",
                        "reason": f"第 {i} 行 Qt include 带了 .h 后缀",
                        "source": "qt",
                    }, "check_qt_include_dot_h")

            # ── check_qt_signal_name ──
            if ledger:
                mark_check_completed(ledger, fp, "check_qt_signal_name")
            signal_re = re.compile(r"\b\w*[Ss]ignal\w*\s*\(")
            in_signals = False
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if re.match(r"^\s*signals\s*:\s*$", line):
                    in_signals = True
                    continue
                if in_signals and re.match(
                    r"^\s*(public|private|protected)\s+slots?\s*:\s*$", line
                ):
                    in_signals = False
                    continue
                if in_signals and signal_re.search(stripped):
                    _add({
                        "file": fp, "line": i,
                        "rule": "信号名禁含 signal",
                        "severity": "warning",
                        "current": stripped,
                        "expected": "重命名，去掉 'signal' 字样",
                        "reason": f"第 {i} 行信号名包含 'signal'",
                        "source": "qt",
                    }, "check_qt_signal_name")

            # ── check_qt_slot_name ──
            if ledger:
                mark_check_completed(ledger, fp, "check_qt_slot_name")
            slot_re = re.compile(r"\b\w*[Ss]lot\w*\s*\(")
            in_slots = False
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if re.match(r"^\s*(public|private|protected)\s+slots?\s*:\s*$", line):
                    in_slots = True
                    continue
                if in_slots and re.match(r"^\s*signals\s*:\s*$", line):
                    in_slots = False
                    continue
                if in_slots and slot_re.search(stripped):
                    _add({
                        "file": fp, "line": i,
                        "rule": "槽名禁含 slot",
                        "severity": "warning",
                        "current": stripped,
                        "expected": "重命名，去掉 'slot' 字样",
                        "reason": f"第 {i} 行槽名包含 'slot'",
                        "source": "qt",
                    }, "check_qt_slot_name")

        # ================================================================
        # SQLite 检查
        # ================================================================
        if ext in CXX_EXTENSIONS and SQLITE_MARKERS.search(content):
            # ── check_sqlite_pragma_key ──
            if ledger:
                mark_check_completed(ledger, fp, "check_sqlite_pragma_key")
            if "PRAGMA key" not in content and "pragma key" not in content:
                _add({
                    "file": fp, "line": 1,
                    "rule": "SQLite 必须使用 SQLCipher 加密",
                    "severity": "critical",
                    "current": "（未找到 PRAGMA key 设置）",
                    "expected": "执行 PRAGMA key = '...' 设置加密密钥",
                    "reason": "文件中未找到 PRAGMA key 加密设置",
                    "source": "sqlite",
                }, "check_sqlite_pragma_key")

            # ── check_sqlite_kdf ──
            if ledger:
                mark_check_completed(ledger, fp, "check_sqlite_kdf")
            if "cipher_default_kdf_iter" not in content:
                _add({
                    "file": fp, "line": 1,
                    "rule": "SQLite KDF 迭代数 ≥ 256000",
                    "severity": "critical",
                    "current": "（未找到 cipher_default_kdf_iter）",
                    "expected": "执行 PRAGMA cipher_default_kdf_iter = 256000",
                    "reason": "未设置 KDF 迭代次数",
                    "source": "sqlite",
                }, "check_sqlite_kdf")
            else:
                m = re.search(r"cipher_default_kdf_iter\s*=\s*(\d+)", content)
                if m and int(m.group(1)) < 256000:
                    _add({
                        "file": fp, "line": 1,
                        "rule": "SQLite KDF 迭代数 ≥ 256000",
                        "severity": "warning",
                        "current": f"cipher_default_kdf_iter = {m.group(1)}",
                        "expected": "cipher_default_kdf_iter = 256000",
                        "reason": f"KDF 迭代数 {m.group(1)} 低于要求的 256000",
                        "source": "sqlite",
                    }, "check_sqlite_kdf")

    return violations


def deterministic_checker(state: AgentState) -> dict:
    """确定性检查器节点 — 对所有文件强制执行所有正则规则。

    位于 repo_scanner 之后、LLM checker agent 扇出之前。
    零 LLM 调用，零 token 消耗，纯粹 Python 正则执行。

    产出:
      - deterministic_violations: 确定性规则发现的违规（must_keep=True）
      - coverage_ledger: 覆盖率账本（completed_checks 已部分填充）
    """
    print("  [deterministic_checker] 启动...")

    file_list = state.get("file_list") or []
    file_contents = state.get("file_contents") or {}

    if not file_list:
        print("  [deterministic_checker] 无文件，跳过")
        return {
            "deterministic_violations": [],
            "coverage_ledger": None,
        }

    # ── 构建覆盖率账本 ──
    ledger = build_coverage_ledger(file_list, file_contents)
    required_count = len(ledger["required_checks"])
    print(f"  [deterministic_checker] {len(file_list)} 个文件, "
          f"{required_count} 条必检项")

    # ── 强制执行所有正则检查 ──
    violations = _run_deterministic_checks(file_list, file_contents, ledger)

    # ── 补充上下文 ──
    from code_checker.utils import enrich_violation_context
    for v in violations:
        enrich_violation_context(v, file_contents)

    # ── 可观测性：记录确定性违规发现事件 ──
    from code_checker.tracer import get_current_tracer
    tracer = get_current_tracer()
    if tracer:
        for i, v in enumerate(violations):
            v["violation_id"] = tracer.record_violation(
                v, "deterministic_checker", i,
            )

    # ── 验证覆盖率 ──
    missing = assert_coverage_complete(ledger)
    coverage_ok = len(missing) == 0

    # 按 category 统计缺失
    missing_by_cat: dict[str, int] = {}
    for m in missing:
        cat = m.get("category", "unknown")
        missing_by_cat[cat] = missing_by_cat.get(cat, 0) + 1

    v_count = len(violations)
    print(f"  [deterministic_checker] 完成: {v_count} 条违规, "
          f"覆盖率 {'✅' if coverage_ok else '❌ ' + str(dict(missing_by_cat))}")

    pipeline_errors = state.get("pipeline_errors") or []
    if not coverage_ok:
        pipeline_errors.append(
            f"Coverage incomplete: {len(missing)}/{required_count} checks missing "
            f"({dict(missing_by_cat)})"
        )

    return {
        "deterministic_violations": violations,
        "coverage_ledger": ledger,
        "pipeline_errors": pipeline_errors,
    }
