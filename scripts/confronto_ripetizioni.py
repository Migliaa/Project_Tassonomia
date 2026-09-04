import glob, json, os, sys
from math import comb
BASE = "C:/Users/andre/Desktop/Progetti/tassonomia"
os.chdir(BASE + "/tau2-bench")

def carica(prefisso, agente):
    out = {}
    for d in glob.glob(f"data/simulations/{prefisso}_{agente}_t*"):
        fp = d + "/results.json"
        if not os.path.exists(fp): continue
        s = (json.load(open(fp, encoding="utf-8")).get("simulations") or [{}])[0]
        r = (s.get("reward_info") or {}).get("reward")
        if r is not None:
            out[s["task_id"]] = r
    return out

b1, c1 = carica("s6", "llm_agent"), carica("s6", "custom_agent")
b2, c2 = carica("s9", "llm_agent"), carica("s9", "custom_agent")
comuni = sorted(set(b1) & set(c1) & set(b2) & set(c2), key=int)
print(f"task presenti in TUTTE E QUATTRO le esecuzioni: {len(comuni)}\n")

def conta(d): return sum(1 for t in comuni if d[t] == 1.0)
print(f"{'':<22}{'baseline':>10}{'custom v1':>12}{'divario':>10}")
print("-" * 54)
for et, (b, c) in (("1a esecuzione", (b1, c1)), ("2a esecuzione", (b2, c2))):
    nb, nc = conta(b), conta(c)
    print(f"{et:<22}{nb:>7}/{len(comuni)}{nc:>9}/{len(comuni)}{nc-nb:>+10}")

# media delle due esecuzioni per task: 0, 0.5 o 1
print("\nstabilita' per task (quanti task cambiano esito fra le due esecuzioni):")
for et, (x, y) in (("baseline", (b1, b2)), ("custom v1", (c1, c2))):
    instabili = [t for t in comuni if x[t] != y[t]]
    print(f"  {et:<12} {len(instabili)}/{len(comuni)} instabili: {instabili}")

print("\nMcNemar sulla SECONDA esecuzione (baseline -> custom):")
win = [t for t in comuni if c2[t] > b2[t]]; lose = [t for t in comuni if c2[t] < b2[t]]
n, k = len(win) + len(lose), len(win)
p = min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2**n) if n else 1.0
print(f"  recuperati {sorted(win,key=int)}, persi {sorted(lose,key=int)}")
print(f"  {n} coppie discordanti, p={p:.4f} -> {'significativo' if p<0.05 else 'NON significativo'}")

print("\nCombinando le due esecuzioni (pass rate medio per task):")
mb = sum((b1[t]+b2[t])/2 for t in comuni)/len(comuni)
mc = sum((c1[t]+c2[t])/2 for t in comuni)/len(comuni)
print(f"  baseline  {mb:.3f}\n  custom v1 {mc:.3f}\n  divario   {mc-mb:+.3f}")
