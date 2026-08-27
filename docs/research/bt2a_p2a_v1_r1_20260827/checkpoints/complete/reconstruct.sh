#!/bin/sh
set -eu
cat checkpoint_inventory_all.csv.gz.b64.part* | base64 -d > checkpoint_inventory_all.csv.gz
printf '%s  %s\n' 'a01026fd94c8ea48f08620764c71a27cfe8ddf89fdb19fcc4f88f537f88d63de' 'checkpoint_inventory_all.csv.gz' | sha256sum -c -
gzip -dc checkpoint_inventory_all.csv.gz > checkpoint_inventory_all.csv
printf '%s  %s\n' '3d916f53f113a788149923cb15fab88e9aeb75772aa85b1d44a7966d590f85da' 'checkpoint_inventory_all.csv' | sha256sum -c -
