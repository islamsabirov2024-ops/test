import ast
from pathlib import Path
bad=[]
for p in Path('.').rglob('*.py'):
    if '__pycache__' in str(p):
        continue
    try:
        ast.parse(p.read_text(encoding='utf-8'))
    except Exception as e:
        bad.append((str(p),str(e)))
if bad:
    print('SELF CHECK FAILED')
    for x in bad: print(x)
    raise SystemExit(1)
print('SELF CHECK OK')
