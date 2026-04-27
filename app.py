from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "last_resort.db"


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, params).fetchall()


def scalar(sql: str) -> int | float | str | None:
    rows = query(sql)
    return rows[0][0] if rows else None


def money(value: float | int | None) -> str:
    return f"${float(value or 0):,.0f}"


def number(value: float | int | None) -> str:
    return f"{int(value or 0):,}"


def pct(value: float | int | None) -> str:
    return f"{float(value or 0):.0f}%"


def table(headers: list[str], rows: list[sqlite3.Row], fields: list[str]) -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for label in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row[field] if row[field] is not None else ''))}</td>" for field in fields)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def dashboard() -> str:
    total_rooms = scalar("SELECT COUNT(*) FROM room")
    occupied_rooms = scalar("SELECT COUNT(*) FROM stay_room WHERE assignedEndDateTime IS NULL")
    active_events = scalar("SELECT COUNT(*) FROM event WHERE date(startDtTm) >= '2026-04-01'")
    total_charges = scalar("SELECT SUM(amount) FROM charge")
    total_payments = scalar("SELECT SUM(amount) FROM payment")
    outstanding = float(total_charges or 0) - float(total_payments or 0)
    occupancy_rate = (float(occupied_rooms or 0) / float(total_rooms or 1)) * 100

    occupancy_by_wing = query(
        """
        SELECT
            b.buildingName,
            w.wingCode,
            COUNT(DISTINCT r.roomId) AS room_count,
            COUNT(DISTINCT CASE WHEN sr.stayRoomId IS NOT NULL AND sr.assignedEndDateTime IS NULL THEN r.roomId END) AS occupied_count,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN sr.stayRoomId IS NOT NULL AND sr.assignedEndDateTime IS NULL THEN r.roomId END)
                / COUNT(DISTINCT r.roomId), 0) AS occupancy_percent
        FROM wing w
        JOIN building b ON w.buildingId = b.buildingId
        JOIN floor f ON w.wingId = f.wingId
        JOIN room r ON f.floorId = r.floorId
        LEFT JOIN stay_room sr ON r.roomId = sr.roomId
        GROUP BY b.buildingName, w.wingCode
        ORDER BY occupancy_percent DESC, w.wingSequenceNumber
        """
    )

    room_mix = query(
        """
        SELECT
            roomCategory,
            COUNT(*) AS room_count,
            SUM(maxSleepingCapacity) AS sleeping_capacity,
            SUM(maxMeetingCapacity) AS meeting_capacity,
            printf('$%.0f', AVG(baseDailyRate)) AS avg_rate
        FROM room
        GROUP BY roomCategory
        ORDER BY room_count DESC
        """
    )

    reservation_demand = query(
        """
        SELECT
            requestedRoomCategory,
            COUNT(*) AS total_requests,
            SUM(requestedSleepingCapacity) AS requested_sleeping_capacity,
            SUM(requestedMeetingCapacity) AS requested_meeting_capacity
        FROM reservation_room_request
        GROUP BY requestedRoomCategory
        ORDER BY total_requests DESC
        """
    )

    billing = query(
        """
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
            COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
            printf('$%.0f', COALESCE(c.total_charges, 0)) AS total_charges,
            printf('$%.0f', COALESCE(py.total_payments, 0)) AS total_payments,
            printf('$%.0f', COALESCE(c.total_charges, 0) - COALESCE(py.total_payments, 0)) AS outstanding_balance
        FROM billed_party bp
        LEFT JOIN organization o ON bp.organizationId = o.organizationId
        LEFT JOIN person p ON bp.personId = p.personId
        LEFT JOIN charges_by_party c ON bp.billedPartyId = c.billedPartyId
        LEFT JOIN payments_by_party py ON bp.billedPartyId = py.billedPartyId
        ORDER BY COALESCE(c.total_charges, 0) - COALESCE(py.total_payments, 0) DESC
        """
    )

    revenue = query(
        """
        SELECT
            COALESCE(si.serviceCategory, chargeType) AS revenue_category,
            COUNT(*) AS charge_count,
            printf('$%.0f', SUM(c.amount)) AS total_revenue,
            SUM(c.amount) AS raw_total
        FROM charge c
        LEFT JOIN service_item si ON c.serviceItemId = si.serviceItemId
        GROUP BY COALESCE(si.serviceCategory, chargeType)
        ORDER BY raw_total DESC
        """
    )

    events = query(
        """
        SELECT
            e.eventName,
            date(e.startDtTm) AS event_date,
            COUNT(fb.facilityBookingId) AS rooms_booked,
            SUM(fb.expectedAttendance) AS expected_attendance,
            GROUP_CONCAT(w.wingCode || ' ' || r.roomCategory || ' ' || r.roomNumberOnFloor, ', ') AS assigned_rooms
        FROM event e
        LEFT JOIN facility_booking fb ON e.eventId = fb.eventId
        LEFT JOIN room r ON fb.roomId = r.roomId
        LEFT JOIN floor f ON r.floorId = f.floorId
        LEFT JOIN wing w ON f.wingId = w.wingId
        GROUP BY e.eventId, e.eventName, e.startDtTm
        ORDER BY e.startDtTm
        """
    )

    deposits = query(
        """
        SELECT
            d.depositStatus,
            COUNT(*) AS deposit_count,
            printf('$%.0f', SUM(d.amount)) AS deposit_value
        FROM deposit d
        GROUP BY d.depositStatus
        ORDER BY SUM(d.amount) DESC
        """
    )

    guest_locations = query(
        """
        SELECT
            p.firstName || ' ' || p.lastName AS guest_name,
            COALESCE(o.organizationName, 'Independent guest') AS affiliation,
            s.stayStatus,
            COALESCE(w.wingCode || ' ' || r.roomNumberOnFloor, 'No active room') AS current_room
        FROM guest g
        JOIN person p ON g.personId = p.personId
        LEFT JOIN organization o ON g.organizationId = o.organizationId
        LEFT JOIN stay s ON g.guestId = s.guestId AND s.checkOutDateTime IS NULL
        LEFT JOIN stay_room sr ON s.stayId = sr.stayId AND sr.assignedEndDateTime IS NULL
        LEFT JOIN room r ON sr.roomId = r.roomId
        LEFT JOIN floor f ON r.floorId = f.floorId
        LEFT JOIN wing w ON f.wingId = w.wingId
        ORDER BY s.stayStatus DESC, guest_name
        """
    )

    max_revenue = max([float(row["raw_total"] or 0) for row in revenue] or [1])
    revenue_bars = "".join(
        f"""
        <div class="bar-row">
            <span>{html.escape(row['revenue_category'].title())}</span>
            <div class="bar-track"><div style="width:{(float(row['raw_total'] or 0) / max_revenue) * 100:.0f}%"></div></div>
            <strong>{html.escape(row['total_revenue'])}</strong>
        </div>
        """
        for row in revenue
    )

    wing_cards = "".join(
        f"""
        <article class="mini-card">
            <div>
                <span class="eyebrow">{html.escape(row['buildingName'])}</span>
                <h3>{html.escape(row['wingCode'])} Wing</h3>
            </div>
            <p class="big">{number(row['occupied_count'])}/{number(row['room_count'])}</p>
            <div class="meter"><span style="width:{float(row['occupancy_percent'] or 0):.0f}%"></span></div>
            <small>{pct(row['occupancy_percent'])} occupied</small>
        </article>
        """
        for row in occupancy_by_wing
    )

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Last Resort Operations Dashboard</title>
        <link rel="stylesheet" href="/static/styles.css">
    </head>
    <body>
        <header class="topbar">
            <div>
                <p class="eyebrow">Database-driven web demo</p>
                <h1>Last Resort Hotels Operations Dashboard</h1>
            </div>
            <nav>
                <a href="#capacity">Capacity</a>
                <a href="#billing">Billing</a>
                <a href="#events">Events</a>
                <a href="#queries">Queries</a>
            </nav>
        </header>

        <main>
            <section class="hero">
                <div>
                    <p class="eyebrow">Azure Sands Resort & Spa</p>
                    <h2>Current room usage, event demand, and billing exposure from the project database.</h2>
                    <p>This page is generated from SQLite tables for rooms, wings, reservations, stays, events, charges, deposits, and payments.</p>
                </div>
                <div class="kpi-grid">
                    <article><span>Total Rooms</span><strong>{number(total_rooms)}</strong></article>
                    <article><span>Occupied Now</span><strong>{number(occupied_rooms)}</strong></article>
                    <article><span>Occupancy</span><strong>{pct(occupancy_rate)}</strong></article>
                    <article><span>Outstanding</span><strong>{money(outstanding)}</strong></article>
                </div>
            </section>

            <section id="capacity" class="section">
                <div class="section-title">
                    <div>
                        <p class="eyebrow">Rooms and reservations</p>
                        <h2>Capacity Planning</h2>
                    </div>
                    <p>Shows how current usage compares with available room inventory and requested reservation needs.</p>
                </div>
                <div class="mini-grid">{wing_cards}</div>
                <div class="two-col">
                    <article class="panel">
                        <h3>Room Inventory Mix</h3>
                        {table(["Category", "Rooms", "Sleep Cap.", "Meeting Cap.", "Avg. Rate"], room_mix, ["roomCategory", "room_count", "sleeping_capacity", "meeting_capacity", "avg_rate"])}
                    </article>
                    <article class="panel">
                        <h3>Reservation Demand</h3>
                        {table(["Requested Category", "Requests", "Sleep Cap.", "Meeting Cap."], reservation_demand, ["requestedRoomCategory", "total_requests", "requested_sleeping_capacity", "requested_meeting_capacity"])}
                    </article>
                </div>
            </section>

            <section id="billing" class="section">
                <div class="section-title">
                    <div>
                        <p class="eyebrow">Charges, payments, deposits</p>
                        <h2>Billing Accountability</h2>
                    </div>
                    <p>Connects guests and hosts to the responsible billed party, then summarizes unpaid balances.</p>
                </div>
                <div class="two-col wide-left">
                    <article class="panel">
                        <h3>Outstanding Balance by Billed Party</h3>
                        {table(["ID", "Billed Party", "Charges", "Payments", "Outstanding"], billing, ["billedPartyId", "billed_party_name", "total_charges", "total_payments", "outstanding_balance"])}
                    </article>
                    <article class="panel">
                        <h3>Revenue Categories</h3>
                        <div class="bars">{revenue_bars}</div>
                        <h3 class="subhead">Deposit Status</h3>
                        {table(["Status", "Count", "Value"], deposits, ["depositStatus", "deposit_count", "deposit_value"])}
                    </article>
                </div>
            </section>

            <section id="events" class="section">
                <div class="section-title">
                    <div>
                        <p class="eyebrow">Meetings and guest location</p>
                        <h2>Coordination View</h2>
                    </div>
                    <p>Highlights scheduled event rooms and current guest locations for staff coordination.</p>
                </div>
                <div class="two-col">
                    <article class="panel">
                        <h3>Event Room Usage</h3>
                        {table(["Event", "Date", "Rooms", "Attendance", "Assigned Rooms"], events, ["eventName", "event_date", "rooms_booked", "expected_attendance", "assigned_rooms"])}
                    </article>
                    <article class="panel">
                        <h3>Guest Contact Snapshot</h3>
                        {table(["Guest", "Affiliation", "Status", "Current Room"], guest_locations, ["guest_name", "affiliation", "stayStatus", "current_room"])}
                    </article>
                </div>
            </section>

            <section id="queries" class="section">
                <div class="section-title">
                    <div>
                        <p class="eyebrow">Query-to-page map</p>
                        <h2>How SQL Results Appear in the Dashboard</h2>
                    </div>
                    <p>Each item below starts with what the query calculates, then points to where that result is shown on the web page.</p>
                </div>
                <ol class="query-list">
                    <li><strong>Occupied room count:</strong> shown in the Occupied Now KPI card.</li>
                    <li><strong>Occupancy by wing:</strong> shown in the Aqua, Lagoon, and Palm wing cards.</li>
                    <li><strong>Room capacity by category:</strong> shown in the Room Inventory Mix table.</li>
                    <li><strong>Reservation demand:</strong> shown in the Reservation Demand table.</li>
                    <li><strong>Charges, payments, and balances:</strong> shown in the Outstanding Balance by Billed Party table.</li>
                    <li><strong>Revenue by category:</strong> shown in the Revenue Categories bar chart.</li>
                    <li><strong>Deposit status totals:</strong> shown in the Deposit Status table.</li>
                    <li><strong>Event room usage:</strong> shown in the Event Room Usage table.</li>
                    <li><strong>Guest location snapshot:</strong> shown in the Guest Contact Snapshot table.</li>
                </ol>
            </section>
        </main>
    </body>
    </html>
    """


class RequestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/static/styles.css"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8" if path == "/" else "text/css; charset=utf-8")
            self.end_headers()
            return
        self.send_error(404, "Not found")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.respond(dashboard(), "text/html; charset=utf-8")
            return
        if path == "/static/styles.css":
            css = (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")
            self.respond(css, "text/css; charset=utf-8")
            return
        self.send_error(404, "Not found")

    def respond(self, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5000), RequestHandler)
    print("Last Resort web demo running at http://127.0.0.1:5000")
    server.serve_forever()
