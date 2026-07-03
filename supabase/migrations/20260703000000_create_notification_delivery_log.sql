create table if not exists public.notification_delivery_log (
    id uuid primary key default gen_random_uuid(),
    event_key text not null unique,
    event_type text not null,
    user_id uuid not null references public.users(id) on delete cascade,
    class_id uuid references public.classes(id) on delete cascade,
    reservation_id uuid references public.reservations(id) on delete cascade,
    created_at timestamp with time zone not null default now()
);

alter table public.notification_delivery_log enable row level security;

drop policy if exists "service role gestiona logs de notificaciones" on public.notification_delivery_log;
create policy "service role gestiona logs de notificaciones"
on public.notification_delivery_log
to service_role
using (true)
with check (true);
