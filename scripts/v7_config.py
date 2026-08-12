#!/usr/bin/env python3
from __future__ import annotations
import json
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / 'config' / 'universe.json'

def load_config() -> dict:
    source = json.loads(UNIVERSE.read_text(encoding='utf-8'))
    rows = list(source.get('companies') or [])
    if len(rows) != 142 or len({str(row['code']) for row in rows}) != 142:
        raise RuntimeError('冻结公司范围必须为142家且代码唯一')
    return {'schema':'v75-universe-1','companies':rows,'external_market':source.get('external_market') or []}

if __name__ == '__main__':
    cfg=load_config()
    print(json.dumps({'schema':cfg['schema'],'companies':len(cfg['companies']),'hardware':sum(x.get('scope')=='hardware' for x in cfg['companies']),'application':sum(x.get('scope')=='application' for x in cfg['companies'])},ensure_ascii=False))
