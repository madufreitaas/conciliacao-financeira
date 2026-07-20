create table execucoes_conciliacao (
  id bigint generated always as identity primary key,
  criado_em timestamptz not null default now(),
  total_banco int not null,
  total_erp int not null,
  matches_exatos int not null,
  matches_janela int not null,
  matches_semanticos int not null,
  pendencias int not null,
  pct_conciliado_automatico numeric not null,
  tempo_execucao_segundos numeric not null
);

grant select, insert on public.execucoes_conciliacao to service_role;
