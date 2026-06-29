from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.core.db_observe import (
    LAB_TABLES,
    SCENARIOS,
    is_postgresql,
    scan_type,
    scenario_sql,
)


class Command(BaseCommand):
    help = "Observe database index usage via EXPLAIN, pg_indexes, and pg_stat views"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--explain",
            action="store_true",
            help="Run EXPLAIN (ANALYZE, BUFFERS) for lab query scenarios (default)",
        )
        group.add_argument(
            "--list-indexes",
            action="store_true",
            help="List indexes on catalog and orders tables",
        )
        group.add_argument(
            "--index-stats",
            action="store_true",
            help="Show pg_stat_user_indexes and table scan stats",
        )
        group.add_argument(
            "--reset-stats",
            action="store_true",
            help="Reset pg_stat_statements and pg_stat counters",
        )
        parser.add_argument(
            "--scenario",
            choices=sorted(SCENARIOS.keys()),
            help="Run a single EXPLAIN scenario instead of all",
        )

    def handle(self, *args, **options):
        if not is_postgresql():
            raise CommandError(
                "db_observe requires PostgreSQL. Current backend: "
                f"{connection.vendor}."
            )

        if options["list_indexes"]:
            self._list_indexes()
        elif options["index_stats"]:
            self._index_stats()
        elif options["reset_stats"]:
            self._reset_stats()
        else:
            self._explain(options.get("scenario"))

    def _explain(self, scenario_name: str | None) -> None:
        scenarios = (
            [SCENARIOS[scenario_name]]
            if scenario_name
            else [SCENARIOS[name] for name in sorted(SCENARIOS.keys())]
        )

        for scenario in scenarios:
            sql, params = scenario_sql(scenario)
            self.stdout.write(self.style.MIGRATE_HEADING(scenario.name))
            self.stdout.write(scenario.description)
            self.stdout.write(f"SQL: {sql}")
            if params:
                self.stdout.write(f"Params: {params}")

            with connection.cursor() as cursor:
                cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS) {sql}", params)
                plan_lines = [row[0] for row in cursor.fetchall()]

            for line in plan_lines:
                self.stdout.write(line)

            detected = scan_type(plan_lines)
            if detected == "Seq Scan":
                self.stdout.write(self.style.WARNING("Scan type: Seq Scan"))
            elif detected == "Index Scan":
                self.stdout.write(self.style.SUCCESS("Scan type: Index Scan"))
            else:
                self.stdout.write("Scan type: unknown")
            self.stdout.write("")

    def _list_indexes(self) -> None:
        placeholders = ", ".join(["%s"] * len(LAB_TABLES))
        query = f"""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename IN ({placeholders})
            ORDER BY tablename, indexname
        """
        with connection.cursor() as cursor:
            cursor.execute(query, LAB_TABLES)
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write("No indexes found for lab tables.")
            return

        current_table = None
        for tablename, indexname, indexdef in rows:
            if tablename != current_table:
                current_table = tablename
                self.stdout.write(self.style.MIGRATE_HEADING(tablename))
            self.stdout.write(f"  {indexname}")
            self.stdout.write(f"    {indexdef}")

    def _index_stats(self) -> None:
        query = """
            SELECT
                s.relname AS table_name,
                s.indexrelname AS index_name,
                s.idx_scan,
                s.idx_tup_read,
                s.idx_tup_fetch,
                t.seq_scan,
                t.seq_tup_read
            FROM pg_stat_user_indexes s
            JOIN pg_stat_user_tables t ON s.relid = t.relid
            WHERE s.schemaname = 'public'
              AND s.relname = ANY(%s)
            ORDER BY s.relname, s.indexrelname
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [list(LAB_TABLES)])
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write("No index stats available yet.")
            return

        self.stdout.write(
            f"{'Table':<20} {'Index':<35} {'idx_scan':>10} {'seq_scan':>10}"
        )
        self.stdout.write("-" * 80)
        for (
            table_name,
            index_name,
            idx_scan,
            _idx_tup_read,
            _idx_tup_fetch,
            seq_scan,
            _seq_tup_read,
        ) in rows:
            self.stdout.write(
                f"{table_name:<20} {index_name:<35} {idx_scan:>10} {seq_scan:>10}"
            )

    def _reset_stats(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_stat_statements_reset()")
            cursor.execute("SELECT pg_stat_reset()")
        self.stdout.write(self.style.SUCCESS("Reset pg_stat_statements and pg_stat."))
