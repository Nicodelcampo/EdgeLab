#!/usr/bin/env python3
"""Baja un archivo de un dataset propio de Kaggle con la credencial que el entorno ya inyecta para www.kaggle.com (reintenta ante 429).
  python tools/kaggle_data.py get nicolasbuttaro/edgelab-ticks-es-preholdout ES_06-26_ticks.parquet --out /data/raw/ES
  python tools/kaggle_data.py ls nicolasbuttaro/edgelab-ticks-es-preholdout"""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data_inventory import download,list_files

def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);g=sp.add_parser("get");g.add_argument("dataset");g.add_argument("file");g.add_argument("--out",required=True);l=sp.add_parser("ls");l.add_argument("dataset");a=ap.parse_args()
    owner,slug=a.dataset.split("/")
    if a.cmd=="ls":
        for f in list_files(slug):print(f"{f['bytes']:>14,}  {f['name']}")
    else:
        dest=Path(a.out)/Path(a.file).name;download(slug,a.file,dest,owner);print(dest,dest.stat().st_size)
if __name__=="__main__":main()
