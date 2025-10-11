<<<<<<< HEAD
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from pydantic import AnyHttpUrl, BaseSettings, Field, validator

from ..utils.database import DatabaseManager


class Settings(BaseSettings):
    """Application configuration derived from environment variables."""

    project_root: Path = Path(__file__).resolve().parents[2]
    assets_dir: Path = Field(default_factory=lambda: Path("server/processed"))
    models_dir: Path = Field(default_factory=lambda: Path("server/models_cache"))
    processed_dir: Path = Field(default_factory=lambda: Path("server/processed"))
    upload_dir: Path = Field(default_factory=lambda: Path("server/uploads"))
    database_url: str = Field("sqlite+aiosqlite:///server/restormer.db")
    secret_key: str = Field("change-me", env="RESTORMER_SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24
    allowed_origins: Iterable[str] = Field(
        default_factory=lambda: ["*"], env="RESTORMER_ALLOWED_ORIGINS"
    )
    public_base_url: AnyHttpUrl | None = Field(
        default=None, env="RESTORMER_PUBLIC_BASE_URL"
    )
    google_client_id: str | None = Field(default=None, env="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(
        default=None, env="GOOGLE_CLIENT_SECRET"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("allowed_origins", pre=True)
    def _split_allowed_origins(cls, value: Any) -> Iterable[str]:  # noqa: D401, N805
        """Support comma separated lists for RESTORMER_ALLOWED_ORIGINS."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def database(self) -> DatabaseManager:
        return DatabaseManager(self.database_url)

    @property
    def normalised_public_base_url(self) -> str | None:
        if not self.public_base_url:
            return None
        return str(self.public_base_url).rstrip("/")

    async def init_directories(self) -> None:
        for directory in (self.assets_dir, self.models_dir, self.processed_dir, self.upload_dir):
            Path(directory).mkdir(parents=True, exist_ok=True)

    def export(self) -> dict[str, Any]:
        return json.loads(self.json())


settings = Settings()
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/core/config.py
index 0000000000000000000000000000000000000000..81c468488b15b61f65a19be0bf8345e882554e51 100644
--- a//dev/null
+++ b/server/app/core/config.py
@@ -0,0 +1,46 @@
+from __future__ import annotations
+
+import json
+import os
+from pathlib import Path
+from typing import Any, Iterable
+
+from pydantic import BaseSettings, Field
+
+from ..utils.database import DatabaseManager
+
+
+class Settings(BaseSettings):
+    """Application configuration derived from environment variables."""
+
+    project_root: Path = Path(__file__).resolve().parents[2]
+    assets_dir: Path = Field(default_factory=lambda: Path("server/processed"))
+    models_dir: Path = Field(default_factory=lambda: Path("server/models_cache"))
+    processed_dir: Path = Field(default_factory=lambda: Path("server/processed"))
+    upload_dir: Path = Field(default_factory=lambda: Path("server/uploads"))
+    database_url: str = Field("sqlite+aiosqlite:///server/restormer.db")
+    secret_key: str = Field("change-me", env="RESTORMER_SECRET_KEY")
+    access_token_expire_minutes: int = 60 * 24
+    allowed_origins: Iterable[str] = Field(default_factory=lambda: ["*"])
+    google_client_id: str | None = Field(default=None, env="GOOGLE_CLIENT_ID")
+    google_client_secret: str | None = Field(
+        default=None, env="GOOGLE_CLIENT_SECRET"
+    )
+
+    class Config:
+        env_file = ".env"
+        env_file_encoding = "utf-8"
+
+    @property
+    def database(self) -> DatabaseManager:
+        return DatabaseManager(self.database_url)
+
+    async def init_directories(self) -> None:
+        for directory in (self.assets_dir, self.models_dir, self.processed_dir, self.upload_dir):
+            Path(directory).mkdir(parents=True, exist_ok=True)
+
+    def export(self) -> dict[str, Any]:
+        return json.loads(self.json())
+
+
+settings = Settings()
 
EOF
)
>>>>>>> origin/main
