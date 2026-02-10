-- Add occupations (list of professions) to clerk_users. Run this if your table was created before this column existed.
ALTER TABLE public.clerk_users
  ADD COLUMN IF NOT EXISTS occupations jsonb DEFAULT '[]'::jsonb;
