path = 'C:/Users/civer/civkings/gui_popups.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_block = [
    '        for bname, btype in BUILDINGS.items():\n',
    '            options.append((f"\U0001f3db {btype.name}", f"cost: {btype.production_cost}", bname))\n',
    '        for dname, dtype in DISTRICTS.items():\n',
    '            options.append((f"\U0001f3d8 {dtype.name}", f"cost: {dtype.production_cost}", dname))\n',
]

lines[64:72] = new_block

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
