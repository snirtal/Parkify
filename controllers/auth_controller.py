"""Sign-in, the current operator, and logout.

The JWT is set only as an HttpOnly cookie. The response body never includes
the token, the password, or the password hash.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, make_response, request

from controllers.authentication import apply_login_cookies, clear_auth_cookies, session_cookie_name
from controllers.authorization import current_account, permission_required, public_endpoint
from controllers.dependencies import current_services
from controllers.parsing import json_object, required_text
from services.results import UserAccount

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
@public_endpoint
def login():
    payload = json_object()
    email = required_text(payload, "email", maximum=254)
    password = required_text(payload, "password", maximum=128)
    result = current_services().auth.login(
        email=email,
        password=password,
        client_key=request.remote_addr or "",
    )
    response = jsonify({"user": _public_user(result.account)})
    apply_login_cookies(response, token=result.token, csrf_token=result.csrf_token)
    return response, 200


@auth_bp.get("/me")
@permission_required()
def me():
    account = current_account()
    return jsonify({"user": _public_user(account)}), 200


@auth_bp.post("/logout")
@permission_required()
def logout():
    token = request.cookies.get(session_cookie_name(), "")
    current_services().auth.logout(token)
    response = make_response("", 204)
    clear_auth_cookies(response)
    return response


def _public_user(account: UserAccount) -> dict[str, object]:
    return {
        "id": account.id,
        "email": account.email,
        "full_name": account.full_name,
        "role": account.role,
        "is_active": account.is_active,
    }
