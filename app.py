from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "last_resort.db"

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with get_db() as conn:
        return conn.execute(sql, params).fetchall()


def scalar(sql: str, params: tuple[Any, ...] = ()) -> Any:
    rows = query(sql, params)
    return rows[0][0] if rows else None


def int_arg(name: str, default: int = 0) -> int:
    raw = request.args.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def float_arg(name: str, default: float = 0) -> float:
    raw = request.args.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, float(raw))
    except ValueError:
        return default


@app.template_filter("money")
def money(value: float | int | None) -> str:
    return f"${float(value or 0):,.0f}"


@app.template_filter("number")
def number(value: float | int | None) -> str:
    return f"{int(value or 0):,}"


@app.template_filter("pct")
def pct(value: float | int | None) -> str:
    return f"{float(value or 0):.0f}%"


def option_rows(table: str, column: str) -> list[str]:
    safe_options = {
        ("room", "roomCategory"),
        ("deposit", "depositStatus"),
        ("service_item", "serviceCategory"),
    }
    if (table, column) not in safe_options:
        return []
    rows = query(f"SELECT DISTINCT {column} FROM {table} ORDER BY {column}")
    return [row[0] for row in rows]


def dashboard_metrics() -> dict[str, Any]:
    total_rooms = scalar("SELECT COUNT(*) FROM room")
    occupied_rooms = scalar("SELECT COUNT(*) FROM stay_room WHERE assignedEndDateTime IS NULL")
    total_charges = scalar("SELECT SUM(amount) FROM charge")
    total_payments = scalar("SELECT SUM(amount) FROM payment")
    outstanding = float(total_charges or 0) - float(total_payments or 0)
    occupancy_rate = (float(occupied_rooms or 0) / float(total_rooms or 1)) * 100

    return {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "occupancy_rate": occupancy_rate,
        "outstanding": outstanding,
    }


def occupancy_by_wing() -> list[sqlite3.Row]:
    return query(
        """
        SELECT
            b.buildingName,
            w.wingCode,
            COUNT(DISTINCT r.roomId) AS room_count,
            COUNT(DISTINCT CASE
                WHEN sr.stayRoomId IS NOT NULL AND sr.assignedEndDateTime IS NULL THEN r.roomId
            END) AS occupied_count,
            ROUND(100.0 * COUNT(DISTINCT CASE
                WHEN sr.stayRoomId IS NOT NULL AND sr.assignedEndDateTime IS NULL THEN r.roomId
            END) / COUNT(DISTINCT r.roomId), 0) AS occupancy_percent
        FROM wing w
        JOIN building b ON w.buildingId = b.buildingId
        JOIN floor f ON w.wingId = f.wingId
        JOIN room r ON f.floorId = r.floorId
        LEFT JOIN stay_room sr ON r.roomId = sr.roomId
        GROUP BY b.buildingName, w.wingCode
        ORDER BY occupancy_percent DESC, w.wingSequenceNumber
        """
    )


def search_rooms() -> tuple[list[sqlite3.Row], dict[str, Any]]:
    filters: list[str] = []
    params: list[Any] = []

    category = request.args.get("room_category", "").strip()
    min_sleep = int_arg("min_sleep")
    min_meeting = int_arg("min_meeting")
    max_rate = float_arg("max_rate")
    near_pool = request.args.get("near_pool", "")
    accessible = request.args.get("accessible", "")

    if category:
        filters.append("r.roomCategory = ?")
        params.append(category)
    if min_sleep:
        filters.append("r.maxSleepingCapacity >= ?")
        params.append(min_sleep)
    if min_meeting:
        filters.append("r.maxMeetingCapacity >= ?")
        params.append(min_meeting)
    if max_rate:
        filters.append("r.baseDailyRate <= ?")
        params.append(max_rate)
    if near_pool == "1":
        filters.append("w.nearPool = ?")
        params.append(1)
    if accessible == "1":
        filters.append("w.hasHandicapAccess = ?")
        params.append(1)

    where = "WHERE " + " AND ".join(filters) if filters else ""
    rows = query(
        f"""
        SELECT
            r.roomId,
            b.buildingName,
            w.wingCode,
            f.floorNumber,
            r.roomNumberOnFloor,
            r.roomCategory,
            r.maxSleepingCapacity,
            r.maxMeetingCapacity,
            r.baseDailyRate,
            CASE WHEN r.hasBathroom = 1 THEN 'Yes' ELSE 'No' END AS hasBathroom,
            CASE WHEN w.nearPool = 1 THEN 'Yes' ELSE 'No' END AS nearPool,
            CASE WHEN w.hasHandicapAccess = 1 THEN 'Yes' ELSE 'No' END AS accessible,
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM stay_room sr
                    WHERE sr.roomId = r.roomId AND sr.assignedEndDateTime IS NULL
                ) THEN 'Occupied'
                ELSE 'Available'
            END AS currentStatus
        FROM room r
        JOIN floor f ON r.floorId = f.floorId
        JOIN wing w ON f.wingId = w.wingId
        JOIN building b ON w.buildingId = b.buildingId
        {where}
        ORDER BY b.buildingName, w.wingSequenceNumber, f.floorNumber, r.roomNumberOnFloor
        """,
        tuple(params),
    )
    selected = {
        "room_category": category,
        "min_sleep": min_sleep or "",
        "min_meeting": min_meeting or "",
        "max_rate": int(max_rate) if max_rate else "",
        "near_pool": near_pool,
        "accessible": accessible,
    }
    return rows, selected


def search_billing() -> tuple[list[sqlite3.Row], dict[str, Any]]:
    search = request.args.get("billing_search", "").strip()
    min_balance = float_arg("min_balance")

    filters: list[str] = []
    params: list[Any] = []
    if search:
        filters.append("(COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) LIKE ?)")
        params.append(f"%{search}%")
    if min_balance:
        filters.append("(COALESCE(c.total_charges, 0) - COALESCE(py.total_payments, 0)) >= ?")
        params.append(min_balance)
    where = "WHERE " + " AND ".join(filters) if filters else ""

    rows = query(
        f"""
        WITH charges_by_party AS (
            SELECT billedPartyId, SUM(amount) AS total_charges
            FROM charge
            GROUP BY billedPartyId
        ),
        payments_by_party AS (
            SELECT billedPartyId, SUM(amount) AS total_payments
            FROM payment
            GROUP BY billedPartyId
        )
        SELECT
            bp.billedPartyId,
            COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billedParty,
            COALESCE(c.total_charges, 0) AS totalCharges,
            COALESCE(py.total_payments, 0) AS totalPayments,
            COALESCE(c.total_charges, 0) - COALESCE(py.total_payments, 0) AS outstandingBalance
        FROM billed_party bp
        LEFT JOIN organization o ON bp.organizationId = o.organizationId
        LEFT JOIN person p ON bp.personId = p.personId
        LEFT JOIN charges_by_party c ON bp.billedPartyId = c.billedPartyId
        LEFT JOIN payments_by_party py ON bp.billedPartyId = py.billedPartyId
        {where}
        ORDER BY outstandingBalance DESC, billedParty
        """,
        tuple(params),
    )
    return rows, {"billing_search": search, "min_balance": int(min_balance) if min_balance else ""}


def search_events() -> tuple[list[sqlite3.Row], dict[str, Any]]:
    start_date = request.args.get("event_start", "").strip()
    end_date = request.args.get("event_end", "").strip()
    min_attendance = int_arg("min_attendance")

    filters: list[str] = []
    params: list[Any] = []
    if start_date:
        filters.append("date(e.startDtTm) >= ?")
        params.append(start_date)
    if end_date:
        filters.append("date(e.startDtTm) <= ?")
        params.append(end_date)
    if min_attendance:
        filters.append("COALESCE(e.estimatedAttendance, 0) >= ?")
        params.append(min_attendance)
    where = "WHERE " + " AND ".join(filters) if filters else ""

    rows = query(
        f"""
        SELECT
            e.eventName,
            date(e.startDtTm) AS eventDate,
            time(e.startDtTm) AS startTime,
            time(e.endDtTm) AS endTime,
            e.estimatedAttendance,
            e.estimatedGuestCount,
            COALESCE(GROUP_CONCAT(w.wingCode || ' ' || r.roomCategory || ' ' || r.roomNumberOnFloor, ', '), 'Not assigned') AS assignedRooms
        FROM event e
        LEFT JOIN facility_booking fb ON e.eventId = fb.eventId
        LEFT JOIN room r ON fb.roomId = r.roomId
        LEFT JOIN floor f ON r.floorId = f.floorId
        LEFT JOIN wing w ON f.wingId = w.wingId
        {where}
        GROUP BY e.eventId
        ORDER BY e.startDtTm
        """,
        tuple(params),
    )
    return rows, {
        "event_start": start_date,
        "event_end": end_date,
        "min_attendance": min_attendance or "",
    }


def search_guest_locations() -> tuple[list[sqlite3.Row], dict[str, Any]]:
    guest_search = request.args.get("guest_search", "").strip()
    only_checked_in = request.args.get("only_checked_in", "")

    filters: list[str] = []
    params: list[Any] = []
    if guest_search:
        filters.append("(p.firstName || ' ' || p.lastName LIKE ? OR COALESCE(o.organizationName, '') LIKE ?)")
        params.extend([f"%{guest_search}%", f"%{guest_search}%"])
    if only_checked_in == "1":
        filters.append("s.checkOutDateTime IS NULL AND s.stayId IS NOT NULL")
    where = "WHERE " + " AND ".join(filters) if filters else ""

    rows = query(
        f"""
        SELECT
            p.firstName || ' ' || p.lastName AS guestName,
            COALESCE(o.organizationName, 'Independent guest') AS affiliation,
            COALESCE(s.stayStatus, 'not currently checked in') AS stayStatus,
            COALESCE(w.wingCode || ' ' || r.roomNumberOnFloor, 'No active room') AS currentRoom
        FROM guest g
        JOIN person p ON g.personId = p.personId
        LEFT JOIN organization o ON g.organizationId = o.organizationId
        LEFT JOIN stay s ON g.guestId = s.guestId AND s.checkOutDateTime IS NULL
        LEFT JOIN stay_room sr ON s.stayId = sr.stayId AND sr.assignedEndDateTime IS NULL
        LEFT JOIN room r ON sr.roomId = r.roomId
        LEFT JOIN floor f ON r.floorId = f.floorId
        LEFT JOIN wing w ON f.wingId = w.wingId
        {where}
        ORDER BY s.stayStatus DESC, guestName
        """,
        tuple(params),
    )
    return rows, {"guest_search": guest_search, "only_checked_in": only_checked_in}


def revenue_by_category() -> list[sqlite3.Row]:
    return query(
        """
        SELECT
            COALESCE(si.serviceCategory, c.chargeType) AS revenueCategory,
            COUNT(*) AS chargeCount,
            SUM(c.amount) AS totalRevenue
        FROM charge c
        LEFT JOIN service_item si ON c.serviceItemId = si.serviceItemId
        GROUP BY COALESCE(si.serviceCategory, c.chargeType)
        ORDER BY totalRevenue DESC
        """
    )


def room_inventory_mix() -> list[sqlite3.Row]:
    return query(
        """
        SELECT
            roomCategory,
            COUNT(*) AS roomCount,
            SUM(maxSleepingCapacity) AS sleepingCapacity,
            SUM(maxMeetingCapacity) AS meetingCapacity,
            AVG(baseDailyRate) AS averageRate
        FROM room
        GROUP BY roomCategory
        ORDER BY roomCount DESC
        """
    )


def reservation_demand() -> list[sqlite3.Row]:
    return query(
        """
        SELECT
            requestedRoomCategory,
            COUNT(*) AS totalRequests,
            SUM(requestedSleepingCapacity) AS requestedSleepingCapacity,
            SUM(requestedMeetingCapacity) AS requestedMeetingCapacity
        FROM reservation_room_request
        GROUP BY requestedRoomCategory
        ORDER BY totalRequests DESC
        """
    )


def deposit_status() -> list[sqlite3.Row]:
    return query(
        """
        SELECT
            depositStatus,
            COUNT(*) AS depositCount,
            SUM(amount) AS depositValue
        FROM deposit
        GROUP BY depositStatus
        ORDER BY depositValue DESC
        """
    )


def original_query_outputs() -> dict[str, list[sqlite3.Row]]:
    return {
        "q1": query(
            """
            SELECT COUNT(*) AS occupied_rooms
            FROM stay_room
            WHERE assignedEndDateTime IS NULL
            """
        ),
        "q2": query(
            """
            SELECT w.wingCode,
                   COUNT(sr.stayRoomId) AS occupied_room_count
            FROM stay_room sr
            JOIN room r ON sr.roomId = r.roomId
            JOIN floor f ON r.floorId = f.floorId
            JOIN wing w ON f.wingId = w.wingId
            WHERE sr.assignedEndDateTime IS NULL
            GROUP BY w.wingCode
            ORDER BY occupied_room_count DESC
            """
        ),
        "q3": query(
            """
            SELECT requestedRoomCategory,
                   COUNT(*) AS total_requests
            FROM reservation_room_request
            GROUP BY requestedRoomCategory
            ORDER BY total_requests DESC
            """
        ),
        "q4": query(
            """
            SELECT bp.billedPartyId,
                   COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
                   SUM(c.amount) AS total_charges
            FROM billed_party bp
            LEFT JOIN organization o ON bp.organizationId = o.organizationId
            LEFT JOIN person p ON bp.personId = p.personId
            JOIN charge c ON bp.billedPartyId = c.billedPartyId
            GROUP BY bp.billedPartyId, billed_party_name
            ORDER BY total_charges DESC
            """
        ),
        "q5": query(
            """
            SELECT bp.billedPartyId,
                   COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
                   SUM(py.amount) AS total_payments
            FROM billed_party bp
            LEFT JOIN organization o ON bp.organizationId = o.organizationId
            LEFT JOIN person p ON bp.personId = p.personId
            JOIN payment py ON bp.billedPartyId = py.billedPartyId
            GROUP BY bp.billedPartyId, billed_party_name
            ORDER BY total_payments DESC
            """
        ),
        "q6": query(
            """
            SELECT bp.billedPartyId,
                   COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
                   COALESCE(c.total_charges, 0) AS total_charges,
                   COALESCE(py.total_payments, 0) AS total_payments,
                   COALESCE(c.total_charges, 0) - COALESCE(py.total_payments, 0) AS outstanding_balance
            FROM billed_party bp
            LEFT JOIN organization o ON bp.organizationId = o.organizationId
            LEFT JOIN person p ON bp.personId = p.personId
            LEFT JOIN (
                SELECT billedPartyId, SUM(amount) AS total_charges
                FROM charge
                GROUP BY billedPartyId
            ) c ON bp.billedPartyId = c.billedPartyId
            LEFT JOIN (
                SELECT billedPartyId, SUM(amount) AS total_payments
                FROM payment
                GROUP BY billedPartyId
            ) py ON bp.billedPartyId = py.billedPartyId
            ORDER BY outstanding_balance DESC
            """
        ),
        "q7": query(
            """
            SELECT si.serviceCategory,
                   SUM(c.amount) AS total_service_revenue
            FROM charge c
            JOIN service_item si ON c.serviceItemId = si.serviceItemId
            GROUP BY si.serviceCategory
            ORDER BY total_service_revenue DESC
            """
        ),
        "q8": query(
            """
            SELECT e.eventName,
                   COUNT(fb.facilityBookingId) AS rooms_booked,
                   SUM(fb.expectedAttendance) AS total_expected_attendance
            FROM event e
            JOIN facility_booking fb ON e.eventId = fb.eventId
            GROUP BY e.eventId, e.eventName
            ORDER BY rooms_booked DESC
            """
        ),
    }


@app.route("/")
def overview() -> str:
    return render_template(
        "overview.html",
        active_page="overview",
        metrics=dashboard_metrics(),
        occupancy=occupancy_by_wing(),
        inventory=room_inventory_mix(),
        demand=reservation_demand(),
        revenue=revenue_by_category(),
        deposits=deposit_status(),
    )


@app.route("/rooms")
def rooms() -> str:
    room_rows, room_filters = search_rooms()

    return render_template(
        "rooms.html",
        active_page="rooms",
        rooms=room_rows,
        room_filters=room_filters,
        room_categories=option_rows("room", "roomCategory"),
    )


@app.route("/billing")
def billing() -> str:
    billing_rows, billing_filters = search_billing()

    return render_template(
        "billing.html",
        active_page="billing",
        billing=billing_rows,
        billing_filters=billing_filters,
        revenue=revenue_by_category(),
        deposits=deposit_status(),
    )


@app.route("/events")
def events() -> str:
    event_rows, event_filters = search_events()

    return render_template(
        "events.html",
        active_page="events",
        events=event_rows,
        event_filters=event_filters,
    )


@app.route("/guests")
def guests() -> str:
    guest_rows, guest_filters = search_guest_locations()

    return render_template(
        "guests.html",
        active_page="guests",
        guests=guest_rows,
        guest_filters=guest_filters,
    )


@app.route("/query-outputs")
def query_outputs() -> str:
    return render_template(
        "query_outputs.html",
        active_page="queries",
        outputs=original_query_outputs(),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
