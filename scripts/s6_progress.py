"""Conta le simulazioni S6 valide su disco. Usato dal monitor notturno."""
import json, glob, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tau2-bench', 'data', 'simulations')
tot = {'llm_agent': 0, 'custom_agent': 0}
for agent in tot:
    for d in glob.glob(os.path.join(ROOT, f's6_{agent}_t*')):
        fp = os.path.join(d, 'results.json')
        if not os.path.exists(fp): continue
        try:
            sims = json.load(open(fp, encoding='utf-8')).get('simulations') or []
            if sims and (sims[0].get('reward_info') or {}).get('reward') is not None:
                tot[agent] += 1
        except Exception:
            pass
print(f"{tot['llm_agent']} {tot['custom_agent']} {tot['llm_agent']+tot['custom_agent']}")
