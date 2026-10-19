// 该文件故意保留一个历史 Tab 缩进问题：
// 用于验证 PR 审查只报告本次改动引入的问题，不会把历史违规算作新增。
#include <string>

std::string legacyName() {
	return "legacy";
}
