#!/usr/bin/env python3
"""Exchange-calendar based market phase and freshness checks for V7.9.4."""
from __future__ import annotations
import datetime as dt
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo
import exchange_calendars as xcals

CONFIG={
 'china':('XSHG','Asia/Shanghai','A股',20),
 'hk':('XHKG','Asia/Hong_Kong','港股',20),
 'us':('XNYS','America/New_York','美股',15),
 'korea':('XKRX','Asia/Seoul','韩国',20),
}
BEIJING=ZoneInfo('Asia/Shanghai')
UTC=dt.timezone.utc

@lru_cache(None)
def calendar(group:str): return xcals.get_calendar(CONFIG[group][0])

def _dt(value:Any)->dt.datetime|None:
    if not value:return None
    if isinstance(value,dt.datetime): x=value
    else:
        raw=str(value).replace('Z','+00:00')
        # Tencent often YYYYMMDDHHMMSS.
        digits=''.join(c for c in raw if c.isdigit())
        if len(digits)>=14 and ('T' not in raw and '-' not in raw):
            try: x=dt.datetime.strptime(digits[:14],'%Y%m%d%H%M%S')
            except ValueError:return None
        else:
            try:x=dt.datetime.fromisoformat(raw)
            except ValueError:return None
    return x.replace(tzinfo=UTC) if x.tzinfo is None else x.astimezone(UTC)

def _date(value:Any)->dt.date|None:
    if not value:return None
    try:return dt.date.fromisoformat(str(value)[:10])
    except ValueError:return None

def _session_label(group:str, day:dt.date):
    cal=calendar(group)
    try:
        if cal.is_session(str(day)):
            return cal.date_to_session(str(day))
    except Exception:
        pass
    return None

def _sessions(group:str, start:dt.date, end:dt.date):
    cal=calendar(group)
    return list(cal.sessions_in_range(str(start),str(end)))

def expected_completed_session(group:str, now:dt.datetime|None=None)->str|None:
    now=(now or dt.datetime.now(UTC)).astimezone(UTC); tz=ZoneInfo(CONFIG[group][1]); local=now.astimezone(tz); cal=calendar(group)
    sessions=_sessions(group,local.date()-dt.timedelta(days=12),local.date()+dt.timedelta(days=1))
    complete=[]
    for sess in sessions:
        close=cal.session_close(sess).to_pydatetime().astimezone(UTC)
        if close<=now: complete.append(sess)
    return complete[-1].date().isoformat() if complete else None

def phase(group:str, now:dt.datetime|None=None)->dict[str,Any]:
    now=(now or dt.datetime.now(UTC)).astimezone(UTC); _,tzname,label,_=CONFIG[group]; tz=ZoneInfo(tzname); local=now.astimezone(tz);cal=calendar(group)
    sess=_session_label(group,local.date())
    if sess is None:
        state='休市'; open_at=close_at=None
    else:
        open_at=cal.session_open(sess).to_pydatetime().astimezone(tz); close_at=cal.session_close(sess).to_pydatetime().astimezone(tz)
        # A compact pre/post classification; lunch breaks still count as intraday because quotes can be unchanged legitimately.
        if local<open_at: state='盘前'
        elif local<=close_at: state='盘中'
        else: state='盘后'
    return {'market':group,'label':label,'phase':state,'local_timezone':tzname,'local_now':local.isoformat(),
            'beijing_now':now.astimezone(BEIJING).isoformat(),'session_open_local':open_at.isoformat() if open_at else None,
            'session_close_local':close_at.isoformat() if close_at else None,'expected_completed_session':expected_completed_session(group,now)}

def assess(group:str, *, sample_at:Any=None, sample_date:Any=None, realtime:bool=False, file_generated_at:Any=None, now:dt.datetime|None=None)->dict[str,Any]:
    now=(now or dt.datetime.now(UTC)).astimezone(UTC); info=phase(group,now); tz=ZoneInfo(CONFIG[group][1]); threshold=CONFIG[group][3]
    sample=_dt(sample_at); sdate=_date(sample_date) or (sample.astimezone(tz).date() if sample else None); generated=_dt(file_generated_at)
    age=(now-sample).total_seconds()/60 if sample else None; file_age=(now-generated).total_seconds()/60 if generated else None
    expected=info['expected_completed_session']; stale=False; reason=''
    if info['phase']=='盘中':
        if not realtime: stale=True; reason='市场盘中但仍是上一收盘快照'
        elif age is None: stale=True; reason='盘中行情缺少实际采样时间'
        elif age>threshold: stale=True; reason=f'盘中行情已超过{threshold}分钟未更新'
    elif info['phase']=='盘前':
        if expected and (not sdate or sdate.isoformat()!=expected): stale=True; reason='盘前应至少具备上一完整交易日数据'
    else: # 盘后/休市
        if expected and (not sdate or sdate.isoformat()!=expected): stale=True; reason=f'最新完整交易日应为{expected}'
    # A file that was generated long after its sample must never be called a fresh market sample.
    if realtime and file_age is not None and file_age>max(60,threshold*3) and info['phase']=='盘中':
        stale=True; reason=reason or '后台行情文件长时间未重新生成'
    return {**info,'sample_at':sample.astimezone(tz).isoformat() if sample else None,'sample_date':sdate.isoformat() if sdate else None,
            'sample_age_minutes':round(age,1) if age is not None else None,'file_generated_at':generated.astimezone(BEIJING).isoformat() if generated else None,
            'file_age_minutes':round(file_age,1) if file_age is not None else None,'stale':stale,'fresh':not stale,'reason':reason or '新鲜度符合当前市场阶段'}
