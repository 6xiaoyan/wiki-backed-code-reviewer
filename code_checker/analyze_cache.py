import json, os, glob, sys

cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache', 'violations')
if not os.path.exists(cache_dir):
    print("缓存目录不存在")
    sys.exit(1)

files = glob.glob(os.path.join(cache_dir, '*.json'))
print(f"总文件数: {len(files)}")

passed = 0
failed = 0
multi_fail = []

for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if data.get('passed'):
        passed += 1
    else:
        failed += 1
        attempts = data.get('attempts', [])
        if len(attempts) >= 2:
            last = attempts[-1]
            all_same = all(
                a.get('fix_before') == a.get('fix_after')
                for a in attempts
            )
            multi_fail.append({
                'idx': data['index'],
                'rule': data.get('rule_name', '')[:60],
                'attempts': len(attempts),
                'last_score': last.get('score', 0),
                'last_fb': last.get('feedback', '')[:120],
                'last_sg': last.get('suggestion', '')[:120],
                'all_same': all_same,
            })

print(f"passed: {passed}, failed: {failed}")
print()

print(f"=== 失败 >=2 次: {len(multi_fail)} 条 ===")
for m in sorted(multi_fail, key=lambda x: x['last_score'])[:10]:
    print(f"  #{m['idx']}  score={m['last_score']}  attempts={m['attempts']}")
    print(f"        rule: {m['rule']}")
    print(f"        fix_before==fix_after in all attempts: {m['all_same']}")
    print(f"        feedback: {m['last_fb']}")
    print(f"        suggestion: {m['last_sg']}")
    print()

same_count = sum(1 for m in multi_fail if m['all_same'])
print(f"多次失败中 fix_before==fix_after 的: {same_count}/{len(multi_fail)}")
