from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from ..models import Output, Site, SiteSnapshot, utc_now


@dataclass
class SupabaseCrmConfig:
    url: str
    service_role_key: str
    posts_table: str = "posts"
    timeout: float = 10.0
    publish_status: str = "published"
    pillar_fallback: str = "general"


class SupabaseCrmSink:
    channel = "website"

    def __init__(self, config: SupabaseCrmConfig) -> None:
        self.config = config

    def publish(self, snapshot: SiteSnapshot, output: Output) -> Output:
        atom = snapshot.atoms[output.atom_id]
        slug = self._slugify(output.metadata.get("public_slug") or output.title)
        now = output.published_at or utc_now()
        payload = {
            "title": output.title,
            "slug": slug,
            "meta_description": self._build_meta_description(atom.topic, output),
            "pillar": self._pillar(atom),
            "content_md": output.body,
            "status": self.config.publish_status,
            "published_at": now,
        }

        record = self._update_or_insert(slug, payload)

        output.status = "published"
        output.published_at = now
        output.updated_at = utc_now()
        output.metadata["artifact_path"] = self._public_url(snapshot.site, slug)
        output.metadata["crm"] = {
            "provider": "supabase",
            "table": self.config.posts_table,
            "record": record,
        }
        output.metadata["public_slug"] = slug
        return output

    def _update_or_insert(self, slug: str, payload: dict[str, object]) -> dict[str, object]:
        existing = self._select_existing(slug)
        if existing is not None:
            return self._patch_existing(slug, payload)
        return self._insert_new(payload)

    def _select_existing(self, slug: str) -> dict[str, object] | None:
        query = urllib.parse.urlencode({"select": "id,slug,status,published_at", "slug": f"eq.{slug}"})
        request = self._request(
            f"{self._table_url()}?{query}",
            method="GET",
            extra_headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
            payload = json.loads(response.read().decode("utf-8") or "[]")
        if isinstance(payload, list) and payload:
            row = payload[0]
            if isinstance(row, dict):
                return row
        return None

    def _patch_existing(self, slug: str, payload: dict[str, object]) -> dict[str, object]:
        query = urllib.parse.urlencode({"slug": f"eq.{slug}", "select": "id,slug,status,published_at"})
        request = self._request(
            f"{self._table_url()}?{query}",
            method="PATCH",
            data=payload,
            extra_headers={"Prefer": "return=representation"},
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8") or "[]")
        if isinstance(response_payload, list) and response_payload:
            row = response_payload[0]
            if isinstance(row, dict):
                return row
        return {"slug": slug}

    def _insert_new(self, payload: dict[str, object]) -> dict[str, object]:
        query = urllib.parse.urlencode({"select": "id,slug,status,published_at"})
        request = self._request(
            f"{self._table_url()}?{query}",
            method="POST",
            data=payload,
            extra_headers={"Prefer": "return=representation"},
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8") or "[]")
        if isinstance(response_payload, list) and response_payload:
            row = response_payload[0]
            if isinstance(row, dict):
                return row
        return {"slug": str(payload["slug"])}

    def _request(
        self,
        url: str,
        *,
        method: str,
        data: dict[str, object] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> urllib.request.Request:
        headers = {
            "apikey": self.config.service_role_key,
            "Authorization": f"Bearer {self.config.service_role_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        body = None if data is None else json.dumps(data).encode("utf-8")
        return urllib.request.Request(url, data=body, headers=headers, method=method)

    def _table_url(self) -> str:
        return f"{self.config.url.rstrip('/')}/rest/v1/{self.config.posts_table}"

    def _pillar(self, atom) -> str:
        cluster_name = str(atom.context.get("cluster_name") or "").strip().lower()
        if not cluster_name:
            return self.config.pillar_fallback
        return "_".join(part for part in cluster_name.split() if part) or self.config.pillar_fallback

    def _build_meta_description(self, topic: str, output: Output) -> str:
        text = str(output.body).replace("\n", " ").strip()
        base = f"{topic.title()} guide."
        if text:
            text = " ".join(text.split())
            snippet = text[:120].rstrip()
            if not snippet.endswith("."):
                snippet = f"{snippet}."
            base = snippet
        return base[:155].rstrip()

    def _public_url(self, site: Site, slug: str) -> str:
        site_url = str(site.metadata.get("site_url", "")).rstrip("/")
        if not site_url:
            return slug
        return f"{site_url}/{slug}"

    def _slugify(self, value: object) -> str:
        chars: list[str] = []
        for char in str(value).lower():
            if char.isalnum():
                chars.append(char)
            elif chars and chars[-1] != "-":
                chars.append("-")
        return "".join(chars).strip("-") or "output"
