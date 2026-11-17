"""Check the three agreed location/reference conditions without an API call."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re

DEFAULT_SOURCE = Path('D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/pygoat')
DEFAULT_GT = Path('D:/ai_share/langgraph/benchmark-data/pygoat-baseline/judge/realvuln/ground-truth/realvuln-pygoat/ground-truth.json')
DEFAULT_EXPERIMENT = Path('D:/ai_share/langgraph/wiki-backed-code-reviewer/experiments/01-pygoat-models-pi-agent')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def filename(value):
    return value.replace('\\','/').removeprefix('./')

def without_whitespace(value):
    return re.sub(r'\s+', '', value)

def label_locations(entries):
    rows=[]
    for entry in entries:
        for loc in [dict(file=entry['file'], **entry['location'])] + entry.get('acceptable_locations', []):
            rows.append({'label_id':entry['id'], 'file':filename(loc['file']),
                         'start_line':loc.get('start_line'), 'end_line':loc.get('end_line') or loc.get('start_line'),
                         'is_vulnerable':entry['is_vulnerable']})
    return rows

def check_finding(finding, source, locations, tolerance):
    path=filename(finding['path'])
    file_path=source/path
    exists=file_path.is_file()
    file_labels=[x for x in locations if x['file']==path]
    start=finding.get('start',{}).get('line')
    end=finding.get('end',{}).get('line',start)
    candidates=[]
    if exists and isinstance(start,int):
        candidates=[x for x in file_labels if isinstance(x['start_line'],int) and
                    x['start_line']-tolerance <= start <= x['end_line']+tolerance]
    evidence=finding.get('extra',{}).get('metadata',{}).get('code_evidence','')
    evidence=without_whitespace(evidence)
    quoted_lines=[]
    if exists and isinstance(start,int) and isinstance(end,int):
        lines=file_path.read_text(encoding='utf-8').splitlines()
        # Exactly the requested rule: any nonblank source line in the reported
        # interval appears in the reported quote after whitespace removal.
        for number in range(max(1,start), min(len(lines),end)+1):
            actual=without_whitespace(lines[number-1])
            if actual and actual in evidence:
                quoted_lines.append({'line':number,'source':lines[number-1]})
    one=exists and bool(file_labels)
    two=bool(candidates)
    three=bool(quoted_lines)
    return {'finding_id':finding.get('extra',{}).get('metadata',{}).get('finding_id',finding.get('check_id')),
            'file':path,'start_line':start,'end_line':end,
            'file_exists':exists,'file_in_ground_truth':bool(file_labels),
            'check_1_file_exists_and_matches':one,
            'check_2_reported_start_within_10_lines':two,
            'check_3_at_least_one_source_line_in_quote':three,
            'all_three':one and two and three,
            'candidate_locations':candidates,'matching_quoted_lines':quoted_lines}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=DEFAULT_SOURCE)
    parser.add_argument('--ground-truth',type=Path,default=DEFAULT_GT)
    parser.add_argument('--experiment',type=Path,default=DEFAULT_EXPERIMENT)
    parser.add_argument('--run',action='append',help='NAME=path/to/findings.json; repeat for multiple runs')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.run:
        runs=[(name,Path(path)) for name,path in (item.split('=',1) for item in args.run)]
    else:
        runs=[(model+'/'+group,args.experiment/folder/model/'runs/r01/findings.json')
              for model in ('minimax-m3.1-flash','glm-5.3-flash','qwen-3.8-flash-next')
              for group,folder in [('A','group-a-no-rules'),('B','group-b-with-rules')]]
    locations=label_locations(read(args.ground_truth)['findings'])
    summaries=[];details=[]
    for name,path in runs:
        findings=read(path)['results']
        rows=[dict(run=name,**check_finding(f,args.source,locations,10)) for f in findings]
        summary={'run':name,'reports':len(rows)}
        for field in ('file_exists','file_in_ground_truth','check_1_file_exists_and_matches',
                      'check_2_reported_start_within_10_lines','check_3_at_least_one_source_line_in_quote','all_three'):
            summary[field]=sum(r[field] for r in rows)
        summaries.append(summary);details.extend(rows)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'details.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
    (args.out/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.out/'summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    md=['# 文件、行号与引用统计','',
        '1. 文件是否存在，且文件路径能与至少一个标准答案的位置对上。',
        '2. 在同一文件中，模型报告的起始行是否处于某个标准答案起止行范围前后 10 行内。标准答案列出的其他可接受位置同样参与比较。',
        '3. 模型报告的起止行范围内，是否至少有一行非空源码能在模型自己的 code_evidence 中找到；比较时删除双方所有空白字符。',
        '三项分别计数，最后一列统计三项同时通过。每条报告只计一次；同一位置可对应多个答案，明细保留全部可能的答案。',
        '标准答案中的正例和负例均参与位置比较。位置对上不表示漏洞判断正确，后续语义判断再区分。',
        '不检查列号，不要求整段引用逐字连续存在，不按 CWE 筛选。','',
        '|运行|报告数|①文件存在且能对上|②在答案范围前后10行|③范围内至少一行在引用中|三项同时通过|',
        '|---|---:|---:|---:|---:|---:|']
    for r in summaries:
        md.append('|'+ '|'.join(str(r[k]) for k in ('run','reports','check_1_file_exists_and_matches','check_2_reported_start_within_10_lines','check_3_at_least_one_source_line_in_quote','all_three'))+'|')
    md+=['','逐条结果见 details.json；汇总见 summary.csv 和 summary.json。']
    (args.out/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    for r in summaries:print(json.dumps(r,ensure_ascii=False))

if __name__=='__main__':main()
