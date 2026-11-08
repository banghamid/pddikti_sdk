"""Client utama untuk berkomunikasi dengan layanan API / data PDDikti."""

from typing import Any, Dict, Optional
import httpx


class PDDiktiClient:
    """Client untuk berinteraksi dengan API atau endpoint PDDikti.
    
    Attributes:
        base_url: URL basis endpoint API PDDikti.
        timeout: Batas waktu permintaan HTTP dalam detik.
    """

    DEFAULT_BASE_URL = "https://api-frontend.kemdikbud.go.id"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        
        default_headers = {
            "User-Agent": "pddikti-sdk/0.1.0 (Python)",
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)
            
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=default_headers,
            timeout=self.timeout,
        )

    def close(self) -> None:
        """Menutup koneksi client HTTP."""
        self._client.close()

    def __enter__(self) -> "PDDiktiClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def search(self, keyword: str) -> Dict[str, Any]:
        """Melakukan pencarian agregat di PDDikti berdasarkan kata kunci.
        
        Args:
            keyword: Kata kunci pencarian (nama mahasiswa, dosen, PT, atau prodi).
            
        Returns:
            Dict berisi hasil pencarian yang dikelompokkan berdasarkan kategori.
        """
        response = self._client.get(f"/hit/{keyword}")
        response.raise_for_status()
        return response.json()
