import os, tempfile, threading, unittest
from datetime import datetime, timezone, timedelta
from memory_engine import MemoryEngine
from memory_engine.resolution import AmbiguousEntityError

UTC = timezone.utc
class MemoryEngineTests(unittest.TestCase):
    def setUp(self):
        self.m = MemoryEngine()
        self.me = self.m.create_entity("Me", "person", ["I", "me"])
        self.tommy = self.m.create_entity("Tommy", "pet", ["my dog"])

    def test_alias_resolution_and_deduplication(self):
        self.assertEqual(self.m.entities.resolve("MY DOG").id, self.tommy.id)
        self.assertEqual(self.m.create_entity("Tommy", "pet").id, self.tommy.id)

    def test_alias_collision_is_not_silently_resolved(self):
        other = self.m.create_entity("Tommy", "person")
        with self.assertRaises(AmbiguousEntityError): self.m.entities.resolve("Tommy")
        self.assertEqual(self.m.entities.resolve("Tommy", "pet").id, self.tommy.id)
        self.assertNotEqual(other.id, self.tommy.id)

    def test_update_supersedes_and_preserves_history(self):
        old = self.m.remember(self.me, "employed_by", "Company A")
        new = self.m.remember(self.me, "employed_by", "Company B")
        self.assertEqual(self.m.lookup("me", "employed_by")[0].value, "Company B")
        history = self.m.history("me", "employed_by")
        self.assertEqual([x.status for x in history], ["superseded", "current"])
        self.assertEqual(history[0].valid_to, new.valid_from)
        self.assertEqual(old.id, history[0].id)

    def test_duplicate_is_an_observation_not_a_second_fact(self):
        self.m.remember(self.tommy, "eats", "Hill's")
        self.m.remember(self.tommy, "eats", "Hill's")
        self.assertEqual(len(self.m.lookup("Tommy", "eats")), 1)
        self.assertEqual(self.m.store.connection.execute("SELECT count(*) FROM observations").fetchone()[0], 2)

    def test_temporal_lookup(self):
        jan = datetime(2026, 1, 1, tzinfo=UTC); feb = datetime(2026, 2, 1, tzinfo=UTC)
        self.m.remember(self.me, "address", "Old", valid_from=jan)
        self.m.remember(self.me, "address", "New", valid_from=feb)
        self.assertEqual(self.m.lookup("me", "address", at=jan + timedelta(days=4))[0].value, "Old")
        self.assertEqual(self.m.lookup("me", "address", at=feb + timedelta(days=4))[0].value, "New")

    def test_relationship_query_and_planner(self):
        self.m.remember(self.tommy, "eats", "Hill's Science Diet")
        self.assertEqual(self.m.answer("What food does Tommy eat?")[0].value, "Hill's Science Diet")
        sister = self.m.create_entity("Sarah", "person")
        self.m.remember(sister, "family_relation", "sister", object_entity=self.me)
        self.assertEqual(self.m.related_to("me", "family_relation")[0].subject.name, "Sarah")

    def test_changed_between(self):
        stamp = datetime(2026, 3, 1, tzinfo=UTC)
        self.m.remember(self.tommy, "name", "Tommy", observed_at=stamp)
        self.assertEqual(len(self.m.changed_between(stamp - timedelta(seconds=1), stamp + timedelta(seconds=1))), 1)

    def test_explicit_lifecycle(self):
        fact = self.m.remember(self.tommy, "favorite_toy", "Ball")
        self.assertEqual(self.m.set_lifecycle(fact.id, "validated").status, "validated")
        self.assertEqual(self.m.set_lifecycle(fact.id, "archived").status, "archived")

    def test_index_rebuild_and_persistence(self):
        handle, path = tempfile.mkstemp(); os.close(handle)
        try:
            one = MemoryEngine(path); pet = one.create_entity("Tommy", "pet"); one.remember(pet, "eats", "Hill's"); one.store.rebuild_indexes()
            self.assertEqual(MemoryEngine(path).lookup("Tommy", "eats")[0].value, "Hill's")
        finally: os.unlink(path)

    def test_concurrent_writes(self):
        handle, path = tempfile.mkstemp(); os.close(handle)
        try:
            MemoryEngine(path).create_entity("Me", "person", ["me"])
            errors = []
            def write(n):
                try: MemoryEngine(path).remember("me", f"preference_{n}", n)
                except Exception as exc: errors.append(exc)
            threads = [threading.Thread(target=write, args=(n,)) for n in range(12)]
            [t.start() for t in threads]; [t.join() for t in threads]
            self.assertEqual(errors, [])
            self.assertEqual(MemoryEngine(path).store.connection.execute("SELECT count(*) FROM facts").fetchone()[0], 12)
        finally: os.unlink(path)

if __name__ == "__main__": unittest.main()
