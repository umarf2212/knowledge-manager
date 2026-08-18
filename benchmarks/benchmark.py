"""Repeatable smoke benchmark; numbers depend on hardware and SQLite version."""
from __future__ import annotations
import sys
import time
from pathlib import Path

# Keep the benchmark runnable from a source checkout without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_engine import MemoryEngine

def timed(label, fn):
    start = time.perf_counter(); result = fn(); elapsed = time.perf_counter() - start
    print(f"{label:24} {elapsed * 1000:8.2f} ms")
    return result

def main():
    memory = MemoryEngine(); me = memory.create_entity("Me", "person", ["me"])
    timed("insert 10,000 facts", lambda: [memory.remember(me, f"attribute_{n}", n) for n in range(10_000)])
    timed("current lookup (1000)", lambda: [memory.lookup("me", f"attribute_{n}") for n in range(1000)])
    timed("1,000 updates", lambda: [memory.remember(me, f"attribute_{n}", n + 1) for n in range(1000)])
    timed("history lookup", lambda: memory.history("me", "attribute_0"))
    timed("index rebuild", memory.store.rebuild_indexes)
if __name__ == "__main__": main()
