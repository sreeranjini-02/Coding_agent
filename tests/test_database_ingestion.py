import sqlite3

from ingestion.database import load_database

def test_load_sqlite_table(tmp_path):
    path = tmp_path / "knowledge.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE notes (topic TEXT, detail TEXT)")
        connection.execute("INSERT INTO notes VALUES ('Java', 'classes and interfaces')")
    docs = load_database(f"sqlite:///{path.as_posix()}")
    assert len(docs) == 1
    assert "classes and interfaces" in docs[0].text
    assert docs[0].kind == "database"

