from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).parent
errors: list[str] = []
exports: dict[str, set[str]] = {}

for path in (ROOT / 'app').rglob('*.py'):
    rel = path.relative_to(ROOT).with_suffix('')
    module = '.'.join(rel.parts)
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except SyntaxError as e:
        errors.append(f'SYNTAX {path}: {e}')
        continue
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    exports[module] = names

for path in (ROOT / 'app').rglob('*.py'):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('app.'):
            if node.module in exports:
                for alias in node.names:
                    if alias.name != '*' and alias.name not in exports[node.module]:
                        errors.append(f'IMPORT {path}: {alias.name} not found in {node.module}')

if errors:
    print('❌ SELF CHECK FAILED')
    print('\n'.join(errors))
    raise SystemExit(1)
print('✅ SELF CHECK OK: syntax/import names passed')
