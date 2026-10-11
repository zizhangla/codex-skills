"""Validate an evidence ledger and compute fixed weighted engineering progress.

No semantic evidence certification, training, or simulation is performed.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

WEIGHTS = dict(rules=5, environment=15, data=10, bread=25, pepper=12,
               process=10, random_eval=10, timing=8, submission=5)


def calculate(ledger, root):
    rows = ledger['rows']
    if len(rows) != len(WEIGHTS) or {r['id']: r['weight'] for r in rows} != WEIGHTS:
        raise ValueError('Expected nine fixed work weights; adapt helper only after versioned contract change')
    seen = set()
    output = []
    for row in rows:
        if row['id'] in seen:
            raise ValueError('Duplicate row')
        seen.add(row['id'])
        gates = row['milestones']
        if not gates or sum(g['points'] for g in gates) != 100:
            raise ValueError(f"Milestone points must total 100: {row['id']}")
        gate_ids = set()
        completion = 0
        for gate in gates:
            if gate['id'] in gate_ids or not 0 < gate['points'] <= 100:
                raise ValueError('Duplicate milestone or invalid points')
            gate_ids.add(gate['id'])
            if gate['status'] not in ('passed', 'pending', 'failed', 'unverified'):
                raise ValueError('Unknown milestone status')
            if gate['status'] == 'passed':
                if not gate.get('evidence') or not gate.get('verified_at') or not gate.get('scope'):
                    raise ValueError(f"Evidence, verification time and scope required: {gate['id']}")
                for relative in gate['evidence']:
                    p = (root / relative).resolve()
                    if not p.is_relative_to(root) or not p.is_file():
                        raise ValueError(f"Evidence missing or outside project: {relative}")
                completion += gate['points']
        hours = row['remaining_hours']
        if len(hours) != 2 or not 0 <= hours[0] <= hours[1]:
            raise ValueError('Invalid remaining hour range')
        output.append(dict(id=row['id'], task=row['task'], requirement=row['requirement'],
                           weight=row['weight'], completion=completion, hours=hours,
                           date=row['target_date'], evidence=row['current_evidence'],
                           acceptance=row['acceptance'], gap=row['gap']))
    score = round(sum(r['weight'] * r['completion'] for r in output) / 100, 2)
    return dict(as_of=ledger['verified_at'], rubric_version=ledger['rubric_version'],
                scope=ledger['scope'], official_deadline=ledger['official_deadline'],
                internal_deadline=ledger['internal_deadline'],
                weights_are='预计工作量权重，非组委会评分权重',
                completion_basis='已核查的开发/验收里程碑，非成功率、得分或晋级概率',
                weighted_completion_percent=score,
                remaining_active_work_hours=[sum(r['hours'][i] for r in output) for i in (0, 1)],
                committee_acceptance=ledger['committee_acceptance'], rows=output,
                administrative=ledger['administrative'], blockers=ledger['blockers'],
                next_milestone=ledger['next_milestone'], estimate_note=ledger['estimate_note'])


def render(data):
    lines = ['# 初赛固定验收计划与进度', '',
             f"核查时间：{data['as_of']}（上海时间）；口径：{data['rubric_version']}。",
             f"工程完成度 **{data['weighted_completion_percent']:g}%**；正式比赛验收：{data['committee_acceptance']}。",
             '这是工作量加权的证据里程碑，不是成功率、评分或晋级概率。', '',
             '| 工作项 | 工作量权重 | 完成度 | 剩余有效工时 | 目标日期 | 当前缺口 |',
             '|---|---:|---:|---:|---|---|']
    for r in data['rows']:
        lines.append(f"| {r['task']} | {r['weight']}% | {r['completion']}% | {r['hours'][0]}–{r['hours'][1]}小时 | {r['date']} | {r['gap']} |")
    h = data['remaining_active_work_hours']
    lines += ['', f"预计剩余有效工作：{h[0]}–{h[1]}小时；{data['estimate_note']}", '', '## 要求和证据', '']
    for r in data['rows']:
        lines.append(f"- **{r['task']}**：{r['requirement']}。当前：{r['evidence']}。验收：{r['acceptance']}。")
    lines += ['', '## 行政条件和范围（不计技术百分比）', '']
    for a in data['administrative']:
        lines.append(f"- {a['requirement']}：{a['status']}；{a['note']}")
    lines += ['', '## 阻碍与下一里程碑', '']
    lines += [f"- {b}" for b in data['blockers']]
    lines += ['', data['next_milestone'], '',
              '门槛、分值、证据路径和范围见 [progress-ledger.json](progress-ledger.json)。',
              '公式：Σ(工作量权重×单项完成度)/100。只有passed门槛计分，反证可扣分，历史快照保留。', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--write', action='store_true')
    args = p.parse_args()
    root = args.root.resolve()
    ledger = json.loads((root/'reports/progress-ledger.json').read_text(encoding='utf-8'))
    data = calculate(ledger, root)
    if args.write:
        history = root/'reports/progress-history'
        history.mkdir(exist_ok=True)
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
        snapshot = history/f"{now.strftime('%Y%m%dT%H%M%S%f')}-milestones-v1.json"
        with snapshot.open('x', encoding='utf-8') as stream:
            json.dump(dict(ledger=ledger, report=data), stream, ensure_ascii=False, indent=2)
        (root/'reports/project-plan-progress.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        (root/'reports/初赛验收计划与完成度-最新.md').write_text(render(data), encoding='utf-8')
    print(json.dumps(data, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
