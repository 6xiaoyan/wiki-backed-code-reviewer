# DeepSeek Flash 重新评分

使用官方 deepseek-flash，思考模式 high，JSON 输出。只对用户指定三项检查同时通过的报告做语义判断。无列号限制，无整段原文限制，不用 CWE 筛选。
三项是：文件存在且与答案文件对上；报告起始行在答案范围前后10行内；报告起止行范围至少一行非空源码出现在自己的引用中（忽略空白）。
语义裁判输入为报告、附近30行源码、可能对应的答案描述，隐藏模型名字及 CWE 编号。same+supported 对应正例计确认；uncertain/insufficient 单列。
参考精确率=确认报告数/全部报告数；召回率=覆盖的不同正例数/78；允许明确的合并报告覆盖多个标签，重复报告不增加召回。这里不是原有一对一计分。
只在附近有参考答案时才请求裁判；没有对应答案不能由此证明报告错误。语义确认仅指给定材料下模型裁判认可，未经人工逐项裁决。

|运行|三项通过|裁判完成|确认报告|覆盖标签|参考精确率|召回率|F1|待确认对|
|---|---|---|---|---|---|---|---|---|
|glm-5.3-flash/A|41/48|41/41|38|43/78|79.17%|55.13%|65.00%|3|
|glm-5.3-flash/B|36/41|36/36|32|35/78|78.05%|44.87%|56.98%|5|
|minimax-m3.1-flash/A|43/47|43/43|36|37/78|76.60%|47.44%|58.59%|9|
|minimax-m3.1-flash/B|50/53|50/50|43|46/78|81.13%|58.97%|68.30%|7|
|qwen-3.8-flash-next/A|42/47|42/42|39|43/78|82.98%|55.13%|66.25%|6|
|qwen-3.8-flash-next/B|50/59|50/50|43|48/78|72.88%|61.54%|66.73%|7|

## CWE 一致性（不影响上表）

|运行|确认配对|主CWE相同|符合允许CWE|
|---|---|---|---|
|glm-5.3-flash/A|43|27/43|36/43|
|glm-5.3-flash/B|35|25/35|29/35|
|minimax-m3.1-flash/A|38|21/38|31/38|
|minimax-m3.1-flash/B|47|31/47|40/47|
|qwen-3.8-flash-next/A|43|24/43|36/43|
|qwen-3.8-flash-next/B|49|25/49|39/49|

## 每个模型加入规则后的变化

**minimax-m3.1-flash**：确认覆盖 37 → 46；F1 58.59% → 68.30%。
新增确认：pygoat-004（reflected_xss，introduction/templates/Lab/XSS/xss_lab_2.html:20）, pygoat-005（reflected_xss，introduction/templates/Lab/XSS/xss_lab_3.html:22）, pygoat-014（missing_authorization，introduction/views.py:837）, pygoat-023（hardcoded_credentials，pygoat/settings.py:171）, pygoat-032（broken_access_control，introduction/views.py:302）, pygoat-040（hardcoded_credentials，dockerized_labs/broken_auth_lab/app.py:11）, pygoat-041（broken_authentication，dockerized_labs/broken_auth_lab/app.py:45）, pygoat-047（hardcoded_credentials，dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8）, pygoat-048（security_misconfiguration，dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:11）, pygoat-049（security_misconfiguration，dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:13）, pygoat-051（hardcoded_credentials，introduction/views.py:831）, pygoat-057（weak_cryptography，dockerized_labs/sensitive_data_exposure/dataexposure/views.py:38）
不再确认：pygoat-019（code_injection）, pygoat-043（security_misconfiguration）, pygoat-059（sensitive_data_exposure）

**glm-5.3-flash**：确认覆盖 43 → 35；F1 65.00% → 56.98%。
新增确认：pygoat-003（reflected_xss，introduction/templates/Lab/XSS/xss_lab.html:27）, pygoat-032（broken_access_control，introduction/views.py:302）, pygoat-055（reflected_xss，introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11）, pygoat-068（log_injection，introduction/views.py:668）
不再确认：pygoat-012（broken_access_control）, pygoat-020（hardcoded_credentials）, pygoat-021（security_misconfiguration）, pygoat-028（hardcoded_credentials）, pygoat-029（weak_cryptography）, pygoat-031（broken_access_control）, pygoat-040（hardcoded_credentials）, pygoat-041（broken_authentication）, pygoat-044（sensitive_data_exposure）, pygoat-051（hardcoded_credentials）, pygoat-056（weak_cryptography）, pygoat-071（sensitive_data_exposure）

**qwen-3.8-flash-next**：确认覆盖 43 → 48；F1 66.25% → 66.73%。
新增确认：pygoat-004（reflected_xss，introduction/templates/Lab/XSS/xss_lab_2.html:20）, pygoat-022（sensitive_data_exposure，pygoat/settings.py:27）, pygoat-041（broken_authentication，dockerized_labs/broken_auth_lab/app.py:45）, pygoat-044（sensitive_data_exposure，dockerized_labs/broken_auth_lab/app.py:91）, pygoat-049（security_misconfiguration，dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:13）, pygoat-052（sensitive_data_exposure，dockerized_labs/sensitive_data_exposure/dataexposure/models.py:6）, pygoat-058（sensitive_data_exposure，dockerized_labs/sensitive_data_exposure/templates/profile.html:216）, pygoat-059（sensitive_data_exposure，introduction/playground/A9/api.py:16）, pygoat-060（hardcoded_credentials，introduction/playground/A9/api.py:17）, pygoat-062（reflected_xss，introduction/templates/Lab/ssrf/ssrf_lab2.html:23）, pygoat-068（log_injection，introduction/views.py:668）
不再确认：pygoat-005（reflected_xss）, pygoat-017（ssti）, pygoat-019（code_injection）, pygoat-057（weak_cryptography）, pygoat-064（weak_cryptography）, pygoat-071（sensitive_data_exposure）

## 模型选择

当前有规则组 F1 最高的是 **minimax-m3.1-flash/B**。作为下一阶段主力候选，依据本轮三项检查与语义判断共同结果；这不是跨项目通用排名。若请求未全部完成，以上数值为确认下界，不应作最终排名。

注意：每条件一次运行、单仓库；裁判只看提供片段，没有主动跨文件搜索。规则组之间没有完整控制实际阅读轨迹。CWE 一致性只统计语义已确认的配对。原来因为严格引用和列号而筛掉报告的 v2 结果不再用于本次推荐。

数据文件：plan.json 保存提示词和全部检查；responses.jsonl 保存每次请求结果和用量；scores.json 保存配对与分数；cwe.csv 单独记录分类一致性。密钥不写入这些文件。
