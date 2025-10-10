<<<<<<< HEAD
from .user import User
from .job import ProcessingJob

__all__ = ["User", "ProcessingJob"]
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/models/__init__.py
index 0000000000000000000000000000000000000000..0f98b19d4ab842ec6fc0db67ea8b2878e10ce300 100644
--- a//dev/null
+++ b/server/app/models/__init__.py
@@ -0,0 +1,4 @@
+from .user import User
+from .job import ProcessingJob
+
+__all__ = ["User", "ProcessingJob"]
 
EOF
)
>>>>>>> origin/main
