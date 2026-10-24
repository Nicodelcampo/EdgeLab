#!/usr/bin/env bash
# M10: bundles + impulsos por activo/contrato (descubrimiento). Ver MANIFIESTO_M10_MULTIACTIVO_LUXIMB_20261020.md
set -e
REL=D:/edgelab_release_work/release_v4/data; B=viewer/nt8_bridge/bundles; O=docs/research/luximb_parity_20261020/desc_m10; mkdir -p $O
while IFS='|' read inst contrato d0 d1 tick; do
  [ -z "$inst" ] && continue
  c=${contrato#* }; id="${inst}_${c}_M1_LUXIMB"
  [ -f $B/$id.json ] || python -X utf8 tools/luximb_parity/build_luximb_nq_m1_bundle.py $REL/${inst}_ticks.parquet "$contrato" $d0 $d1 $B $tick
  python -X utf8 tools/luximb_parity/luximb_impulsos.py $B/$id.json $O/impA_$id.json --modo inicio --p-rango 50 --min-ini 0 --share-ini 0 --rango-min-rel 1.3 | grep '"marcados"' | sed "s/^/$id A /"
  python -X utf8 tools/luximb_parity/luximb_impulsos.py $B/$id.json $O/impB_$id.json --modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-rel 1.3 --ctrl-modo amplitud | grep -E '"marcados"|"n_control"' | tr -d '\n' | sed "s/^/$id B /"; echo
done <<'LISTA'
MYM|MYM 12-25|20251001|20251215|1.0
MYM|MYM 03-26|20251216|20260316|1.0
GC|GC 12-25|20250805|20251125|0.1
GC|GC 02-26|20251126|20260128|0.1
GC|GC 04-26|20260129|20260327|0.1
6E|6E 09-25|20250805|20250912|0.00005
6E|6E 12-25|20250915|20251212|0.00005
6E|6E 03-26|20251215|20260313|0.00005
6B|6B 09-25|20250804|20250912|0.0001
6B|6B 12-25|20250915|20251212|0.0001
6B|6B 03-26|20251215|20260313|0.0001
6J|6J 09-25|20250805|20250912|0.0000005
6J|6J 12-25|20250915|20251212|0.0000005
6J|6J 03-26|20251215|20260313|0.0000005
MBT|MBT 09-25|20250826|20250926|5.0
MBT|MBT 10-25|20250929|20251031|5.0
MBT|MBT 11-25|20251103|20251128|5.0
MBT|MBT 12-25|20251201|20251224|5.0
MBT|MBT 01-26|20251229|20260130|5.0
MBT|MBT 02-26|20260202|20260227|5.0
MBT|MBT 03-26|20260302|20260327|5.0
LISTA
