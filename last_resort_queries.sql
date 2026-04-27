# Q1: Current occupied rooms
SELECT 'Q1 Current occupied rooms';
SELECT COUNT(*) AS occupied_rooms
FROM stay_room
WHERE assignedEndDateTime IS NULL;

# Q2: Current occupancy by wing
SELECT 'Q2 Current occupancy by wing';
SELECT w.wingCode,
       COUNT(sr.stayRoomId) AS occupied_room_count
FROM stay_room sr
JOIN room r
    ON sr.roomId = r.roomId
JOIN floor f
    ON r.floorId = f.floorId
JOIN wing w
    ON f.wingId = w.wingId
WHERE sr.assignedEndDateTime IS NULL
GROUP BY w.wingCode
ORDER BY occupied_room_count DESC;

# Q3: Reservation demand by room category
SELECT 'Q3 Reservation demand by room category';
SELECT requestedRoomCategory,
       COUNT(*) AS total_requests
FROM reservation_room_request
GROUP BY requestedRoomCategory
ORDER BY total_requests DESC;

# Q4: Total charges by billed party
SELECT 'Q4 Total charges by billed party';
SELECT bp.billedPartyId,
       COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
       SUM(c.amount) AS total_charges
FROM billed_party bp
LEFT JOIN organization o
    ON bp.organizationId = o.organizationId
LEFT JOIN person p
    ON bp.personId = p.personId
JOIN charge c
    ON bp.billedPartyId = c.billedPartyId
GROUP BY bp.billedPartyId, billed_party_name
ORDER BY total_charges DESC;

# Q5: Total payments by billed party
SELECT 'Q5 Total payments by billed party';
SELECT bp.billedPartyId,
       COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
       SUM(py.amount) AS total_payments
FROM billed_party bp
LEFT JOIN organization o
    ON bp.organizationId = o.organizationId
LEFT JOIN person p
    ON bp.personId = p.personId
JOIN payment py
    ON bp.billedPartyId = py.billedPartyId
GROUP BY bp.billedPartyId, billed_party_name
ORDER BY total_payments DESC;

# Q6: Outstanding balance by billed party
SELECT 'Q6 Outstanding balance by billed party';
SELECT bp.billedPartyId,
       COALESCE(o.organizationName, p.firstName || ' ' || p.lastName) AS billed_party_name,
       COALESCE(c.total_charges, 0) AS total_charges,
       COALESCE(py.total_payments, 0) AS total_payments,
       COALESCE(c.total_charges, 0) - COALESCE(py.total_payments, 0) AS outstanding_balance
FROM billed_party bp
LEFT JOIN organization o
    ON bp.organizationId = o.organizationId
LEFT JOIN person p
    ON bp.personId = p.personId
LEFT JOIN (
    SELECT billedPartyId, SUM(amount) AS total_charges
    FROM charge
    GROUP BY billedPartyId
) c
    ON bp.billedPartyId = c.billedPartyId
LEFT JOIN (
    SELECT billedPartyId, SUM(amount) AS total_payments
    FROM payment
    GROUP BY billedPartyId
) py
    ON bp.billedPartyId = py.billedPartyId
ORDER BY outstanding_balance DESC;

# Q7: Revenue by service category
SELECT 'Q7 Revenue by service category';
SELECT si.serviceCategory,
       SUM(c.amount) AS total_service_revenue
FROM charge c
JOIN service_item si
    ON c.serviceItemId = si.serviceItemId
GROUP BY si.serviceCategory
ORDER BY total_service_revenue DESC;

# Q8: Event room usage summary
SELECT 'Q8 Event room usage summary';
SELECT e.eventName,
       COUNT(fb.facilityBookingId) AS rooms_booked,
       SUM(fb.expectedAttendance) AS total_expected_attendance
FROM event e
JOIN facility_booking fb
    ON e.eventId = fb.eventId
GROUP BY e.eventId, e.eventName
ORDER BY rooms_booked DESC;
