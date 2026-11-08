"""Modul penyimpanan Cache SQLite lokal untuk akselerasi performa & proteksi rate limit."""

import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Union


class SQLiteCache:
    """Manajer cache persisten berbasis SQLite dengan dukungan Time-To-Live (TTL) dan thread-safety.

    Attributes:
        db_path: Path berkas basis data SQLite untuk cache (atau ':memory:').
        default_ttl: Waktu simpan standar dalam detik (default: 86400 detik / 24 jam).
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        default_ttl: int = 86400,
    ) -> None:
        if db_path is None or db_path == ":memory:":
            self.db_path = ":memory:"
            self._shared_conn: Optional[sqlite3.Connection] = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            p = Path(db_path).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(p)
            self._shared_conn = None

        self.default_ttl = default_ttl
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Membuat koneksi SQLite baru atau mengembalikan koneksi in-memory bersama."""
        if self._shared_conn is not None:
            return self._shared_conn

        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False,
        )
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _release_connection(self, conn: sqlite3.Connection) -> None:
        """Menutup koneksi berkas disk; koneksi in-memory tetap dibuka."""
        if conn is not self._shared_conn:
            conn.close()

    def _init_db(self) -> None:
        """Membuat tabel cache_entries dan index jika belum ada."""
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL,
                        tag TEXT
                    );
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tag ON cache_entries(tag);")
                conn.commit()
            finally:
                self._release_connection(conn)

    def get(self, key: str) -> Optional[Any]:
        """Mengambil nilai data dari cache jika kunci ada dan belum kedaluwarsa.

        Args:
            key: Kunci unik entri (misal URL atau hash kata kunci).

        Returns:
            Data ter-deserialisasi (dict, list, dll.) jika valid, atau None jika miss/expired.
        """
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if not row:
                    self._misses += 1
                    return None

                value_json, expires_at = row
                if expires_at > 0 and now > expires_at:
                    # Entri telah kedaluwarsa
                    self._misses += 1
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    conn.commit()
                    return None

                self._hits += 1
                return json.loads(value_json)
            except Exception:
                self._misses += 1
                return None
            finally:
                self._release_connection(conn)

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tag: Optional[str] = None,
    ) -> None:
        """Menyimpan data ke dalam cache dengan batas masa berlaku (TTL).

        Args:
            key: Kunci unik entri.
            value: Objek serializable (dict, list, str, int, bool).
            ttl: Masa berlaku dalam detik. Jika None, memakai default_ttl. (0 = permanen).
            tag: Kategori tag opsional (misal: 'search', 'detail_pt', 'prodi').
        """
        now = time.time()
        durasi = ttl if ttl is not None else self.default_ttl
        expires_at = (now + durasi) if durasi > 0 else 0.0
        val_str = json.dumps(value, ensure_ascii=False)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries (key, value, created_at, expires_at, tag)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key, val_str, now, expires_at, tag),
                )
                conn.commit()
            finally:
                self._release_connection(conn)

    def delete(self, key: str) -> bool:
        """Menghapus sebuah entri dari cache."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                self._release_connection(conn)

    def clear(self, expired_only: bool = False, tag: Optional[str] = None) -> int:
        """Membersihkan entri cache.

        Args:
            expired_only: Jika True, hanya menghapus yang sudah kedaluwarsa.
            tag: Jika diisi, hanya menghapus entri dengan tag tertentu.

        Returns:
            Jumlah baris yang dihapus.
        """
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                if expired_only:
                    if tag:
                        cursor = conn.execute(
                            "DELETE FROM cache_entries WHERE expires_at > 0 AND expires_at < ? AND tag = ?",
                            (now, tag),
                        )
                    else:
                        cursor = conn.execute(
                            "DELETE FROM cache_entries WHERE expires_at > 0 AND expires_at < ?",
                            (now,),
                        )
                else:
                    if tag:
                        cursor = conn.execute("DELETE FROM cache_entries WHERE tag = ?", (tag,))
                    else:
                        cursor = conn.execute("DELETE FROM cache_entries")
                conn.commit()
                return cursor.rowcount
            finally:
                self._release_connection(conn)

    def stats(self) -> Dict[str, Any]:
        """Mengembalikan statistik penggunaan cache."""
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute("SELECT COUNT(*), SUM(LENGTH(value)) FROM cache_entries")
                total_entries, total_bytes = cursor.fetchone()
                total_entries = total_entries or 0
                total_bytes = total_bytes or 0

                cursor_expired = conn.execute(
                    "SELECT COUNT(*) FROM cache_entries WHERE expires_at > 0 AND expires_at < ?",
                    (now,),
                )
                expired_count = cursor_expired.fetchone()[0] or 0

                file_size_kb = 0.0
                if self.db_path != ":memory:" and os.path.exists(self.db_path):
                    file_size_kb = round(os.path.getsize(self.db_path) / 1024, 2)

                total_requests = self._hits + self._misses
                hit_rate = round((self._hits / total_requests * 100), 1) if total_requests > 0 else 0.0

                return {
                    "database_path": self.db_path,
                    "total_entries": total_entries,
                    "expired_entries": expired_count,
                    "active_entries": total_entries - expired_count,
                    "data_size_bytes": total_bytes,
                    "file_size_kb": file_size_kb,
                    "hits": self._hits,
                    "misses": self._misses,
                    "hit_rate_pct": hit_rate,
                }
            finally:
                self._release_connection(conn)

    def close(self) -> None:
        """Menutup koneksi in-memory jika ada."""
        if self._shared_conn is not None:
            try:
                self._shared_conn.close()
            except Exception:
                pass
            self._shared_conn = None
