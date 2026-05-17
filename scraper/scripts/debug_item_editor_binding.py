# scraper/scripts/debug_item_editor_binding.py
import json
from pathlib import Path

report_path = Path(__file__).resolve().parents[1] / "out" / "poe2db_payload_health_report.json"
report = json.loads(report_path.read_text(encoding="utf-8"))

binding = report.get("itemEditorBinding") or {}
summary = binding.get("summary") or {}

print("Item editor binding summary:")
for key, value in summary.items():
    print(f"- {key}: {value}")

print()
print("Problem classes:")

problem_found = False
for item_class, row in sorted((binding.get("byClass") or {}).items()):
    status = row.get("status")
    if status == "ok":
        continue

    problem_found = True
    print()
    print(f"== {item_class} [{status}] ==")
    print(f"baseOptions: {row.get('baseOptions')}")
    print(f"uniqueOptions: {row.get('uniqueOptions')}")
    print(f"totalItemOptions: {row.get('totalItemOptions')}")
    print(f"resolvedSubtypes: {row.get('resolvedSubtypes')}")
    print(f"editorPools: {row.get('editorPools')}")
    print(f"normalExplicitPools: {row.get('normalExplicitPools')}")
    print(f"optionsWithEditorPools: {row.get('optionsWithEditorPools')}")
    print(f"optionsWithNormalExplicitPools: {row.get('optionsWithNormalExplicitPools')}")

    missing_editor = row.get("missingEditorPoolOptions") or []
    missing_normal = row.get("missingNormalExplicitPoolOptions") or []

    if missing_editor:
        print("missingEditorPoolOptions sample:")
        for item in missing_editor[:10]:
            print(f"  - {item}")

    if missing_normal:
        print("missingNormalExplicitPoolOptions sample:")
        for item in missing_normal[:10]:
            print(f"  - {item}")

excluded = binding.get("excludedClasses") or {}
if excluded:
    print()
    print("Excluded classes:")
    for item_class, row in sorted(excluded.items()):
        print(f"- {item_class}: {row}")

if not problem_found:
    print("No problem classes found.")
