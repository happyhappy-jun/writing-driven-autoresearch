"""Test the unified thesis: Depth-AR's benefit scales with what plain skipping destroys."""
import glob, json
import numpy as np
from scipy.stats import spearmanr
from depth_ar import write_result

rows, seen = [], set()
for f in sorted(glob.glob('/home/lobster/ralph/results/*.json')):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    if 'runs' not in d or 'model' not in d:
        continue
    for k, r in d['runs'].items():
        m = r.get('methods', {})
        if 'depth_ar' not in m or 'avg_acc' not in m.get('dense', {}):
            continue
        key = (d['model'], r['selection'], r['k'])
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            'model': d['model'].split('/')[-1], 'selection': r['selection'], 'k': r['k'],
            'damage_acc': m['dense']['avg_acc'] - m['plain_skip']['avg_acc'],
            'gain_acc': m['depth_ar']['avg_acc'] - m['plain_skip']['avg_acc'],
            'damage_nll': m['plain_skip']['wikitext2_nll'] - m['dense']['wikitext2_nll'],
            'gain_nll': m['plain_skip']['wikitext2_nll'] - m['depth_ar']['wikitext2_nll'],
        })

da = np.array([r['damage_acc'] for r in rows])
ga = np.array([r['gain_acc'] for r in rows])
dn = np.array([r['damage_nll'] for r in rows])
gn = np.array([r['gain_nll'] for r in rows])
ra, pa = spearmanr(da, ga)
rn, pn = spearmanr(dn, gn)

print(f'DAMAGE-AXIS THESIS, tested on all {len(rows)} unique (model, selection, k) runs:')
print(f'  spearman(plain-skip ACC damage, depth_ar ACC gain) = {ra:+.3f}  p={pa:.4g}')
print(f'  spearman(plain-skip NLL damage, depth_ar NLL gain) = {rn:+.3f}  p={pn:.4g}\n')
print('  largest ACC gains:')
for r in sorted(rows, key=lambda x: -x['gain_acc'])[:5]:
    print(f"    {r['model']:12s} {r['selection']:15s} k={r['k']:<2} damage {r['damage_acc']*100:5.1f}pt"
          f" -> gain {r['gain_acc']*100:+5.1f}pt")
print('  smallest damage (nothing to recover):')
for r in sorted(rows, key=lambda x: x['damage_acc'])[:4]:
    print(f"    {r['model']:12s} {r['selection']:15s} k={r['k']:<2} damage {r['damage_acc']*100:5.1f}pt"
          f" -> gain {r['gain_acc']*100:+5.1f}pt")

write_result('/home/lobster/ralph/results/damage_axis.json', {
    'run_id': 'damage_axis', 'round': 5,
    'thesis': 'Depth-AR recovers quality in proportion to what plain skipping destroys. The '
              'two regimes are separated by DAMAGE, not by selection rule.',
    'spearman_acc_damage_vs_acc_gain': {'rho': float(ra), 'p_value': float(pa), 'n': len(rows)},
    'spearman_nll_damage_vs_nll_gain': {'rho': float(rn), 'p_value': float(pn), 'n': len(rows)},
    'rows': rows, 'status': 'complete',
    'notes': 'One row per unique (model, selection, k). Damage and gain are both measured '
             'against plain skip at the identical layer set.',
})
print('\n-> /home/lobster/ralph/results/damage_axis.json')
