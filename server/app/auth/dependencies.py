 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/auth/dependencies.py
index 0000000000000000000000000000000000000000..0be175290d70604f1b3895ca2419dab4284acac2 100644
--- a//dev/null
+++ b/server/app/auth/dependencies.py
@@ -0,0 +1,39 @@
+from __future__ import annotations
+
+from fastapi import Depends, HTTPException, status
+from fastapi.security import OAuth2PasswordBearer
+from jose import JWTError, jwt
+
+from ..core.config import settings
+from ..schemas.tokens import TokenPayload
+from ..schemas.users import UserRead
+from ..services.auth import get_user_by_id
+
+reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="token")
+
+
+def get_token_payload(token: str = Depends(reusable_oauth2)) -> TokenPayload:
+    try:
+        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
+        token_data = TokenPayload(**payload)
+    except JWTError as exc:
+        raise HTTPException(
+            status_code=status.HTTP_403_FORBIDDEN,
+            detail="Could not validate credentials",
+        ) from exc
+    if token_data.sub is None:
+        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
+    return token_data
+
+
+async def get_current_user(payload: TokenPayload = Depends(get_token_payload)) -> UserRead:
+    user = await get_user_by_id(int(payload.sub))
+    if not user:
+        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
+    return user
+
+
+async def get_current_active_user(user: UserRead = Depends(get_current_user)) -> UserRead:
+    if not user.is_active:
+        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
+    return user
 
EOF
)
