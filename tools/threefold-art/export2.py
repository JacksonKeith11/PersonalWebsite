import json, sys, importlib
# usage: export2.py module out.js key=func ...
mod = importlib.import_module(sys.argv[1])
out = []
for kv in sys.argv[3:]:
    key, fn = kv.split('=')
    g = getattr(mod, fn)()
    used = set(''.join(g.strings())) - {'.'}
    pal = {k: v for k, v in g.pal.items() if k in used}
    missing = used - set(pal)
    assert not missing, (key, missing)
    rows = ',\n'.join("    '" + r + "'" for r in g.strings())
    out.append(f"  {key}: {{ pal: {json.dumps(pal).replace(chr(34), chr(39))}, rows: [\n{rows}] }},")
open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
