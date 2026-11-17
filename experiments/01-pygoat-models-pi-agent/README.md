# 实验 01：六次 pi 审查与官方 DeepSeek 语义评分

三个模型分别做无规则、有规则审查，每种条件一次。A=无规则，B=有规则。当前结论以 [语义评分解读](deepseek-official-semantic/ANALYSIS.md)、[完整分数](deepseek-official-semantic/REPORT.md) 为准。

|模型|无规则F1|有规则F1|有规则覆盖漏洞|
|---|---:|---:|---:|
|MiniMax M3.1 Flash|58.59%|68.30%|46/78|
|GLM-5.3-Flash|65.00%|56.98%|35/78|
|Qwen3.8-Flash-Next|66.25%|66.73%|48/78|

下一阶段暂用 MiniMax 做有规则审查主力，Qwen 做覆盖补查和对照。差异不大，每条件只有一次运行，不能宣称稳定排名。接下来研究的重点见 [后续研究](NEXT_STEPS.md)。

## 输入、输出和评分怎么组织

审查输入为固定 PyGoat 代码快照（253文本文件+5二进制），B组增加9份安全文档。代码与规则按 o200k_base 逐文件合计229,526 token，不是50万或百万上下文实验。源仓库与提交见 [材料清单](../../benchmarks/pygoat/assets.lock.json)；B组实际使用的规则在 [规则副本](../../benchmarks/pygoat/experiment-01-rules/) 中，原文件下载版本和规则实验副本有区别。

六组提示词和输出在 `group-a-no-rules/<模型>/`、`group-b-with-rules/<模型>/`。每组 `runs/r01/` 保存 findings.json、report.md、coverage.json、run.json、uncertain-findings.json。输出是原始结果，不根据评测补报。原始pi会话包含本机信息，公开仓库保存其中汇总出的用量和模型身份，见 [review-usage.json](deepseek-official-semantic/review-usage.json)。

评分顺序如下：

1. 本地程序检查三项：文件存在且路径能对上标准答案；模型报的起始行落在答案范围前后10行内；模型起止行范围至少一行非空源码出现在自己的引用中，比较时忽略空白。
2. 三项同时通过的262条报告交给官方 DeepSeek Flash。每条报告可以有多个附近候选，裁判看到报告、附近源码和答案描述，判断是不是同一问题、代码是否支持；模型名称和CWE编号不参与判断。262条已全部完成。
3. 对语义确认的配对，单独统计 CWE 与答案允许列表的一致性，不影响漏洞分数。

[三项统计明细](location-checker/REPORT.md)与[脚本](location-checker/check_locations.py)可独立使用。评分用 [deepseek_score.py](deepseek-official-semantic/deepseek_score.py)，共用提示词和计算方式在 [judge_common.py](deepseek-official-semantic/judge_common.py)。旧版“列号+整段引用”筛选结果不用于本表；该错误做法已撤回。

## token 与费用

六次审查累计23,816,550 token。按查询到的官方价和报告写明的假设，参考费用约¥14.2710，实际经Token Hub结算的金额尚未取得。

官方DeepSeek评分一次：262条成功请求951,162 token；包含实际重试、且收到了用量的请求共993,111 token，按当时官方高峰价估算US$0.671136。完整分项和限制见 [费用报告](deepseek-official-semantic/BILLING.md)。

## 复用

先用项目脚本下载固定版本材料，再按本机目录运行。标准答案在 RealVuln 仓库 `ground-truth/realvuln-pygoat/ground-truth.json`，不交给被测审查模型。

```powershell
python deepseek-official-semantic/check_locations.py --source "代码快照目录" --ground-truth "ground-truth.json路径" --experiment "." --out "location-results"
python deepseek-official-semantic/deepseek_score.py --source "代码快照目录" --ground-truth "ground-truth.json路径" --experiment "." --out "new-semantic-results"
```

第二条只准备任务。设置进程环境变量 `DEEPSEEK_API_KEY` 后，加 `--execute --workers 16` 才调用官方接口。密钥只从环境读取，结果不保存密钥。已成功的任务会跳过，失败任务可再次运行重试。发布结果直接在对应目录查阅；重新实验使用新输出目录。`python deepseek-official-semantic/build_billing.py` 从保存的用量重新生成费用报告。

结果只代表本次仓库、一次运行和现有模型配置。裁判没有完整仓库检索能力，部分跨文件结论仍有争议；具体样例见 ANALYSIS.md。修复代码不在本轮任务内。
