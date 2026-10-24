"""Append new_checked.csv to all_checked.csv (columns unioned)."""
import csv,os
from paths import WORKSPACE
os.chdir(WORKSPACE)
old=list(csv.DictReader(open('all_checked.csv'))) if os.path.exists('all_checked.csv') else []
new=list(csv.DictReader(open('new_checked.csv')))
keys=list(dict.fromkeys(k for r in old+new for k in r))
with open('all_checked.csv','w') as fh:
    w=csv.DictWriter(fh,fieldnames=keys); w.writeheader(); w.writerows(old+new)
print(len(old),'+',len(new),'rows')
