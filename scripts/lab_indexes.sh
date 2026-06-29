#!/usr/bin/env bash
# Toggle lab Postgres indexes for before/after experiments.
# Drops/adds by name with post-toggle verification.

set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
POSTGRES_USER="${POSTGRES_USER:-loadlab}"
POSTGRES_DB="${POSTGRES_DB:-loadlab}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${SCRIPT_DIR}/.lab_index_state"

read -r -a COMPOSE_ARR <<< "${COMPOSE}"

PSQL=(exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1)

# Explicit name -> CREATE INDEX DDL (IF NOT EXISTS added at runtime if missing).
declare -A INDEX_DDL=(
  ["catalog_pro_categor_da8cc9_idx"]="CREATE INDEX catalog_pro_categor_da8cc9_idx ON catalog_product (category, created_at)"
  ["orders_orde_order_i_52f79a_idx"]="CREATE INDEX orders_orde_order_i_52f79a_idx ON orders_orderitem (order_id, product_id)"
)

# Experiment groups (space-separated index names; @dynamic resolves at runtime).
declare -A INDEX_GROUPS=(
  ["category-read"]="catalog_pro_categor_da8cc9_idx @category_column"
  ["order-items"]="orders_orde_order_i_52f79a_idx"
)

usage() {
  cat <<EOF
Usage: $0 <command> [TARGET]

Commands:
  list                     Registry, groups, and live Postgres indexes
  drop INDEX               Drop one index (fails if still present afterward)
  add INDEX                Create one index (fails if missing afterward)
  drop-group GROUP         Drop all indexes in a group
  add-group GROUP          Recreate all indexes in a group
  verify-absent INDEX      Exit 1 if index exists
  verify-present INDEX     Exit 1 if index missing

Groups:
$(for g in "${!INDEX_GROUPS[@]}"; do echo "  - $g: ${INDEX_GROUPS[$g]}"; done | sort)

Registry (explicit DDL):
$(for n in "${!INDEX_DDL[@]}"; do echo "  - $n"; done | sort)

Examples:
  $0 list
  $0 drop catalog_pro_categor_da8cc9_idx
  $0 add catalog_pro_categor_da8cc9_idx
  $0 drop-group category-read
  $0 add-group category-read
EOF
}

run_psql() {
  "${COMPOSE_ARR[@]}" "${PSQL[@]}" -c "$1"
}

run_psql_tsv() {
  "${COMPOSE_ARR[@]}" "${PSQL[@]}" -t -A -c "$1" | tr -d '\r'
}

index_exists() {
  local index="$1"
  local count
  count="$(run_psql_tsv "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname = '${index}';")"
  [[ "${count}" == "1" ]]
}

fetch_indexdef() {
  local index="$1"
  run_psql_tsv "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND indexname = '${index}';"
}

resolve_category_column_index() {
  local live
  live="$(run_psql_tsv "
    SELECT indexname
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename = 'catalog_product'
      AND indexname <> 'catalog_pro_categor_da8cc9_idx'
      AND indexdef ~* '\\(category\\)'
      AND indexdef NOT ILIKE '%created_at%'
      AND indexname NOT LIKE '%_like'
    ORDER BY indexname
    LIMIT 1;
  ")"
  if [[ -n "$live" ]]; then
    echo "$live"
    return
  fi

  local state_file
  for state_file in "${STATE_DIR}"/catalog_product_category_*.sql; do
    if [[ -f "$state_file" ]]; then
      basename "$state_file" .sql
      return
    fi
  done
}

resolve_group_member() {
  local token="$1"
  if [[ "$token" == "@category_column" ]]; then
    resolve_category_column_index
  else
    echo "$token"
  fi
}

expand_group() {
  local group="$1"
  if [[ -z "${INDEX_GROUPS[$group]+x}" ]]; then
    echo "Unknown group: ${group}" >&2
    exit 1
  fi
  local token name
  for token in ${INDEX_GROUPS[$group]}; do
    name="$(resolve_group_member "$token")"
    if [[ -n "$name" ]]; then
      echo "$name"
    fi
  done
}

save_index_state() {
  local index="$1"
  mkdir -p "$STATE_DIR"
  if index_exists "$index"; then
    fetch_indexdef "$index" > "${STATE_DIR}/${index}.sql"
  fi
}

load_index_ddl() {
  local index="$1"
  local ddl=""

  if [[ -n "${INDEX_DDL[$index]+x}" ]]; then
    ddl="${INDEX_DDL[$index]}"
  elif [[ -f "${STATE_DIR}/${index}.sql" ]]; then
    ddl="$(cat "${STATE_DIR}/${index}.sql")"
  else
    echo "No DDL for index ${index}. Drop it first (saves indexdef) or add to INDEX_DDL." >&2
    return 1
  fi

  if [[ "$ddl" != *"IF NOT EXISTS"* ]]; then
    ddl="${ddl/CREATE INDEX /CREATE INDEX IF NOT EXISTS }"
  fi
  echo "$ddl"
}

cmd_list() {
  echo "=== Registry (explicit DDL) ==="
  for name in $(printf '%s\n' "${!INDEX_DDL[@]}" | sort); do
    echo "${name}"
    echo "  ${INDEX_DDL[$name]}"
  done

  echo ""
  echo "=== Groups ==="
  for group in $(printf '%s\n' "${!INDEX_GROUPS[@]}" | sort); do
    echo "${group}:"
    local names=()
    mapfile -t names < <(expand_group "$group")
    local name
    for name in "${names[@]}"; do
      [[ -z "$name" ]] && continue
      echo "  - ${name}"
    done
  done

  local category_idx
  category_idx="$(resolve_category_column_index || true)"
  echo ""
  echo "=== Resolved dynamic indexes ==="
  echo "  @category_column -> ${category_idx:-<not found>}"

  echo ""
  echo "=== Saved state (${STATE_DIR}) ==="
  if [[ -d "$STATE_DIR" ]] && compgen -G "${STATE_DIR}/*.sql" > /dev/null; then
    ls -1 "${STATE_DIR}"/*.sql | xargs -n1 basename
  else
    echo "  (none)"
  fi

  echo ""
  echo "=== Live Postgres indexes (lab tables) ==="
  run_psql "
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN ('catalog_product', 'orders_order', 'orders_orderitem')
    ORDER BY tablename, indexname;
  "
}

cmd_drop_one() {
  local index="$1"
  if [[ -z "$index" ]]; then
    echo "INDEX name required" >&2
    exit 1
  fi

  if index_exists "$index"; then
    save_index_state "$index"
    run_psql "DROP INDEX ${index};"
  else
    echo "Warning: index not found (already absent): ${index}" >&2
    return 0
  fi

  if index_exists "$index"; then
    echo "ERROR: index still exists after DROP: ${index}" >&2
    exit 1
  fi
  echo "Dropped index: ${index}"
}

cmd_add_one() {
  local index="$1"
  local ddl
  if [[ -z "$index" ]]; then
    echo "INDEX name required" >&2
    exit 1
  fi

  if index_exists "$index"; then
    echo "Index already present: ${index}"
    return 0
  fi

  ddl="$(load_index_ddl "$index")"
  run_psql "${ddl};"

  if ! index_exists "$index"; then
    echo "ERROR: index missing after CREATE: ${index}" >&2
    exit 1
  fi
  echo "Created index: ${index}"
}

cmd_drop_group() {
  local group="$1"
  local names=()
  mapfile -t names < <(expand_group "$group")
  local name
  for name in "${names[@]}"; do
    [[ -z "$name" ]] && continue
    cmd_drop_one "$name"
  done
}

cmd_add_group() {
  local group="$1"
  local names=()
  mapfile -t names < <(expand_group "$group")
  local name
  for name in "${names[@]}"; do
    [[ -z "$name" ]] && continue
    cmd_add_one "$name"
  done
}

cmd_verify_absent() {
  local index="$1"
  if index_exists "$index"; then
    echo "ERROR: expected absent, but index exists: ${index}" >&2
    exit 1
  fi
  echo "Verified absent: ${index}"
}

cmd_verify_present() {
  local index="$1"
  if ! index_exists "$index"; then
    echo "ERROR: expected present, but index missing: ${index}" >&2
    exit 1
  fi
  echo "Verified present: ${index}"
}

main() {
  local action="${1:-}"
  local target="${2:-}"

  case "$action" in
    list) cmd_list ;;
    drop) cmd_drop_one "$target" ;;
    add) cmd_add_one "$target" ;;
    drop-group) cmd_drop_group "$target" ;;
    add-group) cmd_add_group "$target" ;;
    verify-absent) cmd_verify_absent "$target" ;;
    verify-present) cmd_verify_present "$target" ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
