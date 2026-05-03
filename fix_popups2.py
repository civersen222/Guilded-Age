path = 'C:/Users/civer/civkings/gui_popups.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace lines 65-72 (0-indexed: 64-71)
new_lines = lines[:64]  # Keep lines before the problematic block
new_lines.append('        for bname, btype in BUILDINGS.items():\n')
new_lines.append('            options.append((f"🏛 {btype.name}", f"cost: {btype.production_cost}", bname))\n')
new_lines.append('        for dname, dtype in DISTRICTS.items():\n')
new_lines.append('            options.append((f"🏘 {dtype.name}", f"cost: {dtype.production_cost}", dname))\n')
new_lines.extend(lines[72:])  # Keep lines after the problematic block

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed BuildingType/DistrictType iteration')
