<<<<<<< HEAD
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth.dependencies import get_current_active_user
from ..schemas.users import UserCreate, UserRead
from ..services import auth

router = APIRouter()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate) -> UserRead:
    return await auth.create_user(user_in)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: UserRead = Depends(get_current_active_user)) -> UserRead:
    return current_user
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/app/api/users.py
index 0000000000000000000000000000000000000000..c2759eb67ce9af66c10e732ec6c378427085b45e 100644
--- a//dev/null
+++ b/server/app/api/users.py
@@ -0,0 +1,19 @@
+from __future__ import annotations
+
+from fastapi import APIRouter, Depends, HTTPException, status
+
+from ..auth.dependencies import get_current_active_user
+from ..schemas.users import UserCreate, UserRead
+from ..services import auth
+
+router = APIRouter()
+
+
+@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
+async def create_user(user_in: UserCreate) -> UserRead:
+    return await auth.create_user(user_in)
+
+
+@router.get("/me", response_model=UserRead)
+async def read_me(current_user: UserRead = Depends(get_current_active_user)) -> UserRead:
+    return current_user
 
EOF
)
>>>>>>> origin/main
