from __future__ import annotations

import datetime as dt
import json
import urllib.parse
import urllib.request

from ..config import gsc_service_account_json, site_url
from ..google_auth import ServiceAccountTokenError, fetch_service_account_token
from ..models import Site


class SearchConsoleClient:
    SEARCHANALYTICS_API = "https://searchconsole.googleapis.com/webmasters/v3"
    SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

    def __init__(self, site: Site) -> None:
        self.site = site

    def enabled(self) -> bool:
        return bool(gsc_service_account_json(self.site) and site_url(self.site))

    def query_exact_topic(self, topic: str, days: int = 7) -> list[dict[str, float]]:
        token = fetch_service_account_token(gsc_service_account_json(self.site), self.SCOPE)
        end_date = dt.date.today()
        start_date = end_date - dt.timedelta(days=max(1, days))
        encoded_site = urllib.parse.quote(site_url(self.site), safe="")
        body = json.dumps(
            {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["query"],
                "rowLimit": 250,
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "query",
                                "operator": "equals",
                                "expression": topic,
                            }
                        ]
                    }
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.SEARCHANALYTICS_API}/sites/{encoded_site}/searchAnalytics/query",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
        return list(payload.get("rows", []))


__all__ = ["SearchConsoleClient", "ServiceAccountTokenError"]
