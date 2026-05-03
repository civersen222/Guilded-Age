path = 'C:/Users/civer/civkings/gui_popups.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: max_production -> production_capacity
content = content.replace('self.city.max_production', 'self.city.production_capacity')

# Fix 2: Remove 'from city import BuildingType, DistrictType' from inside _build (line 64)
content = content.replace('        from city import BuildingType, DistrictType\n', '')

# Fix 3: Fix BuildingType iteration - use BUILDINGS values instead
content = content.replace(
    'for btype in BuildingType:\n            info = btype.value\n            cost = getattr(btype, "cost", 50)\n            options.append((f"🏛 {info}", f"cost: {cost}", btype))',
    'for bname, btype in BUILDINGS.items():\n            options.append((f"🏛 {btype.name}", f"cost: {btype.production_cost}", bname))'
)

# Fix 4: Fix DistrictType iteration - use DISTRICTS values instead
content = content.replace(
    'for dtype in DistrictType:\n            info = dtype.value\n            cost = getattr(dtype, "cost", 100)\n            options.append((f"🏘 {info}", f"cost: {cost}", dtype))',
    'for dname, dtype in DISTRICTS.items():\n            options.append((f"🏘 {dtype.name}", f"cost: {dtype.production_cost}", dname))'
)

# Fix 5: Fix _produce method
old_produce = '''    def _produce(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Pick something to produce.")
            return
        item = self.listbox.get(sel[0])
        self.city.production_queue.append(item)
        self.log_panel.add(f"Producing: {item}")
        self.destroy()'''

new_produce = '''    def _produce(self) -> None:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Pick something to produce.")
            return
        item = self.listbox.get(sel[0]).split('(')[0].strip()
        self.city.production_queue.append(item)
        self.city.current_production = item
        self.destroy()'''

content = content.replace(old_produce, new_produce)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
