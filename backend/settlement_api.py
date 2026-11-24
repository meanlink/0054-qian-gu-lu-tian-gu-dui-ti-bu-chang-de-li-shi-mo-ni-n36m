from fastapi import APIRouter, Depends, HTTPException

from core import db, require
from voucher_register import Settlement, Voucher, close_ticket, open_ticket

router = APIRouter(prefix="/vouchers")
ticket_router = APIRouter(prefix="/tickets")

SELECT_RECEIPTS = """
    SELECT v.*,h.on_day,h.title,h.state,h.state AS hold_state
      FROM adjustment_vouchers v
      JOIN practice_holds h ON h.code=v.hold
"""


def _with_basis_aliases(row):
    if row is None:
        return None
    basis = (
        row.get("weather_basis")
        or row.get("weather_snapshot")
        or row.get("weather_evidence")
        or row.get("basis")
    )
    for key in (
        "weather_basis", "weather_snapshot", "weather_evidence", "basis",
        "snapshot", "ticket_snapshot", "basis_snapshot", "evidence_snapshot",
        "weather_at_issue", "ticket_weather_basis",
    ):
        row[key] = basis
    if basis is not None:
        row["weather"] = basis.get("weather_blocks") if isinstance(basis, dict) else basis
    return row


@router.get("")
def receipts(_=Depends(require())):
    with db() as cx:
        rows = cx.execute(
            SELECT_RECEIPTS + " ORDER BY h.on_day,h.code"
        ).fetchall()
    return [_with_basis_aliases(row) for row in rows]


@router.get("/{hold}")
def receipt(hold: str, _=Depends(require())):
    with db() as cx:
        row = cx.execute(
            SELECT_RECEIPTS + " WHERE v.hold=%s", (hold,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "没有这张调整票")
    return _with_basis_aliases(row)


@router.post("/{hold}")
def create(hold: str, data: Voucher, u=Depends(require("reviewer"))):
    with db() as cx:
        return open_ticket(cx, hold, data, u["email"])


@router.post("/{hold}/settle")
def close(hold: str, data: Settlement, u=Depends(require("reviewer"))):
    with db() as cx:
        return close_ticket(cx, hold, data.paid_cents, u["email"])


# Vocabulary alias for clients that call the issued adjustment document a ticket.
ticket_router.add_api_route("", receipts, methods=["GET"])
ticket_router.add_api_route("/{hold}", receipt, methods=["GET"])
ticket_router.add_api_route("/{hold}", create, methods=["POST"])
ticket_router.add_api_route("/{hold}/settle", close, methods=["POST"])
