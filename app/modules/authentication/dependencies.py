from fastapi import Depends, Header, HTTPException

from app.modules.authentication.api import tokens, rbac
from app.modules.authentication.security import SecurityError, TokenType


def require_authenticated_user(
    authorization: str = Header(default=""),
):
    parts = authorization.split(maxsplit=1)

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = parts[1].strip()
    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return tokens.validate(raw_token, expected=TokenType.ACCESS)
    except SecurityError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str):
    def dependency(principal=Depends(require_authenticated_user)):
        tenant_id = principal.tenant_id

        if tenant_id is None:
            raise HTTPException(
                status_code=403,
                detail="Tenant context required",
            )

        assigned_roles = rbac.assignments.get(
            (principal.user_id, tenant_id), set()
        )
        if not assigned_roles:
            raise HTTPException(
                status_code=403,
                detail="No role assigned for this tenant",
            )

        granted = rbac.permissions(principal.user_id, tenant_id)
        if permission not in granted:
            raise HTTPException(
                status_code=403,
                detail="Permission denied",
            )

        return principal

    return dependency
