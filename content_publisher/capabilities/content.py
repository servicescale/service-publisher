from __future__ import annotations

from ..interfaces import OutputSink
from ..models import Atom, Output, Product, Site, SiteSnapshot, utc_now, new_id
from .utils import tokenize


class ContentCapability:
    def sync_products(self, snapshot: SiteSnapshot, product_sources: list) -> list[Product]:
        existing_keys = {(product.title.lower(), product.url): product_id for product_id, product in snapshot.products.items()}
        added: list[Product] = []
        for source in product_sources:
            for product in source.collect(snapshot):
                key = (product.title.lower(), product.url)
                if key in existing_keys:
                    current = snapshot.products[existing_keys[key]]
                    current.price = product.price
                    current.merchant = product.merchant
                    current.tags = product.tags
                    current.description = product.description
                    current.updated_at = utc_now()
                    continue
                snapshot.products[product.id] = product
                snapshot.site.product_ids.append(product.id)
                existing_keys[key] = product.id
                added.append(product)
        return added

    def select_products(self, snapshot: SiteSnapshot, atom: Atom, limit: int = 3) -> list[dict[str, str]]:
        topic_terms = {token for token in tokenize(atom.topic) if len(token) > 2}
        cluster_terms = {token for token in tokenize(atom.context.get("cluster_name", "")) if len(token) > 2}
        search_terms = topic_terms | cluster_terms
        ranked: list[tuple[int, Product]] = []
        for product in snapshot.products.values():
            product_terms = {token for token in tokenize(product.title + " " + product.description) if len(token) > 2}
            tag_terms = {token for token in product.tags if len(token) > 2}
            overlap = len(search_terms & (product_terms | tag_terms))
            if overlap > 0:
                ranked.append((overlap, product))
        ranked.sort(key=lambda item: (item[0], item[1].title.lower()), reverse=True)
        return [
            {
                "product_id": product.id,
                "title": product.title,
                "url": product.url,
                "price": product.price,
                "merchant": product.merchant,
            }
            for _, product in ranked[:limit]
        ]

    def generate_outputs(self, snapshot: SiteSnapshot, atoms: list[Atom]) -> list[Output]:
        outputs: list[Output] = []
        for atom in atoms:
            recommendations = self.select_products(snapshot, atom)
            for channel in snapshot.site.publishing_channels or ["website"]:
                title = self.render_title(atom.topic, channel)
                output = Output(
                    id=new_id("output"),
                    site_id=snapshot.site.id,
                    atom_id=atom.id,
                    channel=channel,
                    kind=self.choose_output_kind(snapshot.site, channel),
                    title=title,
                    body=self.render_output_body(snapshot.site, atom, title, channel, recommendations),
                    metadata={
                        "site_id": snapshot.site.id,
                        "cluster_id": atom.cluster_id,
                        "atom_id": atom.id,
                        "search_intent": atom.search_intent,
                        "monetization_strategy": snapshot.site.monetization_strategy,
                        "channel": channel,
                        "product_recommendations": recommendations,
                    },
                )
                snapshot.outputs[output.id] = output
                snapshot.site.output_ids.append(output.id)
                atom.output_ids.append(output.id)
                outputs.append(output)
            atom.state = "generated"
            atom.updated_at = utc_now()
        return outputs

    def deliver_outputs(self, snapshot: SiteSnapshot, outputs: list[Output], resolve_sink) -> list[Output]:
        for output in outputs:
            sink: OutputSink = resolve_sink(snapshot.site, output.channel)
            sink.publish(snapshot, output)
            atom = snapshot.atoms[output.atom_id]
            atom.state = "published"
            atom.updated_at = utc_now()
        return outputs

    def choose_output_kind(self, site: Site, channel: str) -> str:
        if channel == "newsletter":
            return "email_snippet"
        if channel == "pinterest":
            return "pinterest_pin"
        if channel == "social":
            return "social_post"
        if "affiliate" in site.monetization_strategy.lower():
            return "buying_guide"
        return "article"

    def render_title(self, topic: str, channel: str) -> str:
        base = topic.title()
        if channel == "newsletter":
            return f"{base}: Weekly Pick"
        if channel == "social":
            return f"{base} Quick Take"
        if channel == "pinterest":
            return f"{base} Ideas"
        return base

    def render_output_body(self, site: Site, atom: Atom, title: str, channel: str, recommendations: list[dict[str, str]]) -> str:
        product_cta = (
            "Relevant product picks are included to support affiliate-driven monetization."
            if "affiliate" in site.monetization_strategy.lower()
            else "Relevant resources are included to support monetization."
        )
        channel_note = {
            "website": "Formatted as a website-ready article draft.",
            "newsletter": "Formatted as a newsletter-ready snippet.",
            "social": "Formatted as a concise social post.",
            "pinterest": "Formatted as a Pinterest-ready concept.",
        }.get(channel, "Formatted for the configured publishing channel.")
        recommendation_lines = ["Recommended products:"]
        if recommendations:
            recommendation_lines.extend(
                [f"- {item['title']} ({item['merchant'] or 'merchant not set'}) {item['price']}".rstrip() for item in recommendations]
            )
        else:
            recommendation_lines.append("- No matched products yet.")
        return "\n\n".join(
            [
                f"# {title}",
                f"Channel: {channel}",
                f"Audience: {site.target_audience}",
                f"Tone: {site.brand_tone}",
                f"Search intent: {atom.search_intent}",
                f"Topic context: {atom.context.get('cluster_name', 'general')}",
                "This output was generated from an Atom and is intended to satisfy search demand.",
                channel_note,
                "\n".join(recommendation_lines),
                product_cta,
            ]
        )
