# 2026-10-26 21:23:56 创建
import json, re, sys, os

base = r'D:\Harumakigohan\tmp'
outdir = r'D:\Harumakigohan\manifest'
os.makedirs(outdir, exist_ok=True)

def load(name):
    out = []
    with open(os.path.join(base, name), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out

vids = load('yt_videos.u8.jsonl')

def classify(t):
    if re.search(r'SPOT|\u30af\u30ed\u30b9\u30d5\u30a7\u30fc\u30c9|crossfade|Trailer|Teaser|\u30c6\u30a3\u30b6\u30fc|\u30e1\u30a4\u30ad\u30f3\u30b0|Making', t, re.I):
        return 'promo'
    if re.search(r'Episode|Playing Sister|\u304a\u59c9\u3061\u3083\u3093\u3054\u3063\u3053|Original Anime', t, re.I):
        return 'anime'
    if re.search(r'Live|LIVE|\u30e9\u30a4\u30d6', t):
        return 'live'
    if re.search(r'Self ?Cover|Vocal ver|Vocal \u697d\u66f2|\u30bb\u30eb\u30d5\u30ab\u30d0\u30fc|SelfCover', t, re.I):
        return 'selfcover'
    if re.search(r'feat', t, re.I):
        return 'vocaloid'
    return 'other'

order = [('vocaloid', 'Vocaloid / 合作 MV'), ('selfcover', 'Self Cover\uff08\u672c\u4eba\u6f14\u5531\uff09'), ('anime', '\u539f\u5275\u30a2\u30cb\u30e1'), ('live', 'Live \u7248\u672c'), ('promo', '\u5ba3\u4f1d\u7269\u6599\uff08SPOT / crossfade / teaser\uff09'), ('other', '\u5176\u4ed6')]
groups = {k: [] for k, _ in order}
for v in vids:
    groups[classify(v.get('title') or '')].append(v)

def dur(v):
    s = v.get('duration') or 0
    return '{}:{:02d}'.format(int(s)//60, int(s) % 60)

lines = []
lines.append('# YouTube 官方频道清单\n')
lines.append('- \u9891\u9053\uff1aHarumakiGohan Official')
lines.append('- Channel ID\uff1a`UCgbTJ0Qb1OpA0GEocaJ7qrw`')
lines.append('- URL\uff1ahttps://www.youtube.com/@harumakigohan')
lines.append('- \u62c9\u53d6\u65f6\u95f4\uff1a2026-10-26 21:23:56')
lines.append('- \u89c6\u9891\u603b\u6570\uff1a{}\n'.format(len(vids)))
lines.append('## \u7edf\u8ba1\n')
lines.append('| \u7c7b\u522b | \u6570\u91cf |')
lines.append('|---|---|')
for k, label in order:
    lines.append('| {} | {} |'.format(label, len(groups[k])))
lines.append('')
for k, label in order:
    if not groups[k]:
        continue
    lines.append('## {} ({})\n'.format(label, len(groups[k])))
    lines.append('| # | \u6807\u9898 | \u65f6\u957f | \u64ad\u653e\u91cf | \u94fe\u63a5 |')
    lines.append('|---|---|---|---|---|')
    for i, v in enumerate(groups[k], 1):
        title = (v.get('title') or '').replace('|', '\\|')
        lines.append('| {} | {} | {} | {} | https://www.youtube.com/watch?v={} |'.format(i, title, dur(v), v.get('view_count'), v.get('id')))
    lines.append('')

with open(os.path.join(outdir, 'youtube-channel.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

recs = []
for k, label in order:
    for v in groups[k]:
        recs.append({'_id': v.get('id'), 'title': v.get('title'), 'duration_sec': v.get('duration'), 'view_count': v.get('view_count'), 'category': k, 'url': 'https://www.youtube.com/watch?v=' + str(v.get('id'))})
with open(os.path.join(outdir, 'youtube-channel.json'), 'w', encoding='utf-8') as f:
    json.dump(recs, f, ensure_ascii=False, indent=1)

print('WROTE', os.path.join(outdir, 'youtube-channel.md'))
for k, label in order:
    print('{:<45} {}'.format(label, len(groups[k])))
