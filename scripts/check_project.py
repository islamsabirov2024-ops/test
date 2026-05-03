import compileall, pathlib, sys
root = pathlib.Path(__file__).resolve().parents[1]
ok = compileall.compile_dir(str(root / 'app'), quiet=1)
print('OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
