insert into engine_sites (
  id,
  name,
  niche_focus,
  target_audience,
  brand_tone,
  monetization_strategy,
  publishing_channels,
  opportunity_pool,
  metadata
) values (
  'mylegoguide',
  'My LEGO Guide',
  'lego product guides and buying content',
  'adult builders, gift buyers, and collectors',
  'clear, practical, and commercial without hype',
  'affiliate links and buying guides',
  '["website","newsletter"]'::jsonb,
  '[
    {"topic":"best lego sets for adults","cluster_name":"best lego sets","search_intent":"commercial","demand_score":82,"source":"seed","confidence":0.91},
    {"topic":"best lego sets under $100","cluster_name":"best lego sets","search_intent":"commercial","demand_score":74,"source":"seed","confidence":0.87},
    {"topic":"lego gift ideas for adults","cluster_name":"lego gift guides","search_intent":"commercial","demand_score":78,"source":"seed","confidence":0.88},
    {"topic":"best retired lego sets to buy","cluster_name":"retired lego sets","search_intent":"commercial","demand_score":69,"source":"seed","confidence":0.82}
  ]'::jsonb,
  '{"siteUrl":"https://mylegoguide.com"}'::jsonb
)
on conflict (id) do update
set
  name = excluded.name,
  niche_focus = excluded.niche_focus,
  target_audience = excluded.target_audience,
  brand_tone = excluded.brand_tone,
  monetization_strategy = excluded.monetization_strategy,
  publishing_channels = excluded.publishing_channels,
  opportunity_pool = excluded.opportunity_pool,
  metadata = excluded.metadata,
  updated_at = now();
