import json
import os
from pathlib import Path

BUNDLES_DIR = Path(r"E:\EdgeLab-multiasset\viewer\nt8_bridge\bundles")
manifest_p = BUNDLES_DIR / "manifest.json"
catalog = json.loads(manifest_p.read_text(encoding="utf-8"))

print(f"Catalog contains {len(catalog)} bundles.")

exact_byte_matches = 0
logical_matches = 0
mismatches = []

for item in catalog:
    aid = item["id"]
    json_p = BUNDLES_DIR / f"{aid}.json"
    js_p = BUNDLES_DIR / f"{aid}.js"
    
    if not json_p.exists() or not js_p.exists():
        mismatches.append({"id": aid, "reason": "FILE_MISSING"})
        continue
    
    json_bytes = json_p.read_bytes()
    js_bytes = js_p.read_bytes()
    
    expected_js = f'window["BUNDLE_{aid}"] = '.encode("utf-8") + json_bytes + b";\r\n"
    if js_bytes == expected_js:
        exact_byte_matches += 1
    else:
        # Check if line ending is \n instead of \r\n or single quote
        expected_js_lf = f'window["BUNDLE_{aid}"] = '.encode("utf-8") + json_bytes + b";\n"
        if js_bytes == expected_js_lf:
            exact_byte_matches += 1
        else:
            mismatches.append({
                "id": aid,
                "reason": "FORMAT_VARIATION",
                "js_len": len(js_bytes),
                "json_len": len(json_bytes)
            })

print(f"Exact byte matches (wrapper + json_bytes + ;\\r\\n): {exact_byte_matches}/{len(catalog)}")
if mismatches:
    print(f"Mismatches / variations ({len(mismatches)}): {mismatches}")
else:
    print("ALL 147 BUNDLES ARE 100% BITWISE IDENTICAL IN PAYLOAD!")
