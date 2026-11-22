import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database

class LocalDatabaseSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [
            patch.object(database, 'DATA_DIR', root),
            patch.object(database, 'DB_PATH', root / 'test.db'),
            patch.object(database, 'KEY_PATH', root / 'master.key.dpapi'),
            patch.object(database, '_MASTER_KEY', None),
        ]
        for item in self.patches: item.start()
        database.initialize_database()
        self.assertTrue(database.create_user('alice', 'correct-horse-battery')[0])
        self.alice = database.authenticate_user('alice', 'correct-horse-battery')
        self.assertTrue(database.create_user('bob', 'another-secure-password')[0])
        self.bob = database.authenticate_user('bob', 'another-secure-password')

    def tearDown(self):
        for item in reversed(self.patches): item.stop()
        self.temp.cleanup()

    def test_document_content_and_file_are_encrypted_at_rest(self):
        doc_id = database.add_document('private.txt', 'private document text', self.alice['id'], file_data=b'private file bytes', file_type='.txt', file_size=18)
        with database.get_connection() as connection:
            row = connection.execute('SELECT content, file_data FROM documents WHERE id = ?', (doc_id,)).fetchone()
        self.assertNotIn('private document text', row['content'])
        self.assertNotIn(b'private file bytes', bytes(row['file_data']))
        loaded = database.get_document(doc_id, self.alice['id'])
        self.assertEqual(loaded['content'], 'private document text')
        self.assertEqual(loaded['file_data'], b'private file bytes')

    def test_documents_are_isolated_between_users(self):
        doc_id = database.add_document('alice.txt', 'secret', self.alice['id'])
        self.assertEqual(database.get_documents(self.bob['id']), [])
        self.assertIsNone(database.get_document(doc_id, self.bob['id']))
        self.assertEqual(database.get_document_contents(self.bob['id']), [])
        database.delete_document(doc_id, self.bob['id'])
        self.assertIsNotNone(database.get_document(doc_id, self.alice['id']))

    def test_login_locks_after_five_wrong_passwords(self):
        for _ in range(5): self.assertIsNone(database.authenticate_user('alice', 'wrong-password'))
        self.assertIsNone(database.authenticate_user('alice', 'correct-horse-battery'))

    def test_case_insensitive_duplicate_user_is_rejected(self):
        self.assertFalse(database.create_user('ALICE', 'another-secure-password')[0])

    def test_short_password_is_rejected(self):
        self.assertFalse(database.create_user('charlie', 'short')[0])

    def test_database_apis_require_user_scope(self):
        with self.assertRaises(ValueError): database.get_documents(None)
        with self.assertRaises(ValueError): database.get_document_contents(None)
        with self.assertRaises(ValueError): database.add_document('x.txt', 'x', None)
        with self.assertRaises(ValueError): database.delete_document(1, None)

if __name__ == '__main__': unittest.main()
