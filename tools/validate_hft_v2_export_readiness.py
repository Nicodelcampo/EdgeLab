"""Static guardrails for the audited HFT V2 exporter source."""
from pathlib import Path
import re
p=Path("nt8/HFTZonesNQPureV4_V2.cs");s=p.read_text(encoding="utf-8-sig") if p.exists() else ""
checks={"headless_property":"ModoExportacionPuro" in s,"headless_draw_guard":"if (!ModoExportacionPuro)" in s and "if (ModoExportacionPuro) return;" in s,"tick_buffer_present":"tickBuf" in s and "hft_ticks_v2" in s,"start_tick_seq_set":"zoneStartTickSeq = currentTickSeq" in s,"parameter_sha256_64":False,"generated_class_v2":"cacheHFTZonesNQPureV4_V2" in s}
m=re.search(r'PARAMETER_MANIFEST_SHA256\s*=\s*"([0-9a-fA-F]+)"',s);checks["parameter_sha256_64"]=bool(m and len(m.group(1))==64)
for k,v in checks.items():print(f"{k}: {'PASS' if v else 'FAIL'}")
raise SystemExit(0 if all(checks.values()) else 1)
