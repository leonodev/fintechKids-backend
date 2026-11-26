"""Generate a complete Mockoon Desktop Environment JSON for FHKBackend.

Features:
- Organized into the exact 12 Swagger/OpenAPI modules using Mockoon folders.
- Every route has a 3000 ms default delay (latency) to simulate mobile app loaders.
- Every route includes multiple responses:
  1. Success (200 OK / 201 Created, 3000 ms delay) - set as Default
  2. Bad Request / Business Rule Error (400 Bad Request, 3000 ms delay)
  3. Unauthorized / Expired JWT (401 Unauthorized, 3000 ms delay)
  4. Forbidden / Ownership Mismatch (403 Forbidden, 3000 ms delay)
  5. Not Found (404 Not Found, 3000 ms delay)
  6. Validation Error (422 Unprocessable Entity, 3000 ms delay)
  7. Internal Server Error (500 Internal Server Error, 3000 ms delay)
  8. Request Timeout - Slow Network (408 Request Timeout, 15000 ms delay)
  9. Gateway Timeout - Hard Timeout (504 Gateway Timeout, 35000 ms delay)
- Responses can be switched with 1 click in Mockoon Desktop OR triggered dynamically
  from the app/Postman by sending header `x-mock-scenario` or query param `mock_scenario`.

Usage:
    python3 scripts/generate_mockoon.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DELAY_MS = 3000
SOFT_TIMEOUT_DELAY_MS = 15000
HARD_TIMEOUT_DELAY_MS = 35000


def deterministic_uuid(seed: str) -> str:
    """Generate a deterministic UUIDv5 so regenerating the file keeps stable UUIDs."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fhkbackend.mockoon.{seed}"))


def make_rule(target: str, modifier: str, value: str) -> Dict[str, Any]:
    return {
        "target": target,
        "modifier": modifier,
        "value": value,
        "invert": False,
        "operator": "equals",
    }


def make_scenario_rules(scenario_name: str) -> List[Dict[str, Any]]:
    """Allow triggering a scenario via either Header `x-mock-scenario` or Query `?mock_scenario=`."""
    return [
        make_rule("header", "x-mock-scenario", scenario_name),
        make_rule("query", "mock_scenario", scenario_name),
    ]


def make_response(
    seed: str,
    label: str,
    status_code: int,
    body_obj: Any,
    latency: int = DEFAULT_DELAY_MS,
    default: bool = False,
    scenario_key: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "uuid": deterministic_uuid(f"resp.{seed}"),
        "body": json.dumps(body_obj, indent=2, ensure_ascii=False),
        "latency": latency,
        "statusCode": status_code,
        "label": label,
        "headers": [
            {
                "key": "Content-Type",
                "value": "application/json; charset=utf-8",
            }
        ],
        "bodyType": "INLINE",
        "filePath": "",
        "databucketID": "",
        "sendFileAsBody": False,
        "rules": make_scenario_rules(scenario_key) if scenario_key else [],
        "rulesOperator": "OR",
        "disableTemplating": False,
        "fallbackTo404": False,
        "default": default,
        "crudKey": "id",
        "callbacks": [],
    }


def build_standard_error_responses(
    route_seed: str,
    protected: bool = True,
    not_found_detail: str = "Requested resource was not found for this family.",
    bad_request_detail: str = "Invalid request parameters or business rule violation.",
    extra_responses: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    responses: List[Dict[str, Any]] = []
    if extra_responses:
        responses.extend(extra_responses)

    # 400 Bad Request
    responses.append(
        make_response(
            seed=f"{route_seed}.400",
            label="ERROR 400 - Bad Request / Business Rule (3000ms)",
            status_code=400,
            body_obj={"detail": bad_request_detail},
            latency=DEFAULT_DELAY_MS,
            scenario_key="bad_request",
        )
    )

    if protected:
        # 401 Unauthorized
        responses.append(
            make_response(
                seed=f"{route_seed}.401",
                label="ERROR 401 - Unauthorized / Expired JWT (3000ms)",
                status_code=401,
                body_obj={"detail": "Could not validate credentials"},
                latency=DEFAULT_DELAY_MS,
                scenario_key="unauthorized",
            )
        )
        # 403 Forbidden
        responses.append(
            make_response(
                seed=f"{route_seed}.403",
                label="ERROR 403 - Forbidden / Family Ownership Mismatch (3000ms)",
                status_code=403,
                body_obj={"detail": "The email does not match the authenticated parent account"},
                latency=DEFAULT_DELAY_MS,
                scenario_key="forbidden",
            )
        )

    # 404 Not Found
    responses.append(
        make_response(
            seed=f"{route_seed}.404",
            label="ERROR 404 - Resource Not Found (3000ms)",
            status_code=404,
            body_obj={"detail": not_found_detail},
            latency=DEFAULT_DELAY_MS,
            scenario_key="not_found",
        )
    )

    # 422 Validation Error
    responses.append(
        make_response(
            seed=f"{route_seed}.422",
            label="ERROR 422 - Unprocessable Entity / Validation Error (3000ms)",
            status_code=422,
            body_obj={
                "detail": [
                    {
                        "type": "missing",
                        "loc": ["body", "field_name"],
                        "msg": "Field required",
                        "input": None,
                    }
                ]
            },
            latency=DEFAULT_DELAY_MS,
            scenario_key="validation_error",
        )
    )

    # 500 Internal Server Error
    responses.append(
        make_response(
            seed=f"{route_seed}.500",
            label="ERROR 500 - Internal Server Error (3000ms)",
            status_code=500,
            body_obj={"detail": "Internal server error. Please try again later."},
            latency=DEFAULT_DELAY_MS,
            scenario_key="server_error",
        )
    )

    # 408 Request Timeout (15,000 ms)
    responses.append(
        make_response(
            seed=f"{route_seed}.408",
            label="TIMEOUT 408 - Slow Network Request Timeout (15000ms Delay)",
            status_code=408,
            body_obj={"detail": "Request timed out while waiting for server response."},
            latency=SOFT_TIMEOUT_DELAY_MS,
            scenario_key="slow_timeout",
        )
    )

    # 504 Gateway Timeout (35,000 ms)
    responses.append(
        make_response(
            seed=f"{route_seed}.504",
            label="TIMEOUT 504 - Hard Gateway Timeout (35000ms Delay)",
            status_code=504,
            body_obj={"detail": "Gateway timeout. Upstream service did not respond in time."},
            latency=HARD_TIMEOUT_DELAY_MS,
            scenario_key="timeout",
        )
    )

    return responses


def make_route(
    seed: str,
    method: str,
    endpoint: str,
    documentation: str,
    success_status: int,
    success_label: str,
    success_body: Any,
    protected: bool = True,
    not_found_detail: str = "Requested resource was not found for this family.",
    bad_request_detail: str = "Invalid request parameters or business rule violation.",
    extra_responses: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    default_resp = make_response(
        seed=f"{seed}.success",
        label=f"{success_label} (3000ms Loader Delay)",
        status_code=success_status,
        body_obj=success_body,
        latency=DEFAULT_DELAY_MS,
        default=True,
        scenario_key="success",
    )
    all_responses = [default_resp] + build_standard_error_responses(
        route_seed=seed,
        protected=protected,
        not_found_detail=not_found_detail,
        bad_request_detail=bad_request_detail,
        extra_responses=extra_responses,
    )
    return {
        "uuid": deterministic_uuid(f"route.{seed}"),
        "type": "http",
        "documentation": documentation,
        "method": method.lower(),
        "endpoint": endpoint.lstrip("/"),
        "responses": all_responses,
        "responseMode": None,
        "streamingMode": None,
        "streamingInterval": 0,
    }


def build_mockoon_environment() -> Dict[str, Any]:
    sample_jwt_access = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxIiwidHlwZSI6ImFjY2VzcyIsImVtYWlsIjoicGFyZW50QGZoay5hcHAiLCJyb2xlIjoidXNlciJ9."
        "mockoon-signature-access-token"
    )
    sample_jwt_refresh = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxIiwidHlwZSI6InJlZnJlc2gifQ."
        "mockoon-signature-refresh-token"
    )

    modules_spec: List[Dict[str, Any]] = [
        # 1. Server Status
        {
            "folder_name": "1. Server Status",
            "routes": [
                make_route(
                    seed="health.get",
                    method="GET",
                    endpoint="api/v1/health",
                    documentation="Backend Health Check — Verifies that the server is active and ready.",
                    success_status=200,
                    success_label="SUCCESS 200 - Server Online",
                    protected=False,
                    success_body={
                        "status": "ok",
                        "service": "FHK Backend API",
                        "version": "1.0.0",
                        "environment": "mockoon",
                        "docs_url": "/docs",
                        "openapi_url": "/api/v1/openapi.json",
                    },
                ),
            ],
        },
        # 2. App Version (Stores)
        {
            "folder_name": "2. App Version (Stores)",
            "routes": [
                make_route(
                    seed="app_version.check",
                    method="GET",
                    endpoint="api/v1/app-version/check",
                    documentation="Check if the installed app version (IOS or AND) is up to date or requires a store update.",
                    success_status=200,
                    success_label="SUCCESS 200 - App Up to Date",
                    protected=False,
                    success_body={
                        "platform": "IOS",
                        "current_version": "1.2.0",
                        "latest_version": "1.2.0",
                        "min_required_version": "1.0.0",
                        "is_up_to_date": True,
                        "update_available": False,
                        "force_update": False,
                        "store_url": "https://apps.apple.com/app/id000000000",
                        "release_notes": "Performance improvements and new security features.",
                        "message": "The application is up to date with the latest store version.",
                    },
                    extra_responses=[
                        make_response(
                            seed="app_version.check.optional_update",
                            label="SUCCESS 200 - Optional Store Update Available (3000ms)",
                            status_code=200,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="update_available",
                            body_obj={
                                "platform": "IOS",
                                "current_version": "1.1.0",
                                "latest_version": "1.2.0",
                                "min_required_version": "1.0.0",
                                "is_up_to_date": False,
                                "update_available": True,
                                "force_update": False,
                                "store_url": "https://apps.apple.com/app/id000000000",
                                "release_notes": "New family rewards and tasks features available!",
                                "message": "A new version (1.2.0) is available in the store.",
                            },
                        ),
                        make_response(
                            seed="app_version.check.force_update",
                            label="SUCCESS 200 - Mandatory Force Update Required (3000ms)",
                            status_code=200,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="force_update",
                            body_obj={
                                "platform": "IOS",
                                "current_version": "0.9.0",
                                "latest_version": "1.2.0",
                                "min_required_version": "1.0.0",
                                "is_up_to_date": False,
                                "update_available": True,
                                "force_update": True,
                                "store_url": "https://apps.apple.com/app/id000000000",
                                "release_notes": "Critical security update required to continue using FintechKids.",
                                "message": "Mandatory update required: minimum allowed version is 1.0.0.",
                            },
                        ),
                    ],
                ),
                make_route(
                    seed="app_version.list",
                    method="GET",
                    endpoint="api/v1/app-version",
                    documentation="List current store version configurations for IOS and AND.",
                    success_status=200,
                    success_label="SUCCESS 200 - Store Versions List",
                    protected=False,
                    success_body=[
                        {
                            "id": 1,
                            "platform": "IOS",
                            "latest_version": "1.2.0",
                            "min_required_version": "1.0.0",
                            "force_update": False,
                            "store_url": "https://apps.apple.com/app/id000000000",
                            "release_notes": "Initial iOS release notes.",
                            "updated_at": "2026-11-15T10:00:00Z",
                        },
                        {
                            "id": 2,
                            "platform": "AND",
                            "latest_version": "1.2.0",
                            "min_required_version": "1.0.0",
                            "force_update": False,
                            "store_url": "https://play.google.com/store/apps/details?id=com.fhk.app",
                            "release_notes": "Initial Android release notes.",
                            "updated_at": "2026-11-15T10:00:00Z",
                        },
                    ],
                ),
                make_route(
                    seed="app_version.update",
                    method="PUT",
                    endpoint="api/v1/app-version/:platform",
                    documentation="Update the published store version configuration for a platform (IOS or AND).",
                    success_status=200,
                    success_label="SUCCESS 200 - Store Version Updated",
                    protected=True,
                    success_body={
                        "id": 1,
                        "platform": "IOS",
                        "latest_version": "1.3.0",
                        "min_required_version": "1.0.0",
                        "force_update": False,
                        "store_url": "https://apps.apple.com/app/id000000000",
                        "release_notes": "Updated version configuration.",
                        "updated_at": "2026-11-15T10:05:00Z",
                    },
                ),
            ],
        },
        # 3. Authentication
        {
            "folder_name": "3. Authentication",
            "routes": [
                make_route(
                    seed="auth.register",
                    method="POST",
                    endpoint="api/v1/auth/register",
                    documentation="Register a new family account and return initial JWT tokens.",
                    success_status=201,
                    success_label="SUCCESS 201 - Family Registered + JWT",
                    protected=False,
                    bad_request_detail="The email address is already registered.",
                    success_body={
                        "access_token": sample_jwt_access,
                        "refresh_token": sample_jwt_refresh,
                        "token_type": "bearer",
                        "expires_in_minutes": 30,
                        "approve_pin": "1234",
                    },
                    extra_responses=[
                        make_response(
                            seed="auth.register.duplicate_email",
                            label="ERROR 400 - Email Already Registered (3000ms)",
                            status_code=400,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="duplicate_email",
                            body_obj={"detail": "The email address is already registered"},
                        ),
                    ],
                ),
                make_route(
                    seed="auth.login",
                    method="POST",
                    endpoint="api/v1/auth/login",
                    documentation="Authenticate parent with email_parent and client-encrypted password.",
                    success_status=200,
                    success_label="SUCCESS 200 - Login Successful + JWT",
                    protected=False,
                    bad_request_detail="Invalid login request payload.",
                    success_body={
                        "access_token": sample_jwt_access,
                        "refresh_token": sample_jwt_refresh,
                        "token_type": "bearer",
                        "expires_in_minutes": 30,
                        "approve_pin": "1234",
                    },
                    extra_responses=[
                        make_response(
                            seed="auth.login.invalid_credentials",
                            label="ERROR 401 - Incorrect Email or Password (3000ms)",
                            status_code=401,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="invalid_credentials",
                            body_obj={"detail": "Incorrect email or password"},
                        ),
                        make_response(
                            seed="auth.login.inactive",
                            label="ERROR 403 - Inactive User Account (3000ms)",
                            status_code=403,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="inactive_account",
                            body_obj={"detail": "Inactive user account"},
                        ),
                    ],
                ),
                make_route(
                    seed="auth.forgot_password",
                    method="POST",
                    endpoint="api/v1/auth/forgot-password",
                    documentation="Request a 6-digit password recovery code valid for 15 minutes.",
                    success_status=200,
                    success_label="SUCCESS 200 - Recovery Code Generated",
                    protected=False,
                    not_found_detail="No account exists with the provided email_parent.",
                    success_body={
                        "message": "A 6-digit verification code has been generated and sent to the registered email.",
                        "email_parent": "parent@fhk.app",
                        "expires_in_minutes": 15,
                        "debug_recovery_code": "482910",
                    },
                ),
                make_route(
                    seed="auth.reset_password",
                    method="POST",
                    endpoint="api/v1/auth/reset-password",
                    documentation="Reset password using the 6-digit recovery_code.",
                    success_status=200,
                    success_label="SUCCESS 200 - Password Reset Complete",
                    protected=False,
                    bad_request_detail="Invalid or expired 6-digit recovery code.",
                    success_body={
                        "message": "Password has been updated successfully. You can now log in.",
                        "email_parent": "parent@fhk.app",
                        "updated_at": "2026-11-15T10:10:00Z",
                    },
                    extra_responses=[
                        make_response(
                            seed="auth.reset_password.expired_code",
                            label="ERROR 400 - Expired 6-Digit Recovery Code (3000ms)",
                            status_code=400,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="expired_code",
                            body_obj={"detail": "The recovery code has expired. Please request a new one."},
                        ),
                    ],
                ),
                make_route(
                    seed="auth.refresh",
                    method="POST",
                    endpoint="api/v1/auth/refresh",
                    documentation="Refresh an expired access_token using a valid refresh_token.",
                    success_status=200,
                    success_label="SUCCESS 200 - Refreshed JWT Pair",
                    protected=True,
                    success_body={
                        "access_token": sample_jwt_access,
                        "refresh_token": sample_jwt_refresh,
                        "token_type": "bearer",
                        "expires_in_minutes": 30,
                        "approve_pin": "1234",
                    },
                ),
            ],
        },
        # 4. Users / Family
        {
            "folder_name": "4. Users / Family",
            "routes": [
                make_route(
                    seed="users.me.get",
                    method="GET",
                    endpoint="api/v1/users/me",
                    documentation="Get profile information of the currently authenticated parent/family.",
                    success_status=200,
                    success_label="SUCCESS 200 - Authenticated Family Profile",
                    protected=True,
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:00:00Z",
                        "name_family": "Leon Family",
                        "email_parent": "parent@fhk.app",
                        "approve_pin": "1234",
                        "is_active": True,
                        "updated_at": "2026-11-15T09:00:00Z",
                    },
                ),
                make_route(
                    seed="users.me.patch",
                    method="PATCH",
                    endpoint="api/v1/users/me",
                    documentation="Update family name, parental approve_pin, or encrypted password.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Profile Updated",
                    protected=True,
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:00:00Z",
                        "name_family": "Leon Family Updated",
                        "email_parent": "parent@fhk.app",
                        "approve_pin": "5678",
                        "is_active": True,
                        "updated_at": "2026-11-15T10:15:00Z",
                    },
                ),
            ],
        },
        # 5. Family Members
        {
            "folder_name": "5. Family Members",
            "routes": [
                make_route(
                    seed="family_members.create",
                    method="POST",
                    endpoint="api/v1/family-members",
                    documentation="Register a new family member associated with the authenticated parent.",
                    success_status=201,
                    success_label="SUCCESS 201 - Family Member Created",
                    protected=True,
                    bad_request_detail="A family member with this identification_uuid already exists.",
                    success_body={
                        "id": 1,
                        "identification_uuid": "550e8400-e29b-41d4-a716-446655440000",
                        "email_parent": "parent@fhk.app",
                        "name_family": "Leon Family",
                        "member_name": "Mateo",
                        "avatar_name": "avatar_lion_01",
                        "parent_id": 1,
                        "created_at": "2026-11-15T09:10:00Z",
                        "updated_at": "2026-11-15T09:10:00Z",
                    },
                ),
                make_route(
                    seed="family_members.list",
                    method="GET",
                    endpoint="api/v1/family-members",
                    documentation="List all family members belonging to the authenticated parent.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Members List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "identification_uuid": "550e8400-e29b-41d4-a716-446655440000",
                            "email_parent": "parent@fhk.app",
                            "name_family": "Leon Family",
                            "member_name": "Mateo",
                            "avatar_name": "avatar_lion_01",
                            "parent_id": 1,
                            "created_at": "2026-11-15T09:10:00Z",
                            "updated_at": "2026-11-15T09:10:00Z",
                        },
                        {
                            "id": 2,
                            "identification_uuid": "550e8400-e29b-41d4-a716-446655440001",
                            "email_parent": "parent@fhk.app",
                            "name_family": "Leon Family",
                            "member_name": "Sofia",
                            "avatar_name": "avatar_unicorn_01",
                            "parent_id": 1,
                            "created_at": "2026-11-15T09:12:00Z",
                            "updated_at": "2026-11-15T09:12:00Z",
                        },
                    ],
                    extra_responses=[
                        make_response(
                            seed="family_members.list.empty",
                            label="SUCCESS 200 - Empty Family Members List (3000ms)",
                            status_code=200,
                            latency=DEFAULT_DELAY_MS,
                            scenario_key="empty",
                            body_obj=[],
                        ),
                    ],
                ),
                make_route(
                    seed="family_members.patch",
                    method="PATCH",
                    endpoint="api/v1/family-members/:identification_uuid",
                    documentation="Update member_name and/or avatar_name of a family member by identification_uuid.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Member Updated",
                    protected=True,
                    not_found_detail="No family member found with that identification_uuid for this family.",
                    success_body={
                        "id": 1,
                        "identification_uuid": "550e8400-e29b-41d4-a716-446655440000",
                        "email_parent": "parent@fhk.app",
                        "name_family": "Leon Family",
                        "member_name": "Mateo Leon",
                        "avatar_name": "avatar_tiger_02",
                        "parent_id": 1,
                        "created_at": "2026-11-15T09:10:00Z",
                        "updated_at": "2026-11-15T10:20:00Z",
                    },
                ),
                make_route(
                    seed="family_members.delete",
                    method="DELETE",
                    endpoint="api/v1/family-members/:identification_uuid",
                    documentation="Delete a family member by identification_uuid.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Member Deleted",
                    protected=True,
                    not_found_detail="No family member found with that identification_uuid for this family.",
                    success_body={
                        "message": "Family member deleted successfully.",
                        "identification_uuid": "550e8400-e29b-41d4-a716-446655440000",
                    },
                ),
            ],
        },
        # 6. Family Tasks
        {
            "folder_name": "6. Family Tasks",
            "routes": [
                make_route(
                    seed="tasks.create",
                    method="POST",
                    endpoint="api/v1/tasks",
                    documentation="Create a new family task (status defaults to enable).",
                    success_status=201,
                    success_label="SUCCESS 201 - Family Task Created",
                    protected=True,
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:20:00Z",
                        "name": "Clean the bedroom",
                        "time_granted": "00:30:00",
                        "coins_granted": 50,
                        "email_parent": "parent@fhk.app",
                        "description": "Make the bed and put away all toys before dinner.",
                        "status": "enable",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:20:00Z",
                    },
                ),
                make_route(
                    seed="tasks.patch",
                    method="PATCH",
                    endpoint="api/v1/tasks/:task_id",
                    documentation="Edit a family task or toggle its status between enable and disable.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Task Updated",
                    protected=True,
                    not_found_detail="No task found with that ID for this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:20:00Z",
                        "name": "Clean bedroom and desk",
                        "time_granted": "00:45:00",
                        "coins_granted": 75,
                        "email_parent": "parent@fhk.app",
                        "description": "Make the bed, put away toys, and organize the desk.",
                        "status": "enable",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T10:25:00Z",
                    },
                ),
                make_route(
                    seed="tasks.list_all",
                    method="GET",
                    endpoint="api/v1/tasks",
                    documentation="List all tasks for the family regardless of status (enable and disable).",
                    success_status=200,
                    success_label="SUCCESS 200 - All Family Tasks List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:20:00Z",
                            "name": "Clean the bedroom",
                            "time_granted": "00:30:00",
                            "coins_granted": 50,
                            "email_parent": "parent@fhk.app",
                            "description": "Make the bed and put away all toys before dinner.",
                            "status": "enable",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:20:00Z",
                        },
                        {
                            "id": 2,
                            "created_at": "2026-11-15T09:25:00Z",
                            "name": "Wash the dishes",
                            "time_granted": "00:20:00",
                            "coins_granted": 35,
                            "email_parent": "parent@fhk.app",
                            "description": "Help wash plates after lunch.",
                            "status": "disable",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:25:00Z",
                        },
                    ],
                ),
                make_route(
                    seed="tasks.list_enabled",
                    method="GET",
                    endpoint="api/v1/tasks/enabled",
                    documentation="List only family tasks with status = enable.",
                    success_status=200,
                    success_label="SUCCESS 200 - Enabled Family Tasks Only",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:20:00Z",
                            "name": "Clean the bedroom",
                            "time_granted": "00:30:00",
                            "coins_granted": 50,
                            "email_parent": "parent@fhk.app",
                            "description": "Make the bed and put away all toys before dinner.",
                            "status": "enable",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:20:00Z",
                        }
                    ],
                ),
                make_route(
                    seed="tasks.delete",
                    method="DELETE",
                    endpoint="api/v1/tasks/:task_id",
                    documentation="Delete a family task by task_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Task Deleted",
                    protected=True,
                    not_found_detail="No task found with that ID for this family.",
                    success_body={
                        "message": "Task deleted successfully.",
                        "task_id": 1,
                    },
                ),
            ],
        },
        # 7. Parent Goals
        {
            "folder_name": "7. Parent Goals",
            "routes": [
                make_route(
                    seed="goals.create",
                    method="POST",
                    endpoint="api/v1/goals",
                    documentation="Create a new parent goal template.",
                    success_status=201,
                    success_label="SUCCESS 201 - Parent Goal Created",
                    protected=True,
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:30:00Z",
                        "measure_type": "minutes",
                        "status": "active",
                        "email_parent": "parent@fhk.app",
                        "name": "Daily reading",
                        "value": 30,
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:30:00Z",
                    },
                ),
                make_route(
                    seed="goals.list",
                    method="GET",
                    endpoint="api/v1/goals",
                    documentation="List all goals created by the parent.",
                    success_status=200,
                    success_label="SUCCESS 200 - Parent Goals List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:30:00Z",
                            "measure_type": "minutes",
                            "status": "active",
                            "email_parent": "parent@fhk.app",
                            "name": "Daily reading",
                            "value": 30,
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:30:00Z",
                        }
                    ],
                ),
                make_route(
                    seed="goals.patch",
                    method="PATCH",
                    endpoint="api/v1/goals/:goal_id",
                    documentation="Update a parent goal by goal_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Parent Goal Updated",
                    protected=True,
                    not_found_detail="No goal found with that ID for this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:30:00Z",
                        "measure_type": "minutes",
                        "status": "active",
                        "email_parent": "parent@fhk.app",
                        "name": "Evening reading",
                        "value": 45,
                        "parent_id": 1,
                        "updated_at": "2026-11-15T10:30:00Z",
                    },
                ),
                make_route(
                    seed="goals.delete",
                    method="DELETE",
                    endpoint="api/v1/goals/:goal_id",
                    documentation="Delete a parent goal by goal_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Parent Goal Deleted",
                    protected=True,
                    not_found_detail="No goal found with that ID for this family.",
                    success_body={
                        "message": "Goal deleted successfully.",
                        "goal_id": 1,
                    },
                ),
            ],
        },
        # 8. Parent Rewards
        {
            "folder_name": "8. Parent Rewards",
            "routes": [
                make_route(
                    seed="rewards.create",
                    method="POST",
                    endpoint="api/v1/rewards",
                    documentation="Create a new reward in the parent's family catalog.",
                    success_status=201,
                    success_label="SUCCESS 201 - Parent Reward Created",
                    protected=True,
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:35:00Z",
                        "name": "1 hour of video games",
                        "time_required": "01:00:00",
                        "coins_required": 100,
                        "email_parent": "parent@fhk.app",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:35:00Z",
                    },
                ),
                make_route(
                    seed="rewards.list",
                    method="GET",
                    endpoint="api/v1/rewards",
                    documentation="List all rewards created by the parent.",
                    success_status=200,
                    success_label="SUCCESS 200 - Parent Rewards List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:35:00Z",
                            "name": "1 hour of video games",
                            "time_required": "01:00:00",
                            "coins_required": 100,
                            "email_parent": "parent@fhk.app",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:35:00Z",
                        }
                    ],
                ),
                make_route(
                    seed="rewards.patch",
                    method="PATCH",
                    endpoint="api/v1/rewards/:reward_id",
                    documentation="Update a parent reward by reward_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Parent Reward Updated",
                    protected=True,
                    not_found_detail="No reward found with that ID for this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:35:00Z",
                        "name": "2 hours of video games",
                        "time_required": "02:00:00",
                        "coins_required": 180,
                        "email_parent": "parent@fhk.app",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T10:35:00Z",
                    },
                ),
                make_route(
                    seed="rewards.delete",
                    method="DELETE",
                    endpoint="api/v1/rewards/:reward_id",
                    documentation="Delete a parent reward by reward_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Parent Reward Deleted",
                    protected=True,
                    not_found_detail="No reward found with that ID for this family.",
                    success_body={
                        "message": "Reward deleted successfully.",
                        "reward_id": 1,
                    },
                ),
            ],
        },
        # 9. Member Goals
        {
            "folder_name": "9. Member Goals",
            "routes": [
                make_route(
                    seed="member_goals.create",
                    method="POST",
                    endpoint="api/v1/member-goals",
                    documentation="Assign a parent goal to a family member.",
                    success_status=201,
                    success_label="SUCCESS 201 - Member Goal Created",
                    protected=True,
                    not_found_detail="The specified goal_id or member_id does not exist in this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:40:00Z",
                        "goal_id": 1,
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "rewards_system_type": "stars",
                        "rewards_system_value": 10,
                        "accumulated_value": 0,
                        "parent_email": "parent@fhk.app",
                        "name": "Daily reading",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:40:00Z",
                    },
                ),
                make_route(
                    seed="member_goals.list",
                    method="GET",
                    endpoint="api/v1/member-goals",
                    documentation="List goals assigned to family members (optional query param: member_id).",
                    success_status=200,
                    success_label="SUCCESS 200 - Member Goals List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:40:00Z",
                            "goal_id": 1,
                            "member_id": "550e8400-e29b-41d4-a716-446655440000",
                            "rewards_system_type": "stars",
                            "rewards_system_value": 10,
                            "accumulated_value": 5,
                            "parent_email": "parent@fhk.app",
                            "name": "Daily reading",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:45:00Z",
                        }
                    ],
                ),
                make_route(
                    seed="member_goals.patch",
                    method="PATCH",
                    endpoint="api/v1/member-goals/:member_goal_id",
                    documentation="Update accumulated_value or reward settings of a member goal.",
                    success_status=200,
                    success_label="SUCCESS 200 - Member Goal Progress Updated",
                    protected=True,
                    not_found_detail="No member goal found with that ID for this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:40:00Z",
                        "goal_id": 1,
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "rewards_system_type": "stars",
                        "rewards_system_value": 10,
                        "accumulated_value": 15,
                        "parent_email": "parent@fhk.app",
                        "name": "Daily reading",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T10:40:00Z",
                    },
                ),
                make_route(
                    seed="member_goals.delete",
                    method="DELETE",
                    endpoint="api/v1/member-goals/:member_goal_id",
                    documentation="Delete a member goal by member_goal_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Member Goal Deleted",
                    protected=True,
                    not_found_detail="No member goal found with that ID for this family.",
                    success_body={
                        "message": "Member goal deleted successfully.",
                        "member_goal_id": 1,
                    },
                ),
            ],
        },
        # 10. Member Rewards
        {
            "folder_name": "10. Member Rewards",
            "routes": [
                make_route(
                    seed="member_rewards.create",
                    method="POST",
                    endpoint="api/v1/member-rewards",
                    documentation="Claim a reward for a family member (initial state: PENDING).",
                    success_status=201,
                    success_label="SUCCESS 201 - Member Reward Claimed (PENDING)",
                    protected=True,
                    bad_request_detail="You must provide either reward_id or name_reward.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:50:00Z",
                        "reward_id": 1,
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "parent_email": "parent@fhk.app",
                        "name_reward": "1 hour of video games",
                        "claimed_value": "100 coins",
                        "state": "PENDING",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:50:00Z",
                    },
                ),
                make_route(
                    seed="member_rewards.list",
                    method="GET",
                    endpoint="api/v1/member-rewards",
                    documentation="List claimed rewards for the family (optional filters: member_id, state).",
                    success_status=200,
                    success_label="SUCCESS 200 - Claimed Member Rewards List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:50:00Z",
                            "reward_id": 1,
                            "member_id": "550e8400-e29b-41d4-a716-446655440000",
                            "parent_email": "parent@fhk.app",
                            "name_reward": "1 hour of video games",
                            "claimed_value": "100 coins",
                            "state": "PENDING",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:50:00Z",
                        }
                    ],
                ),
                make_route(
                    seed="member_rewards.patch",
                    method="PATCH",
                    endpoint="api/v1/member-rewards/:member_reward_id",
                    documentation="Update state of a claimed reward (strictly PENDING or COLLECTED).",
                    success_status=200,
                    success_label="SUCCESS 200 - Member Reward Marked COLLECTED",
                    protected=True,
                    not_found_detail="No claimed reward found with that ID for this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:50:00Z",
                        "reward_id": 1,
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "parent_email": "parent@fhk.app",
                        "name_reward": "1 hour of video games",
                        "claimed_value": "100 coins",
                        "state": "COLLECTED",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T10:45:00Z",
                    },
                ),
                make_route(
                    seed="member_rewards.delete",
                    method="DELETE",
                    endpoint="api/v1/member-rewards/:member_reward_id",
                    documentation="Delete a claimed member reward by member_reward_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Claimed Member Reward Deleted",
                    protected=True,
                    not_found_detail="No claimed reward found with that ID for this family.",
                    success_body={
                        "message": "Claimed reward deleted successfully.",
                        "member_reward_id": 1,
                    },
                ),
            ],
        },
        # 11. Member Balances
        {
            "folder_name": "11. Member Balances",
            "routes": [
                make_route(
                    seed="member_balances.create",
                    method="POST",
                    endpoint="api/v1/member-balances",
                    documentation="Create or update the coin and time balance for a family member.",
                    success_status=201,
                    success_label="SUCCESS 201 - Member Balance Saved",
                    protected=True,
                    not_found_detail="No family member found with that member_id for this family.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:55:00Z",
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "coins_obtained": 150,
                        "time_obtained": "01:30:00",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:55:00Z",
                    },
                ),
                make_route(
                    seed="member_balances.list",
                    method="GET",
                    endpoint="api/v1/member-balances",
                    documentation="List balances for all members of the authenticated family.",
                    success_status=200,
                    success_label="SUCCESS 200 - All Member Balances List",
                    protected=True,
                    success_body=[
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:55:00Z",
                            "member_id": "550e8400-e29b-41d4-a716-446655440000",
                            "coins_obtained": 150,
                            "time_obtained": "01:30:00",
                            "parent_id": 1,
                            "updated_at": "2026-11-15T09:55:00Z",
                        }
                    ],
                ),
                make_route(
                    seed="member_balances.get_one",
                    method="GET",
                    endpoint="api/v1/member-balances/:member_id",
                    documentation="Retrieve the coin and time balance for a single family member by member_id.",
                    success_status=200,
                    success_label="SUCCESS 200 - Single Member Balance",
                    protected=True,
                    not_found_detail="No balance record found for the specified member_id.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:55:00Z",
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "coins_obtained": 150,
                        "time_obtained": "01:30:00",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T09:55:00Z",
                    },
                ),
                make_route(
                    seed="member_balances.patch",
                    method="PATCH",
                    endpoint="api/v1/member-balances/:member_id",
                    documentation="Partially update coins_obtained and/or time_obtained for a family member.",
                    success_status=200,
                    success_label="SUCCESS 200 - Member Balance Updated",
                    protected=True,
                    not_found_detail="No balance record found for the specified member_id.",
                    success_body={
                        "id": 1,
                        "created_at": "2026-11-15T09:55:00Z",
                        "member_id": "550e8400-e29b-41d4-a716-446655440000",
                        "coins_obtained": 200,
                        "time_obtained": "02:00:00",
                        "parent_id": 1,
                        "updated_at": "2026-11-15T10:50:00Z",
                    },
                ),
            ],
        },
        # 12. Activity History (Audit Logs)
        {
            "folder_name": "12. Activity History (Audit Logs)",
            "routes": [
                make_route(
                    seed="activity_logs.list",
                    method="GET",
                    endpoint="api/v1/activity-logs",
                    documentation="Query the chronological audit log of actions recorded for the authenticated family.",
                    success_status=200,
                    success_label="SUCCESS 200 - Family Activity Audit Logs",
                    protected=True,
                    success_body=[
                        {
                            "id": 3,
                            "created_at": "2026-11-15T10:45:00Z",
                            "parent_id": 1,
                            "email_parent": "parent@fhk.app",
                            "member_id": "550e8400-e29b-41d4-a716-446655440000",
                            "action": "COLLECT_REWARD",
                            "entity_type": "MEMBER_REWARD",
                            "entity_id": "1",
                            "details": "Claimed reward '1 hour of video games' updated to state COLLECTED",
                        },
                        {
                            "id": 2,
                            "created_at": "2026-11-15T09:20:00Z",
                            "parent_id": 1,
                            "email_parent": "parent@fhk.app",
                            "member_id": None,
                            "action": "CREATE",
                            "entity_type": "TASK",
                            "entity_id": "1",
                            "details": "Created task 'Clean the bedroom' with status 'enable'",
                        },
                        {
                            "id": 1,
                            "created_at": "2026-11-15T09:00:00Z",
                            "parent_id": 1,
                            "email_parent": "parent@fhk.app",
                            "member_id": None,
                            "action": "REGISTER",
                            "entity_type": "USER",
                            "entity_id": "1",
                            "details": "Registered family 'Leon Family'",
                        },
                    ],
                ),
            ],
        },
    ]

    folders: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    root_children: List[Dict[str, str]] = []

    for idx, mod in enumerate(modules_spec, start=1):
        folder_uuid = deterministic_uuid(f"folder.{idx}")
        folder_children: List[Dict[str, str]] = []
        for route in mod["routes"]:
            routes.append(route)
            folder_children.append({"type": "route", "uuid": route["uuid"]})

        folders.append(
            {
                "uuid": folder_uuid,
                "name": mod["folder_name"],
                "children": folder_children,
            }
        )
        root_children.append({"type": "folder", "uuid": folder_uuid})

    return {
        "uuid": deterministic_uuid("environment.fhkbackend"),
        "lastMigration": 32,
        "name": "FHKBackend Mock Server (FintechKids)",
        "endpointPrefix": "",
        "latency": 0,
        "port": 3001,
        "hostname": "0.0.0.0",
        "folders": folders,
        "routes": routes,
        "rootChildren": root_children,
        "proxyMode": False,
        "proxyHost": "",
        "proxyRemovePrefix": False,
        "tlsOptions": {
            "enabled": False,
            "type": "CERT",
            "pfxPath": "",
            "certPath": "",
            "keyPath": "",
            "caPath": "",
            "passphrase": "",
        },
        "cors": True,
        "headers": [
            {"key": "Content-Type", "value": "application/json"},
            {"key": "Access-Control-Allow-Origin", "value": "*"},
            {
                "key": "Access-Control-Allow-Methods",
                "value": "GET,POST,PUT,PATCH,DELETE,HEAD,OPTIONS",
            },
            {
                "key": "Access-Control-Allow-Headers",
                "value": "Content-Type, Origin, Accept, Authorization, Content-Length, X-Requested-With, x-mock-scenario",
            },
        ],
        "proxyReqHeaders": [{"key": "", "value": ""}],
        "proxyResHeaders": [{"key": "", "value": ""}],
        "data": [],
        "callbacks": [],
    }


def main() -> None:
    mockoon_dir = ROOT_DIR / "mockoon"
    mockoon_dir.mkdir(parents=True, exist_ok=True)
    output_path = mockoon_dir / "FHKBackend.mockoon.json"

    env_data = build_mockoon_environment()
    output_path.write_text(
        json.dumps(env_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Mockoon environment generated at: {output_path}")
    print(f"Total folders: {len(env_data['folders'])}, Total routes: {len(env_data['routes'])}")


if __name__ == "__main__":
    main()
