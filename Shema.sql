-- À exécuter dans Supabase > SQL Editor
-- Crée la table transactions avec Row Level Security

create table transactions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  created_at  timestamptz default now(),
  date        date not null,
  description text not null,
  categorie   text not null,
  type        text not null,
  montant     numeric not null,
  auteur      text not null
);

-- Activer la sécurité par ligne (RLS)
alter table transactions enable row level security;

-- Chaque utilisateur ne voit que ses propres données
create policy "Users see own rows"
  on transactions for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
