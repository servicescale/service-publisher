from __future__ import annotations

import os
from typing import Any

from .models import Site


def site_setting(site: Site, key: str, env_names: list[str] | None = None, default: Any = None) -> Any:
    if key in site.metadata:
        return site.metadata[key]
    for env_name in env_names or []:
        value = os.environ.get(env_name)
        if value:
            return value
    return default


def site_url(site: Site) -> str:
    return str(site_setting(site, "site_url", ["NEXT_PUBLIC_SITE_URL"], "") or "")


def gsc_service_account_json(site: Site) -> str:
    return str(site_setting(site, "gsc_service_account_json", ["GSC_SERVICE_ACCOUNT_JSON"], "") or "")


def cron_secret(site: Site) -> str:
    return str(site_setting(site, "cron_secret", ["CRON_SECRET"], "") or "")


def supabase_url(site: Site) -> str:
    return str(site_setting(site, "supabase_url", ["NEXT_PUBLIC_SUPABASE_URL"], "") or "")


def supabase_service_role_key(site: Site) -> str:
    return str(site_setting(site, "supabase_service_role_key", ["SUPABASE_SERVICE_ROLE_KEY"], "") or "")
