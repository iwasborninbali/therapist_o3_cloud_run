import importlib
import os
import sys

os.environ.setdefault("TESTING", "True")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test_project")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import firestore_client

class FakeDoc:
    def __init__(self):
        self.data = None
        self.exists = True
    def get(self):
        return self
    def set(self, data):
        self.data = data

class FakeCollection:
    def __init__(self, db):
        self.db = db
    def document(self, doc_id):
        self.db.last_doc_id = doc_id
        return FakeDoc()

class FakeDB:
    def __init__(self):
        self.last_collection = None
        self.last_doc_id = None
    def collection(self, name):
        self.last_collection = name
        return FakeCollection(self)

def setup_fake_db(monkeypatch, collection_name):
    fake_db = FakeDB()
    monkeypatch.setattr(firestore_client, 'get_db', lambda: fake_db)
    firestore_client.Config.IDEMPOTENCY_COLLECTION = collection_name
    return fake_db

def test_has_processed_update_uses_config(monkeypatch):
    fake_db = setup_fake_db(monkeypatch, 'test_updates')
    firestore_client.has_processed_update(42)
    assert fake_db.last_collection == 'test_updates'


def test_mark_update_processed_uses_config(monkeypatch):
    fake_db = setup_fake_db(monkeypatch, 'test_updates2')
    firestore_client.mark_update_processed(99)
    assert fake_db.last_collection == 'test_updates2'
