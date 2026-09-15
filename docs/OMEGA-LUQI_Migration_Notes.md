# OMEGA-LUQI Migration & Sync Notes (v4.0.0)

## 1. Kimi model sunset - RESOLVED
`moonshot-v1-auto` (and the whole moonshot-v1 series) was officially discontinued
by Moonshot on 2026-08-31; live calls now return 404. All engines migrated to
`kimi-k3` (1M context, $3/$15 per M tokens). Cost note: K3 thinking is always-on,
so output-token spend is higher than the sticker rate suggests - for high-volume
codegen set `KIMI_MODEL=kimi-k2.7-code` ($0.95/$4). Reasoning depth is env-controlled:
`KIMI_REASONING_EFFORT=low|high|max` (default high).
Also note: K3 fixes temperature server-side; the dev-agent temperature parameter
was replaced with reasoning_effort (forced-JSON output still enforces stability).

## 2. JWT validation - NOT YET APPLICABLE
The crash logs referenced jsonwebtoken binding failures, but Luqi-AI has no JWT
layer yet - student/enterprise auth is still the pending build item. When auth
lands, all token validation will be wrapped in fail-closed try/except so a bad
token can never crash the process (this is already the pattern for every other
external dependency in the engine).

## 3. Database dialect - ALREADY AGNOSTIC
models.py uses SQLAlchemy v2 typed mappings with no dialect-specific constructs,
and DATABASE_URL accepts any SQLAlchemy dialect. MySQL works by changing one line:
    DATABASE_URL=mysql+pymysql://luqi:pass@host:3306/luqi_ai
(requires `pip install pymysql`; add to requirements when used)

## 4. Data residency flag
Moonshot processes requests in China, and a July 2026 US Treasury warning re
potential Entity List designation was unresolved as of the last reports. For
POPIA-sensitive workloads, plan a self-hosted or regional-provider fallback path
for the reasoning layer; the engine's env-based KIMI_BASE_URL/KIMI_MODEL design
is built exactly for that swap.
