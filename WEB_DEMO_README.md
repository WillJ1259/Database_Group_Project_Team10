# Last Resort Web Demo

This web interface is the Item 5 demo for the database project. It is a multi-page Flask portal that reads directly from `last_resort.db` and presents query results for hotel operations, billing, room capacity, event scheduling, and guest coordination.

## How to Run

From this folder:

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The app uses Flask with the existing SQLite database file. User inputs from the forms are passed into SQLite with parameterized query placeholders instead of being concatenated into SQL strings.

## Interactive Query Features

The portal includes four user-facing query forms:

1. Room search by category, sleeping capacity, meeting capacity, maximum rate, pool proximity, and accessibility.
2. Billing search by billed party name and minimum outstanding balance.
3. Event search by date range and minimum expected attendance.
4. Guest search by guest/organization name, with an option to show only currently checked-in guests.

## Query-to-Page Map

The portal includes a dedicated Query Outputs page showing all eight outputs from `last_resort_queries.sql`. Those outputs also correspond to staff-facing portal pages:

1. Q1 current occupied room count appears in the Overview KPI cards.
2. Q2 current occupancy by wing appears in the Overview wing cards.
3. Q3 reservation demand appears in the Overview Reservation Demand table.
4. Q4 total charges by billed party appears on the Billing page.
5. Q5 total payments by billed party appears on the Billing page.
6. Q6 outstanding balance by billed party appears on the Billing page.
7. Q7 revenue by service category appears on the Billing page.
8. Q8 event room usage summary appears on the Events page.

These views use joins, grouping, aggregation, and computed balances to turn raw records into useful operational summaries.
