import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.db_observe import SCENARIOS, is_postgresql, scan_type, scenario_sql


@pytest.mark.parametrize(
    "scenario_name,expected_fragment",
    [
        ("category_list", "category"),
        ("catalog_list", "catalog_product"),
        ("product_detail", "catalog_product"),
        ("orders_by_status", "orders_order"),
        ("order_items", "orders_orderitem"),
    ],
)
def test_scenario_sql_contains_expected_tables(scenario_name, expected_fragment):
    sql, _params = scenario_sql(SCENARIOS[scenario_name])
    assert expected_fragment in sql.lower()


def test_scan_type_detects_seq_scan():
    plan = [
        "Seq Scan on catalog_product  (cost=0.00..123.00 rows=100 width=64)",
        "  Filter: (category = 'electronics'::text)",
    ]
    assert scan_type(plan) == "Seq Scan"


def test_scan_type_detects_index_scan():
    plan = [
        "Index Scan using catalog_pro_categor_da8cc9_idx on catalog_product",
        "  Index Cond: (category = 'electronics'::text)",
    ]
    assert scan_type(plan) == "Index Scan"


def test_scan_type_detects_index_only_scan():
    plan = ["Index Only Scan using catalog_product_pkey on catalog_product"]
    assert scan_type(plan) == "Index Scan"


@pytest.mark.django_db
def test_db_observe_requires_postgresql():
    if is_postgresql():
        pytest.skip("Requires non-PostgreSQL test database")

    with pytest.raises(CommandError, match="requires PostgreSQL"):
        call_command("db_observe", "--explain")
