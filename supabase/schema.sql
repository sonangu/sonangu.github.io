-- ============================================================
-- 이용승 교수님 논문 공유 홈페이지 — Supabase 스키마
-- 2026-11-21
-- 읽기: 누구나(anon) / 쓰기: 관리자(admins 테이블에 등록된 이메일)만
-- ============================================================

-- ---------- 관리자 명단 ----------
create table if not exists public.admins (
  email      text primary key,
  name       text,
  created_at timestamptz not null default now()
);

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.admins a
    where lower(a.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

grant execute on function public.is_admin() to anon, authenticated;

-- ---------- 논문 · 이슈브리프 ----------
create table if not exists public.publications (
  id         text primary key,                 -- 예: 2026-poly-convivialism
  year       int  not null,
  month      int,
  kind       text not null default 'article',  -- article | brief
  grade      text,
  t          text not null,                    -- 한국어 제목
  te         text,                             -- 영문 제목
  t_zh       text,                             -- 중문 제목
  a          text[] not null default '{}',     -- 저자
  v          text,                             -- 학술지(한글)
  ve         text,                             -- 학술지(영문)
  vol        text,
  pages      text,
  doi        text,
  kci        text,                             -- KCI artiId
  dbpia      text,
  isbn       text,
  abs        text,                             -- 한국어 초록
  abs_en     text,                             -- 영문 초록
  abs_zh     text,                             -- 중문 초록
  langs      text[] not null default '{ko}',   -- 원문/번역 보유 언어
  pdf_url    text,                             -- 국문 PDF
  pdf_en_url text,                             -- 영문 PDF
  pdf_zh_url text,                             -- 중문 PDF
  sort       int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------- 저서 · 교재 ----------
create table if not exists public.books (
  id         text primary key,
  year       int  not null,
  month      int,
  grade      text,                             -- 저서(공저) | 교재(공저) | 저서(단독) 등
  t          text not null,
  te         text,
  t_zh       text,
  a          text[] not null default '{}',
  v          text,                             -- 출판사
  ve         text,
  vol        text,                             -- 총서 등
  pages      text,
  isbn       text,
  abs        text,
  abs_en     text,
  abs_zh     text,
  langs      text[] not null default '{ko}',
  pdf_url    text,
  pdf_en_url text,
  pdf_zh_url text,
  sort       int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------- 강의 ----------
create table if not exists public.courses (
  id         uuid primary key default gen_random_uuid(),
  sort       int not null default 0,
  t_ko       text not null default '',
  t_en       text,
  t_zh       text,
  k_ko       text,                             -- 분류 (예: 교양 · 다문화/이주)
  k_en       text,
  k_zh       text,
  d_ko       text,                             -- 설명
  d_en       text,
  d_zh       text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------- 사이트 소개·연락처 (한 행) ----------
create table if not exists public.site_profile (
  id         int primary key default 1 check (id = 1),
  content    jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
insert into public.site_profile (id, content) values (1, '{}'::jsonb)
  on conflict (id) do nothing;

-- ---------- updated_at 자동 갱신 ----------
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_pubs_touch on public.publications;
create trigger trg_pubs_touch before update on public.publications
  for each row execute function public.touch_updated_at();

drop trigger if exists trg_books_touch on public.books;
create trigger trg_books_touch before update on public.books
  for each row execute function public.touch_updated_at();

drop trigger if exists trg_courses_touch on public.courses;
create trigger trg_courses_touch before update on public.courses
  for each row execute function public.touch_updated_at();

-- ---------- RLS ----------
alter table public.admins       enable row level security;
alter table public.publications enable row level security;
alter table public.books        enable row level security;
alter table public.courses      enable row level security;
alter table public.site_profile enable row level security;

-- admins: 관리자 본인만 조회 가능 (이메일 명단 자체는 비공개)
drop policy if exists admins_read on public.admins;
create policy admins_read on public.admins for select to authenticated
  using (public.is_admin());

-- publications
drop policy if exists pubs_read on public.publications;
create policy pubs_read on public.publications for select to anon, authenticated using (true);
drop policy if exists pubs_write on public.publications;
create policy pubs_write on public.publications for insert to authenticated with check (public.is_admin());
drop policy if exists pubs_update on public.publications;
create policy pubs_update on public.publications for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists pubs_delete on public.publications;
create policy pubs_delete on public.publications for delete to authenticated using (public.is_admin());

-- books
drop policy if exists books_read on public.books;
create policy books_read on public.books for select to anon, authenticated using (true);
drop policy if exists books_write on public.books;
create policy books_write on public.books for insert to authenticated with check (public.is_admin());
drop policy if exists books_update on public.books;
create policy books_update on public.books for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists books_delete on public.books;
create policy books_delete on public.books for delete to authenticated using (public.is_admin());

-- courses
drop policy if exists courses_read on public.courses;
create policy courses_read on public.courses for select to anon, authenticated using (true);
drop policy if exists courses_write on public.courses;
create policy courses_write on public.courses for insert to authenticated with check (public.is_admin());
drop policy if exists courses_update on public.courses;
create policy courses_update on public.courses for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists courses_delete on public.courses;
create policy courses_delete on public.courses for delete to authenticated using (public.is_admin());

-- site_profile
drop policy if exists profile_read on public.site_profile;
create policy profile_read on public.site_profile for select to anon, authenticated using (true);
drop policy if exists profile_write on public.site_profile;
create policy profile_write on public.site_profile for insert to authenticated with check (public.is_admin());
drop policy if exists profile_update on public.site_profile;
create policy profile_update on public.site_profile for update to authenticated using (public.is_admin()) with check (public.is_admin());
drop policy if exists profile_delete on public.site_profile;
create policy profile_delete on public.site_profile for delete to authenticated using (public.is_admin());

-- ---------- 권한 ----------
grant select on public.publications, public.books, public.courses, public.site_profile to anon, authenticated;
grant insert, update, delete on public.publications, public.books, public.courses, public.site_profile to authenticated;
grant select on public.admins to authenticated;

-- ---------- Storage: 버킷 papers (공개 읽기, 관리자만 쓰기) ----------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('papers', 'papers', true, 52428800, array['application/pdf'])
on conflict (id) do update set public = true, file_size_limit = 52428800, allowed_mime_types = array['application/pdf'];

drop policy if exists papers_public_read on storage.objects;
create policy papers_public_read on storage.objects for select to anon, authenticated
  using (bucket_id = 'papers');

drop policy if exists papers_admin_insert on storage.objects;
create policy papers_admin_insert on storage.objects for insert to authenticated
  with check (bucket_id = 'papers' and public.is_admin());

drop policy if exists papers_admin_update on storage.objects;
create policy papers_admin_update on storage.objects for update to authenticated
  using (bucket_id = 'papers' and public.is_admin());

drop policy if exists papers_admin_delete on storage.objects;
create policy papers_admin_delete on storage.objects for delete to authenticated
  using (bucket_id = 'papers' and public.is_admin());
