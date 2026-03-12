create extension if not exists pgcrypto;

create table if not exists engine_sites (
  id text primary key,
  name text not null,
  niche_focus text not null,
  target_audience text not null,
  brand_tone text not null,
  monetization_strategy text not null,
  publishing_channels jsonb not null default '[]'::jsonb,
  opportunity_pool jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists site_snapshots (
  site_id text primary key references engine_sites(id) on delete cascade,
  snapshot jsonb not null,
  summary jsonb,
  report_md text,
  updated_at timestamptz not null default now()
);

create table if not exists posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  slug text not null unique,
  meta_description text,
  pillar text,
  content_md text not null,
  status text not null default 'draft',
  published_at timestamptz,
  image_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  category text,
  image_url text,
  price_approx numeric,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
