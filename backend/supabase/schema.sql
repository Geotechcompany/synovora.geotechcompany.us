-- Supabase schema for LinkedIn Automation (posts + Clerk users)
-- Run in Supabase SQL editor (or psql) once.

create extension if not exists pgcrypto;

-- Posts
create table if not exists public.posts (
  id bigserial primary key,
  topic text not null,
  content text not null,
  status text not null default 'draft' check (status in ('draft', 'scheduled', 'publishing', 'published', 'failed')),
  linkedin_post_id text,
  image_base64 text,
  image_mime_type text,
  image_url text,
  image_storage_path text,
  scheduled_for timestamptz,
  scheduled_visibility text not null default 'PUBLIC',
  publish_attempts int not null default 0,
  last_publish_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create index if not exists posts_status_idx on public.posts (status);
create index if not exists posts_created_at_idx on public.posts (created_at desc);
create index if not exists posts_scheduled_for_idx on public.posts (scheduled_for asc);
create index if not exists posts_status_scheduled_for_idx on public.posts (status, scheduled_for asc);
create index if not exists posts_image_storage_path_idx on public.posts (image_storage_path);

-- Clerk users
create table if not exists public.clerk_users (
  id uuid primary key default gen_random_uuid(),
  clerk_user_id text not null unique,
  email text,
  first_name text,
  last_name text,
  username text,
  image_url text,
  external_id text,
  last_sign_in_at timestamptz,
  linkedin_connected boolean not null default false,
  linkedin_profile jsonb,
  linkedin_last_checked_at timestamptz,
  linkedin_status_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists clerk_users_clerk_user_id_idx on public.clerk_users (clerk_user_id);
create index if not exists clerk_users_linkedin_connected_idx on public.clerk_users (linkedin_connected);
create index if not exists clerk_users_linkedin_last_checked_at_idx on public.clerk_users (linkedin_last_checked_at desc);


