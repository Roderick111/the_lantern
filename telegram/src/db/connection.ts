import { Database } from "bun:sqlite";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { SCHEMA_SQL, migrateSchema } from "./schema";

let _db: Database | null = null;

export function openDb(path: string): Database {
  // MED-14: parent dir must exist before Bun creates the DB file
  if (path !== ":memory:") {
    mkdirSync(dirname(path), { recursive: true });
  }
  const db = new Database(path, { create: true });
  db.exec("PRAGMA journal_mode=WAL");
  db.exec("PRAGMA busy_timeout=5000");
  db.exec("PRAGMA foreign_keys=ON");
  db.exec(SCHEMA_SQL);
  migrateSchema(db);
  return db;
}

export function getDb(path?: string): Database {
  if (_db) return _db;
  if (!path) throw new Error("DB not initialized");
  _db = openDb(path);
  return _db;
}

export function setDb(db: Database): void {
  _db = db;
}

export function closeDb(): void {
  if (_db) {
    _db.close();
    _db = null;
  }
}

export function resetDbForTests(path = ":memory:"): Database {
  closeDb();
  _db = openDb(path);
  return _db;
}
