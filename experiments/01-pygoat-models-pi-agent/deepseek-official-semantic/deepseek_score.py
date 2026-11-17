"""Run the agreed three local checks, then semantic judging using DeepSeek."""
import argparse
import concurrent.futures
import csv
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from check_locations import check_finding, label_locations, DEFAULT_GT, DEFAULT_SOURCE, DEFAULT_EXPERIMENT
from judge_common import PROMPT, make_payload, validate_response, metrics, digest

MODELS=['minimax-m3.1-flash','glm-5.3-flash','qwen-3.8-flash-next']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def prepare(out,source=DEFAULT_SOURCE,ground_truth=DEFAULT_GT,experiment=DEFAULT_EXPERIMENT):
    gt=read(ground_truth)['findings']; locs=label_locations(gt);records=[];jobs=[]
    for model in MODELS:
        for group,folder in [('A','group-a-no-rules'),('B','group-b-with-rules')]:
            path=experiment/folder/model/'runs/r01/findings.json'
            for f in read(path)['results']:
                checks=check_finding(f,source,locs,10)
                rec=dict(run=model+'/'+group,**checks,reported_cwes=f['extra']['metadata'].get('cwe',[]),validation={'valid':checks['all_three']})
                if checks['all_three']:
                    ids={x['label_id'] for x in checks['candidate_locations']}
                    payload=make_payload(f,[e for e in gt if e['id'] in ids],30,source)
                    jid=digest({'prompt':PROMPT,'payload':payload,'judge':'deepseek-flash'})
                    jobs.append({'job_id':jid,'payload':payload});rec['job_id']=jid
                records.append(rec)
    plan={'prompt':PROMPT,'ground_truth':gt,'records':records,'jobs':jobs,
          'judge':{'base_url':'https://api.deepseek.com','model':'deepseek-flash','thinking':{'type':'enabled'},'reasoning_effort':'high','max_tokens':8192,'response_format':{'type':'json_object'}},
          'rules':{'line_tolerance':10,'source_radius':30,'three_checks':'check_locations.py; no columns, CWE, or full-quote match'}}
    save(out/'plan.json',plan);return plan

def call(job,key,config):
    body={k:v for k,v in config.items() if k!='base_url'}
    body['messages']=[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(job['payload'],ensure_ascii=False)}]
    request=urllib.request.Request(config['base_url']+'/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    result={'job_id':job['job_id'],'status':'error','started':time.time(),'request_config':config}
    try:
        with urllib.request.urlopen(request,timeout=180) as r:response=json.load(r)
        message=response['choices'][0]['message'];content=message.get('content','')
        result.update(raw_response=content,reasoning=message.get('reasoning_content'),usage=response.get('usage'),response_model=response.get('model'),finish_reason=response['choices'][0].get('finish_reason'))
        result['assessments']=validate_response(content,[x['id'] for x in job['payload']['candidates']]);result['status']='ok'
    except urllib.error.HTTPError as e:
        result['error']=f'HTTP {e.code}'
    except Exception as e:result['error']=type(e).__name__+': '+str(e)
    result['seconds']=time.time()-result['started'];return result

def report(out,plan,responses):
    scores={};cwes=[];gt={e['id']:e for e in plan['ground_truth']}
    for run in sorted({r['run'] for r in plan['records']}):
        recs=[r for r in plan['records'] if r['run']==run];s=metrics(recs,responses,plan['ground_truth'])
        s['checks']={name:sum(r[name] for r in recs) for name in ('check_1_file_exists_and_matches','check_2_reported_start_within_10_lines','check_3_at_least_one_source_line_in_quote','all_three')}
        s['jobs']=sum('job_id'in r for r in recs);s['completed']=sum(responses.get(r.get('job_id'),{}).get('status')=='ok' for r in recs)
        byid={r['finding_id']:r for r in recs}
        for fid,gid in s['accepted_pairs']:
            reported=byid[fid]['reported_cwes'];e=gt[gid]
            cwes.append({'run':run,'finding_id':fid,'gt_id':gid,'reported_cwes':';'.join(reported),'primary_cwe':e['primary_cwe'],'exact_primary':e['primary_cwe'] in reported,'acceptable':bool(set(reported)&set(e['acceptable_cwes']))})
        scores[run]=s
    save(out/'scores.json',scores)
    with (out/'cwe.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['run','finding_id','gt_id','reported_cwes','primary_cwe','exact_primary','acceptable']);w.writeheader();w.writerows(cwes)
    md=['# DeepSeek Flash 重新评分','',
        '使用官方 deepseek-flash，思考模式 high，JSON 输出。只对用户指定三项检查同时通过的报告做语义判断。无列号限制，无整段原文限制，不用 CWE 筛选。',
        '三项是：文件存在且与答案文件对上；报告起始行在答案范围前后10行内；报告起止行范围至少一行非空源码出现在自己的引用中（忽略空白）。',
        '语义裁判输入为报告、附近30行源码、可能对应的答案描述，隐藏模型名字及 CWE 编号。same+supported 对应正例计确认；uncertain/insufficient 单列。',
        '参考精确率=确认报告数/全部报告数；召回率=覆盖的不同正例数/78；允许明确的合并报告覆盖多个标签，重复报告不增加召回。这里不是原有一对一计分。',
        '只在附近有参考答案时才请求裁判；没有对应答案不能由此证明报告错误。语义确认仅指给定材料下模型裁判认可，未经人工逐项裁决。','',
        '|运行|三项通过|裁判完成|确认报告|覆盖标签|参考精确率|召回率|F1|待确认对|',
        '|---|---|---|---|---|---|---|---|---|']
    for run,s in scores.items():
        md.append(f"|{run}|{s['checks']['all_three']}/{s['reports']}|{s['completed']}/{s['jobs']}|{s['confirmed_reports']}|{s['covered_labels']}/78|{s['reference_precision']:.2%}|{s['recall']:.2%}|{s['f1']:.2%}|{s['pending_pairs']}|")
    md+=['','## CWE 一致性（不影响上表）','', '|运行|确认配对|主CWE相同|符合允许CWE|','|---|---|---|---|']
    for run in scores:
        rows=[r for r in cwes if r['run']==run];n=len(rows)
        md.append(f"|{run}|{n}|{sum(r['exact_primary'] for r in rows)}/{n}|{sum(r['acceptable'] for r in rows)}/{n}|")
    md+=['','## 每个模型加入规则后的变化','']
    for model in MODELS:
        a,b=scores[model+'/A'],scores[model+'/B'];added=set(b['covered_ids'])-set(a['covered_ids']);lost=set(a['covered_ids'])-set(b['covered_ids'])
        md.append(f"**{model}**：确认覆盖 {a['covered_labels']} → {b['covered_labels']}；F1 {a['f1']:.2%} → {b['f1']:.2%}。")
        md.append('新增确认：'+', '.join(f"{i}（{gt[i]['vulnerability_class']}，{gt[i]['file']}:{gt[i]['location']['start_line']}）" for i in sorted(added)))
        md.append('不再确认：'+', '.join(f"{i}（{gt[i]['vulnerability_class']}）" for i in sorted(lost)))
        md.append('')
    best=max((k for k in scores if k.endswith('/B')),key=lambda k:scores[k]['f1'])
    md+=['## 模型选择','',f"当前有规则组 F1 最高的是 **{best}**。作为下一阶段主力候选，依据本轮三项检查与语义判断共同结果；这不是跨项目通用排名。若请求未全部完成，以上数值为确认下界，不应作最终排名。",'',
        '注意：每条件一次运行、单仓库；裁判只看提供片段，没有主动跨文件搜索。规则组之间没有完整控制实际阅读轨迹。CWE 一致性只统计语义已确认的配对。原来因为严格引用和列号而筛掉报告的 v2 结果不再用于本次推荐。',
        '', '数据文件：plan.json 保存提示词和全部检查；responses.jsonl 保存每次请求结果和用量；scores.json 保存配对与分数；cwe.csv 单独记录分类一致性。密钥不写入这些文件。']
    (out/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--workers',type=int,default=16);p.add_argument('--limit',type=int,default=0);p.add_argument('--max-tokens',type=int)
    p.add_argument('--source',type=Path,default=DEFAULT_SOURCE);p.add_argument('--ground-truth',type=Path,default=DEFAULT_GT);p.add_argument('--experiment',type=Path,default=DEFAULT_EXPERIMENT)
    args=p.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    plan=read(out/'plan.json') if (out/'plan.json').exists() else prepare(out,args.source,args.ground_truth,args.experiment)
    responses={};path=out/'responses.jsonl'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            row=json.loads(line);responses[row['job_id']]=row
    if args.execute:
        key=os.environ['DEEPSEEK_API_KEY']
        todo=[j for j in plan['jobs'] if responses.get(j['job_id'],{}).get('status')!='ok']
        if args.limit:todo=todo[:args.limit]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool,path.open('a',encoding='utf-8') as f:
            config=dict(plan['judge'])
            if args.max_tokens:config['max_tokens']=args.max_tokens
            fs=[pool.submit(call,job,key,config) for job in todo]
            for n,future in enumerate(concurrent.futures.as_completed(fs),1):
                row=future.result();responses[row['job_id']]=row;f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();print(f"{n}/{len(todo)} {row['status']}",flush=True)
    report(out,plan,responses)
    print(f"Reports: {len(plan['records'])}; judge requests: {len(plan['jobs'])}; completed: {sum(r['status']=='ok' for r in responses.values())}")

if __name__=='__main__':main()
