#!/usr/bin/env python3
"""Portable, stdlib-only deterministic personal-memory CLI."""
from __future__ import annotations
import argparse, json, re, sqlite3, sys, unicodedata, uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY,name TEXT NOT NULL,norm TEXT NOT NULL,type TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(norm,type));
CREATE TABLE IF NOT EXISTS aliases(norm TEXT NOT NULL,entity_id TEXT NOT NULL REFERENCES entities(id),PRIMARY KEY(norm,entity_id));
CREATE TABLE IF NOT EXISTS facts(id TEXT PRIMARY KEY,subject_id TEXT NOT NULL REFERENCES entities(id),predicate TEXT NOT NULL,value_json TEXT NOT NULL,context_key TEXT NOT NULL,status TEXT NOT NULL,confidence REAL NOT NULL,source TEXT NOT NULL,observed_at TEXT NOT NULL,valid_from TEXT NOT NULL,valid_to TEXT,supersedes_id TEXT REFERENCES facts(id));
CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,fact_id TEXT NOT NULL REFERENCES facts(id),source TEXT NOT NULL,observed_at TEXT NOT NULL,confidence REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_alias ON aliases(norm); CREATE INDEX IF NOT EXISTS ix_current ON facts(subject_id,predicate,context_key,status); CREATE INDEX IF NOT EXISTS ix_time ON facts(valid_from,valid_to,status);
"""
def norm(s): return re.sub(r"\s+", " ", unicodedata.normalize("NFKC",s).casefold().strip())
def now(): return datetime.now(timezone.utc).isoformat()
def emit(x): print(json.dumps(x, ensure_ascii=False, indent=2, default=str))
def db(path):
    Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(Path(path).expanduser(),isolation_level=None); con.row_factory=sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA busy_timeout=5000"); con.executescript(SCHEMA); return con
def entity(con, name, kind=None):
    key=norm(name); sql="SELECT DISTINCT e.* FROM entities e LEFT JOIN aliases a ON a.entity_id=e.id WHERE e.norm=? OR a.norm=?"; args=[key,key]
    if kind: sql += " AND e.type=?"; args.append(kind)
    rows=con.execute(sql,args).fetchall()
    if not rows: raise ValueError(f"unknown entity: {name}")
    if len(rows)>1: raise ValueError(f"ambiguous entity: {name}; matches {[r['name'] for r in rows]}")
    return rows[0]
def show(con,row,why):
    subject=con.execute("SELECT name,type FROM entities WHERE id=?",(row['subject_id'],)).fetchone()
    return {"id":row['id'],"subject":{"name":subject['name'],"type":subject['type']},"predicate":row['predicate'],"value":json.loads(row['value_json']),"context":row['context_key'],"status":row['status'],"confidence":row['confidence'],"source":row['source'],"observed_at":row['observed_at'],"valid_from":row['valid_from'],"valid_to":row['valid_to'],"supersedes_id":row['supersedes_id'],"why_matched":why}
def parse_value(value):
    try: return json.loads(value)
    except json.JSONDecodeError: return value
def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",required=True); sub=p.add_subparsers(dest="cmd",required=True)
    ep=sub.add_parser("entity"); es=ep.add_subparsers(dest="action",required=True)
    ec=es.add_parser("create"); ec.add_argument("--name",required=True); ec.add_argument("--type",required=True); ec.add_argument("--alias",action="append",default=[])
    er=es.add_parser("resolve"); er.add_argument("--name",required=True); er.add_argument("--type")
    for command in ("remember", "correct"):
        r=sub.add_parser(command); r.add_argument("--subject",required=True); r.add_argument("--predicate",required=True); r.add_argument("--value",required=True); r.add_argument("--context",default="default"); r.add_argument("--confidence",type=float,default=1); r.add_argument("--source",default="user"); r.add_argument("--at")
    for command in ("lookup","history","at"):
        q=sub.add_parser(command); q.add_argument("--subject",required=True); q.add_argument("--predicate",required=True)
        if command=="at": q.add_argument("--time",required=True)
    c=sub.add_parser("changes"); c.add_argument("--from",dest="start",required=True); c.add_argument("--to",dest="end",required=True)
    archive=sub.add_parser("archive"); archive.add_argument("--fact-id",required=True); archive.add_argument("--at"); archive.add_argument("--confirm",choices=["ARCHIVE"],required=True)
    forget=sub.add_parser("forget"); forget.add_argument("--fact-id",required=True); forget.add_argument("--confirm",choices=["DELETE"],required=True)
    a=p.parse_args(); con=db(a.db)
    try:
        if a.cmd=="entity" and a.action=="create":
            with con:
                row=con.execute("SELECT * FROM entities WHERE norm=? AND type=?",(norm(a.name),a.type)).fetchone()
                if not row:
                    eid=str(uuid.uuid4()); con.execute("INSERT INTO entities VALUES(?,?,?,?,?)",(eid,a.name,norm(a.name),a.type,now())); row=con.execute("SELECT * FROM entities WHERE id=?",(eid,)).fetchone()
                for alias in set([a.name,*a.alias]): con.execute("INSERT OR IGNORE INTO aliases VALUES(?,?)",(norm(alias),row['id']))
            emit(dict(row)); return
        if a.cmd=="entity": emit(dict(entity(con,a.name,a.type))); return
        if a.cmd in ("remember", "correct"):
            subject=entity(con,a.subject); value=parse_value(a.value); packed=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False); stamp=a.at or now()
            con.execute("BEGIN IMMEDIATE")
            old=con.execute("SELECT * FROM facts WHERE subject_id=? AND predicate=? AND context_key=? AND status='current'",(subject['id'],a.predicate,a.context)).fetchall()
            same=next((x for x in old if x['value_json']==packed),None)
            if same:
                con.execute("INSERT INTO observations VALUES(?,?,?,?,?)",(str(uuid.uuid4()),same['id'],a.source,stamp,a.confidence)); con.execute("COMMIT"); emit(show(con,same,"duplicate observation")); return
            for x in old: con.execute("UPDATE facts SET status='superseded',valid_to=? WHERE id=?",(stamp,x['id']))
            fid=str(uuid.uuid4()); con.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(fid,subject['id'],a.predicate,packed,a.context,"current",a.confidence,a.source,stamp,stamp,None,old[0]['id'] if old else None)); con.execute("INSERT INTO observations VALUES(?,?,?,?,?)",(str(uuid.uuid4()),fid,a.source,stamp,a.confidence)); con.execute("COMMIT")
            why="correction superseded prior current fact" if a.cmd=="correct" else "new current assertion"
            emit(show(con,con.execute("SELECT * FROM facts WHERE id=?",(fid,)).fetchone(),why)); return
        if a.cmd in ("lookup","history","at"):
            subject=entity(con,a.subject)
            if a.cmd=="lookup": rows=con.execute("SELECT * FROM facts WHERE subject_id=? AND predicate=? AND status='current' ORDER BY valid_from",(subject['id'],a.predicate)).fetchall(); why="current-slot index"
            elif a.cmd=="history": rows=con.execute("SELECT * FROM facts WHERE subject_id=? AND predicate=? ORDER BY valid_from",(subject['id'],a.predicate)).fetchall(); why="entity history index"
            else: rows=con.execute("SELECT * FROM facts WHERE subject_id=? AND predicate=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?) AND status IN ('current','superseded') ORDER BY valid_from",(subject['id'],a.predicate,a.time,a.time)).fetchall(); why="temporal index"
            emit([show(con,x,why) for x in rows]); return
        if a.cmd=="archive":
            con.execute("BEGIN IMMEDIATE"); row=con.execute("SELECT * FROM facts WHERE id=?",(a.fact_id,)).fetchone()
            if not row: raise ValueError(f"unknown fact {a.fact_id}")
            con.execute("UPDATE facts SET status='archived',valid_to=COALESCE(valid_to,?) WHERE id=?",(a.at or now(),a.fact_id)); con.execute("COMMIT")
            emit(show(con,con.execute("SELECT * FROM facts WHERE id=?",(a.fact_id,)).fetchone(),"explicitly archived")); return
        if a.cmd=="forget":
            con.execute("BEGIN IMMEDIATE"); row=con.execute("SELECT id FROM facts WHERE id=?",(a.fact_id,)).fetchone()
            if not row: raise ValueError(f"unknown fact {a.fact_id}")
            con.execute("UPDATE facts SET supersedes_id=NULL WHERE supersedes_id=?",(a.fact_id,)); con.execute("DELETE FROM observations WHERE fact_id=?",(a.fact_id,)); con.execute("DELETE FROM facts WHERE id=?",(a.fact_id,)); con.execute("COMMIT")
            emit({"deleted_fact_id":a.fact_id,"status":"permanently_deleted"}); return
        rows=con.execute("SELECT * FROM facts WHERE observed_at>=? AND observed_at<? ORDER BY observed_at",(a.start,a.end)); emit([show(con,x,"observation time index") for x in rows])
    except Exception as exc:
        if con.in_transaction: con.execute("ROLLBACK")
        print(json.dumps({"error":str(exc)}),file=sys.stderr); sys.exit(2)
if __name__=="__main__": main()
