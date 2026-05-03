import os
for f in ['append_panels.py', 'panels_new.py']:
    if os.path.exists(f):
        os.remove(f)
        print(f'Removed {f}')
