"""Real row-lock tests; CI runs these against PostgreSQL 16, not SQLite."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, connections

from apps.accounts.models import User
from apps.payments.models import InvoiceReservation
from apps.payments.services.checkout import create_payment, quote


@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_competing_partial_payments_serialize(world):
    """Two requests cannot reserve more principal than the same invoice balance."""
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    quotes = [
        quote(world["user"], world["invoice"].pk, "70", world["merchant"].pk, "card", "USD")
        for _ in range(2)
    ]
    barrier = Barrier(2)

    def attempt(index):
        """Run checkout on a dedicated connection after synchronising the callers."""
        close_old_connections()
        user = User.objects.get(pk=world["user"].pk)
        barrier.wait()
        try:
            create_payment(user, quotes[index].pk, "concurrent-" + str(index))
            return "created"
        except ValueError:
            return "rejected"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, [0, 1]))
    assert sorted(outcomes) == ["created", "rejected"]
    assert InvoiceReservation.objects.filter(status="active").count() == 1
