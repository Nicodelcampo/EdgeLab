#!/usr/bin/env python3
"""Remove per-price-slice borders from the NT8 bridge viewer.

Volume slices keep their fill and exact vertical consumption marker. Only the
outer top/bottom price boundaries are stroked, so internal price divisions are
not rendered. Idempotent and fail-closed against unexpected viewer changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
OLD='''          // Borde punteado
          ctx.strokeStyle = col;
          ctx.lineWidth = isDead ? 1.0 : 1.3;
          ctx.setLineDash(isDead ? [3, 2] : [5, 3]);
          ctx.strokeRect(drawX0 + 0.5, yMin_s + 0.5, rw_s, h_s);
          ctx.setLineDash([]);
'''
NEW='''          // Dibujar únicamente los límites EXTERIORES de la zona.
          // Las divisiones interiores por nivel conservan el relleno, pero no
          // generan líneas horizontales ni strokeRect por rebanada.
          var isBottomOuterSlice = (slice.startK === 0);
          var isTopOuterSlice = (slice.endK === (cData.nTicks - 1));
          if (isBottomOuterSlice || isTopOuterSlice) {
            ctx.strokeStyle = col;
            ctx.lineWidth = isDead ? 1.0 : 1.3;
            ctx.setLineDash(isDead ? [3, 2] : [5, 3]);
            ctx.beginPath();
            if (isTopOuterSlice) {
              ctx.moveTo(drawX0 + 0.5, yMin_s + 0.5);
              ctx.lineTo(drawX1, yMin_s + 0.5);
            }
            if (isBottomOuterSlice) {
              ctx.moveTo(drawX0 + 0.5, yMax_s - 0.5);
              ctx.lineTo(drawX1, yMax_s - 0.5);
            }
            ctx.stroke();
            ctx.setLineDash([]);
          }
'''
def apply(path:Path)->str:
 text=path.read_text(encoding='utf-8')
 if NEW in text:return 'ALREADY_APPLIED'
 count=text.count(OLD)
 if count!=1:raise RuntimeError(f'expected exactly one volume-slice border block, found {count}')
 path.write_text(text.replace(OLD,NEW),encoding='utf-8');return 'APPLIED'
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--viewer',type=Path,default=Path('viewer/nt8_bridge/index.html'));a=p.parse_args();print(apply(a.viewer));return 0
if __name__=='__main__':raise SystemExit(main())
