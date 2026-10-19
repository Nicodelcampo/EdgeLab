#!/bin/sh
set -eu
cat file_inventory_all.csv.gz.b64.part* | base64 -d > file_inventory_all.csv.gz
printf '%s  %s\n' 'be6d317ac7ba23f61416d509796ddfb48714a22b5c5bf3061b00daf6b19f4720' 'file_inventory_all.csv.gz' | sha256sum -c -
gzip -dc file_inventory_all.csv.gz > file_inventory_all.csv
printf '%s  %s\n' '611f2f567bf5da42d74e9bd99d755e56f89a00709e552061134e0506010dbf5e' 'file_inventory_all.csv' | sha256sum -c -
