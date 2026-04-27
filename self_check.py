import compileall, sys
ok=compileall.compile_dir('app',quiet=1)
print('SELF CHECK:', 'OK' if ok else 'ERROR')
sys.exit(0 if ok else 1)
