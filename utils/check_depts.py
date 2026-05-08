import json
with open('hacettepe_tree_ready.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

depts = [x for x in data if 'Bölüm' in (x.get('category') or '') or 'Anabilim Dalı' in (x.get('category') or '')]
print(f"Total departments: {len(depts)}")
missing = [x for x in depts if not x.get('parent_entity') or x.get('parent_entity') == 'Rektörlük' or x.get('parent_entity') == 'Unknown']
print(f"Departments with missing/root parent: {len(missing)}")

for x in missing[:15]:
    print(f"- {x['entity_name']} | Category: {x['category']}")
