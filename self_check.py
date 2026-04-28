from pathlib import Path
need = [
    'app/main.py', 'app/db.py', 'app/runner.py', 'app/handlers/builder.py',
    'app/keyboards/common.py', 'app/states.py', 'app/bot_templates/kino_full/bot.py'
]
missing = [p for p in need if not Path(p).exists()]
if missing:
    raise SystemExit('Missing: ' + ', '.join(missing))
print('SELF CHECK OK')
