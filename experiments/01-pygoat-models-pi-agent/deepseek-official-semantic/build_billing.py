"""Recompute token totals and published-price estimates from saved usage."""
import collections
import datetime
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    usage=read(BASE/'review-usage.json');prices=read(BASE/'pricing.json');review=[]
    for name,x in usage.items():
        u=x['usage'];p=prices['review'][name.split('/')[0]]
        # pi input excludes cacheRead for MiniMax; gateway logs don't separate cache.
        amount=(u['input']*p['input']+u.get('cacheRead',0)*p['cached']+u['output']*p['output'])/1e6
        review.append({'run':name,**u,'official_price_estimate_cny':amount,'pi_estimate_usd':x.get('pi_estimate_usd')})
    attempts=[json.loads(line) for line in (BASE/'responses.jsonl').read_text(encoding='utf-8').splitlines()]
    latest={r['job_id']:r for r in attempts}
    def total(rows):
        counter=collections.Counter();cost=0
        for r in rows:
            u=r.get('usage') or {}
            counter.update({k:v for k,v in u.items() if type(v)is int})
            counter['reasoning_tokens']+=u.get('completion_tokens_details',{}).get('reasoning_tokens',0)
            if not u:continue
            dt=datetime.datetime.fromtimestamp(r['started'],datetime.timezone.utc)
            peak=dt.weekday()<5 and (1<=dt.hour<4 or 6<=dt.hour<10)
            p=prices['deepseek']['peak' if peak else 'off_peak']
            cost+=(u.get('prompt_cache_hit_tokens',0)*p['cached']+u.get('prompt_cache_miss_tokens',u.get('prompt_tokens',0))*p['input']+u.get('completion_tokens',0)*p['output'])/1e6
        return {'attempts':len(rows),'usage_received':sum(bool(r.get('usage')) for r in rows),'tokens':dict(counter),'estimate_usd':cost}
    billing={'review_runs':review,'review_total_tokens':sum(x['totalTokens'] for x in review),
             'review_official_price_estimate_cny':sum(x['official_price_estimate_cny'] for x in review),
             'deepseek_successful_once':total(list(latest.values())),
             'deepseek_including_retries':total(attempts)}
    (BASE/'billing.json').write_text(json.dumps(billing,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 六次审查与 DeepSeek 评测用量、费用','',
        '以下金额是按2026-11-17核对的官方标准单价计算，不是平台实际扣款账单。GLM/Qwen通过Token Hub调用；网关实际价格、折扣和缓存命中未取得，不以pi中价格为0推断免费。',
        '## 六次审查','',
        '|运行|普通输入token|缓存读取token|输出token|累计token|官方价参考估算/元|',
        '|---|---:|---:|---:|---:|---:|']
    for r in review:md.append(f"|{r['run']}|{r['input']:,}|{r.get('cacheRead',0):,}|{r['output']:,}|{r['totalTokens']:,}|{r['official_price_estimate_cny']:.4f}|")
    md+=['',f"六次合计 **{billing['review_total_tokens']:,} token**，按下述假设计价约 **¥{billing['review_official_price_estimate_cny']:.4f}**。不是完整实际账单。",'',
         'MiniMax：国内官方标准价，输入¥1、输出¥4、缓存读取¥0.1/百万token。pi另记录两轮估算US$0.098704404和US$0.1114633852；美元与人民币价格不同，不能混加或当作真实结算。',
         'GLM：国内官方标准价，输入¥0.8、输出¥2.8、缓存命中¥0.23/百万token。由于网关没有单列缓存，本表将全部input按普通输入计价，未应用促销或订阅。',
         'Qwen：Token Hub模型ID为Qwen3.8-Flash-Next；官方百炼公布的是qwen3.8-flash。本表采用同系列北京/全球公开价（输入¥0.8、输出¥2.7、缓存¥0.1/百万token）做参考估算，**未证明Token Hub别名对应同一付费服务**。缓存未单列，按全额普通输入估算。此项是同系列价格参考，不是假称查到了网关精确账单。',
         '累计token是每次模型请求的用量之和，包括反复传入的历史和缓存，不是代码仓库大小，也不是单次上下文长度。reasoning已另外保存供观察，不再加到output以免重复计费；不同兼容接口计量方式可能不同。','',
         '## DeepSeek 对六组结果评测一次','',
         '一轮需要判断262条报告。下表第一行仅统计每个任务最终成功的一次；第二行包括所有重试及已收到usage的失败回答。','',
         '|范围|请求次数|有usage次数|输入token|其中缓存命中|输出token|合计token|按官方价估算/美元|',
         '|---|---:|---:|---:|---:|---:|---:|---:|']
    for label,key in [('262条成功评分各一次','deepseek_successful_once'),('含实际重试','deepseek_including_retries')]:
        r=billing[key];u=r['tokens'];md.append(f"|{label}|{r['attempts']}|{r['usage_received']}|{u['prompt_tokens']:,}|{u['prompt_cache_hit_tokens']:,}|{u['completion_tokens']:,}|{u['total_tokens']:,}|${r['estimate_usd']:.6f}|")
    md+=['',
         '本轮请求发生在工作日09:15—09:22 UTC，按官方高峰标准价：未命中输入$0.30、缓存输入$0.006、输出$1.20/百万token。输出包括思考用量，不再重复加reasoning。13次连接失败没有收到usage，其可能的服务端用量无法在客户端确认，因此含重试金额也不等于已核对的最终扣款。',
         '本表不包含前面已撤回的Qwen裁判试跑、旧版严格筛选评分费用，也不包含本次整理仓库所用助手费用。',
         '', '## 官方定价来源','']
    for name,p in prices['sources'].items():md.append(f"- [{name}]({p})")
    md+=['','`review-usage.json`保留六次原始用量摘要；`pricing.json`保存所用单价；运行 `python build_billing.py` 重新计算 `billing.json` 和本报告。']
    (BASE/'BILLING.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({'review_tokens':billing['review_total_tokens'],'review_cny_estimate':billing['review_official_price_estimate_cny'],'deepseek':billing['deepseek_including_retries']},ensure_ascii=False))

if __name__=='__main__':main()
