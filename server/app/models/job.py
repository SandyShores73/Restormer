<<<<<<< HEAD
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ProcessingJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="pending", index=True)
    input_path: str
    output_path: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = None
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/models/job.py
index 0000000000000000000000000000000000000000..dd37c75cceab3e55ed147d790af2b221fca2e852 100644
--- a//dev/null
+++ b/server/app/models/job.py
@@ -0,0 +1,17 @@
+from __future__ import annotations
+
+from datetime import datetime
+from typing import Optional
+
+from sqlmodel import Field, SQLModel
+
+
+class ProcessingJob(SQLModel, table=True):
+    id: Optional[int] = Field(default=None, primary_key=True)
+    user_id: int = Field(foreign_key="user.id", index=True)
+    status: str = Field(default="pending", index=True)
+    input_path: str
+    output_path: str | None = None
+    created_at: datetime = Field(default_factory=datetime.utcnow)
+    updated_at: datetime = Field(default_factory=datetime.utcnow)
+    error_message: str | None = None
 
EOF
)
>>>>>>> origin/main
