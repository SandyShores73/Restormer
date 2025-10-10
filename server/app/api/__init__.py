 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/api/__init__.py
index 0000000000000000000000000000000000000000..a17b83301209f284f948d8f51b782170cd957b12 100644
--- a//dev/null
+++ b/server/app/api/__init__.py
@@ -0,0 +1,3 @@
+from . import jobs, oauth, users
+
+__all__ = ["jobs", "oauth", "users"]
 
EOF
)
