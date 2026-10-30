#!/usr/bin/env bash
cd "C:/Users/Gonza-PC/AppData/Local/Temp/edgelab-bt" || exit 1
export KAGGLE_AUTH_HEADER_FILE="$HOME/.kaggle_auth_header" EDGELAB_KAGGLE_OWNER=nicolasbutta EDGELAB_KAGGLE_API=https://www.kaggle.com/api/v1 PYTHONIOENCODING=utf-8
L="cvgap-nq cvgap-cfd-nq u1-ym-grilla u1-zonas-avcl-nq u1-zonas-bt2-nq"
for i in $(seq 1 100); do
  pend=0; out=""
  for c in $L; do
    r=$(python tools/kaggle_kernel.py status --slug nicolasbutta/embudo-btt-$c-rep-20250805 2>&1 | tail -1)
    case "$r" in *'"complete"'*) out="$out $c=ok";; *'"error"'*|*cancel*) out="$out $c=ERROR";; *'"code":404'*) out="$out $c=404"; pend=$((pend+1));; *) pend=$((pend+1));; esac
  done
  echo "$(date +%T) pend=$pend $out"; [ $pend -eq 0 ] && exit 0
  sleep 180
done
