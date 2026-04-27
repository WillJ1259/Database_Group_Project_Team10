PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS charge;
DROP TABLE IF EXISTS service_item;
DROP TABLE IF EXISTS facility_booking;
DROP TABLE IF EXISTS event;
DROP TABLE IF EXISTS stay_room;
DROP TABLE IF EXISTS stay;
DROP TABLE IF EXISTS deposit;
DROP TABLE IF EXISTS reservation_room_request;
DROP TABLE IF EXISTS reservation_guest;
DROP TABLE IF EXISTS reservation;
DROP TABLE IF EXISTS billed_party;
DROP TABLE IF EXISTS guest;
DROP TABLE IF EXISTS organization;
DROP TABLE IF EXISTS person;
DROP TABLE IF EXISTS room_bed;
DROP TABLE IF EXISTS bed_type;
DROP TABLE IF EXISTS room_adjacency;
DROP TABLE IF EXISTS room;
DROP TABLE IF EXISTS floor;
DROP TABLE IF EXISTS wing;
DROP TABLE IF EXISTS building;
DROP TABLE IF EXISTS hotel_complex;

CREATE TABLE hotel_complex (
    hotelId INTEGER PRIMARY KEY,
    hotelName TEXT NOT NULL,
    street TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zipCode TEXT NOT NULL,
    mainPhone TEXT
);

CREATE TABLE building (
    buildingId INTEGER PRIMARY KEY,
    hotelId INTEGER NOT NULL,
    buildingName TEXT NOT NULL,
    FOREIGN KEY (hotelId) REFERENCES hotel_complex(hotelId)
);

CREATE TABLE wing (
    wingId INTEGER PRIMARY KEY,
    buildingId INTEGER NOT NULL,
    wingCode TEXT NOT NULL,
    wingSequenceNumber INTEGER NOT NULL,
    nearPool INTEGER NOT NULL,
    nearParkingGarage INTEGER NOT NULL,
    hasHandicapAccess INTEGER NOT NULL,
    wingDescription TEXT,
    FOREIGN KEY (buildingId) REFERENCES building(buildingId),
    UNIQUE (buildingId, wingCode),
    UNIQUE (buildingId, wingSequenceNumber)
);

CREATE TABLE floor (
    floorId INTEGER PRIMARY KEY,
    wingId INTEGER NOT NULL,
    floorNumber INTEGER NOT NULL,
    isNonSmokingFloor INTEGER NOT NULL,
    FOREIGN KEY (wingId) REFERENCES wing(wingId),
    UNIQUE (wingId, floorNumber)
);

CREATE TABLE room (
    roomId INTEGER PRIMARY KEY,
    floorId INTEGER NOT NULL,
    roomNumberOnFloor TEXT NOT NULL,
    baseDailyRate REAL NOT NULL,
    roomCategory TEXT NOT NULL,
    maxSleepingCapacity INTEGER NOT NULL,
    maxMeetingCapacity INTEGER NOT NULL,
    hasBathroom INTEGER NOT NULL,
    isSmokingAllowed INTEGER NOT NULL,
    parentRoomId INTEGER,
    FOREIGN KEY (floorId) REFERENCES floor(floorId),
    FOREIGN KEY (parentRoomId) REFERENCES room(roomId),
    UNIQUE (floorId, roomNumberOnFloor)
);

CREATE TABLE room_adjacency (
    roomAdjacencyId INTEGER PRIMARY KEY,
    roomId INTEGER NOT NULL,
    adjacentRoomId INTEGER NOT NULL,
    adjacencyType TEXT NOT NULL,
    FOREIGN KEY (roomId) REFERENCES room(roomId),
    FOREIGN KEY (adjacentRoomId) REFERENCES room(roomId),
    UNIQUE (roomId, adjacentRoomId)
);

CREATE TABLE bed_type (
    bedTypeId INTEGER PRIMARY KEY,
    bedSizeName TEXT NOT NULL UNIQUE
);

CREATE TABLE room_bed (
    roomBedId INTEGER PRIMARY KEY,
    roomId INTEGER NOT NULL,
    bedTypeId INTEGER NOT NULL,
    bedCount INTEGER NOT NULL,
    FOREIGN KEY (roomId) REFERENCES room(roomId),
    FOREIGN KEY (bedTypeId) REFERENCES bed_type(bedTypeId),
    UNIQUE (roomId, bedTypeId)
);

CREATE TABLE person (
    personId INTEGER PRIMARY KEY,
    firstName TEXT NOT NULL,
    lastName TEXT NOT NULL,
    phone TEXT,
    email TEXT
);

CREATE TABLE organization (
    organizationId INTEGER PRIMARY KEY,
    organizationName TEXT NOT NULL,
    phone TEXT,
    email TEXT
);

CREATE TABLE guest (
    guestId INTEGER PRIMARY KEY,
    personId INTEGER NOT NULL,
    organizationId INTEGER,
    FOREIGN KEY (personId) REFERENCES person(personId),
    FOREIGN KEY (organizationId) REFERENCES organization(organizationId),
    UNIQUE (personId)
);

CREATE TABLE billed_party (
    billedPartyId INTEGER PRIMARY KEY,
    organizationId INTEGER,
    personId INTEGER,
    billingPhone TEXT,
    billingEmail TEXT,
    FOREIGN KEY (organizationId) REFERENCES organization(organizationId),
    FOREIGN KEY (personId) REFERENCES person(personId)
);

CREATE TABLE reservation (
    reservationId INTEGER PRIMARY KEY,
    hotelId INTEGER NOT NULL,
    billedPartyId INTEGER NOT NULL,
    personId INTEGER NOT NULL,
    createdDateTime TEXT NOT NULL,
    arrivalDate TEXT NOT NULL,
    departureDate TEXT NOT NULL,
    reservationStatus TEXT NOT NULL,
    FOREIGN KEY (hotelId) REFERENCES hotel_complex(hotelId),
    FOREIGN KEY (billedPartyId) REFERENCES billed_party(billedPartyId),
    FOREIGN KEY (personId) REFERENCES person(personId)
);

CREATE TABLE reservation_guest (
    reservationGuestId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL,
    guestId INTEGER NOT NULL,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (guestId) REFERENCES guest(guestId),
    UNIQUE (reservationId, guestId)
);

CREATE TABLE reservation_room_request (
    reservationRoomRequestId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL,
    requestedRoomCategory TEXT NOT NULL,
    requestedSmokingPreference TEXT NOT NULL,
    requestedSleepingCapacity INTEGER NOT NULL,
    requestedMeetingCapacity INTEGER NOT NULL,
    requestedNearPool INTEGER NOT NULL,
    requestedNearParkingGarage INTEGER NOT NULL,
    requestedHandicapAccess INTEGER NOT NULL,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId)
);

CREATE TABLE deposit (
    depositId INTEGER PRIMARY KEY,
    reservationId INTEGER NOT NULL,
    billedPartyId INTEGER NOT NULL,
    amount REAL NOT NULL,
    dueDate TEXT NOT NULL,
    receivedDate TEXT,
    depositStatus TEXT NOT NULL,
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (billedPartyId) REFERENCES billed_party(billedPartyId)
);

CREATE TABLE stay (
    stayId INTEGER PRIMARY KEY,
    hotelId INTEGER NOT NULL,
    reservationId INTEGER,
    guestId INTEGER NOT NULL,
    checkInDateTime TEXT NOT NULL,
    checkOutDateTime TEXT,
    stayStatus TEXT NOT NULL,
    FOREIGN KEY (hotelId) REFERENCES hotel_complex(hotelId),
    FOREIGN KEY (reservationId) REFERENCES reservation(reservationId),
    FOREIGN KEY (guestId) REFERENCES guest(guestId)
);

CREATE TABLE stay_room (
    stayRoomId INTEGER PRIMARY KEY,
    stayId INTEGER NOT NULL,
    roomId INTEGER NOT NULL,
    assignedStartDateTime TEXT NOT NULL,
    assignedEndDateTime TEXT,
    FOREIGN KEY (stayId) REFERENCES stay(stayId),
    FOREIGN KEY (roomId) REFERENCES room(roomId)
);

CREATE TABLE event (
    eventId INTEGER PRIMARY KEY,
    hotelId INTEGER NOT NULL,
    billedPartyId INTEGER NOT NULL,
    eventName TEXT NOT NULL,
    startDtTm TEXT NOT NULL,
    endDtTm TEXT NOT NULL,
    estimatedAttendance INTEGER,
    estimatedGuestCount INTEGER,
    FOREIGN KEY (hotelId) REFERENCES hotel_complex(hotelId),
    FOREIGN KEY (billedPartyId) REFERENCES billed_party(billedPartyId)
);

CREATE TABLE facility_booking (
    facilityBookingId INTEGER PRIMARY KEY,
    eventId INTEGER NOT NULL,
    roomId INTEGER NOT NULL,
    bookingStartDateTime TEXT NOT NULL,
    bookingEndDateTime TEXT NOT NULL,
    bookingStatus TEXT NOT NULL,
    expectedAttendance INTEGER,
    FOREIGN KEY (eventId) REFERENCES event(eventId),
    FOREIGN KEY (roomId) REFERENCES room(roomId)
);

CREATE TABLE service_item (
    serviceItemId INTEGER PRIMARY KEY,
    serviceName TEXT NOT NULL,
    serviceCategory TEXT NOT NULL,
    standardUnitPrice REAL NOT NULL
);

CREATE TABLE charge (
    chargeId INTEGER PRIMARY KEY,
    billedPartyId INTEGER NOT NULL,
    stayId INTEGER,
    facilityBookingId INTEGER,
    serviceItemId INTEGER,
    chargeType TEXT NOT NULL,
    chargeDateTime TEXT NOT NULL,
    chargeDescription TEXT,
    amount REAL NOT NULL,
    FOREIGN KEY (billedPartyId) REFERENCES billed_party(billedPartyId),
    FOREIGN KEY (stayId) REFERENCES stay(stayId),
    FOREIGN KEY (facilityBookingId) REFERENCES facility_booking(facilityBookingId),
    FOREIGN KEY (serviceItemId) REFERENCES service_item(serviceItemId)
);

CREATE TABLE payment (
    paymentId INTEGER PRIMARY KEY,
    billedPartyId INTEGER NOT NULL,
    paymentDateTime TEXT NOT NULL,
    amount REAL NOT NULL,
    paymentMethod TEXT NOT NULL,
    paymentReference TEXT,
    FOREIGN KEY (billedPartyId) REFERENCES billed_party(billedPartyId)
);

INSERT INTO hotel_complex VALUES 
(1, 'Azure Sands Resort & Spa', '880 Coral Bay Drive', 'Key Biscayne', 'FL', '33149', '305-777-8899');

INSERT INTO building VALUES 
(1, 1, 'Coral Tower'),
(2, 1, 'Laguna Suites');

INSERT INTO wing VALUES 
(1, 1, 'Aqua', 1, 1, 0, 1, 'Ocean-facing luxury wing'),
(2, 1, 'Palm', 2, 0, 1, 1, 'Garden-facing, near parking'),
(3, 2, 'Lagoon', 1, 1, 1, 1, 'Premium event and conference wing');

INSERT INTO floor VALUES 
(1, 1, 1, 1),
(2, 1, 2, 1),
(3, 2, 1, 0),
(4, 3, 1, 1);

INSERT INTO room VALUES 
(1, 1, '101', 180, 'sleeping', 2, 0, 1, 0, NULL),
(2, 1, '102', 320, 'suite', 4, 2, 1, 0, NULL),
(3, 2, '201', 140, 'sleeping', 2, 0, 1, 1, NULL),
(4, 3, '101', 450, 'meeting', 0, 60, 1, 0, NULL),
(5, 4, '101', 750, 'meeting', 0, 120, 1, 0, NULL),
(6, 4, '102', 900, 'hybrid', 2, 40, 1, 0, NULL);

INSERT INTO room_adjacency VALUES 
(1, 1, 2, 'door'),
(2, 4, 5, 'movable_wall'),
(3, 5, 6, 'door');

INSERT INTO bed_type VALUES 
(1, 'Queen'),
(2, 'King'),
(3, 'California King');

INSERT INTO room_bed VALUES 
(1, 1, 1, 1),
(2, 2, 2, 2),
(3, 3, 1, 2),
(4, 6, 3, 1);

INSERT INTO person VALUES 
(1, 'Elena', 'Marquez', '+52-55-5555-1010', 'elena.marquez@email.com'),
(2, 'Daniel', 'Kim', '+1-917-555-2020', 'daniel.kim@email.com'),
(3, 'Sofia', 'Rossi', '+1-646-555-3030', 'sofia.rossi@email.com'),
(4, 'Marcus', 'Chen', '+1-718-555-4040', 'marcus.chen@email.com'),
(5, 'Valeria', 'Ortega', '+52-998-555-5050', 'valeria.ortega@email.com'),
(6, 'James', 'Walker', '+1-212-555-6060', 'james.walker@email.com');

INSERT INTO organization VALUES 
(1, 'NeuroLink Analytics', '212-999-8888', 'contact@neurolink.com'),
(2, 'BlueWave Ventures', '305-888-7777', 'info@bluewavevc.com'),
(3, 'Solstice Creative Group', '+52-55-7777-1212', 'hello@solsticecg.com');

INSERT INTO guest VALUES 
(1, 1, NULL),
(2, 2, NULL),
(3, 3, 1),
(4, 4, 2),
(5, 5, 3),
(6, 6, NULL);

INSERT INTO billed_party VALUES 
(1, NULL, 1, '+52-55-5555-1010', 'elena.marquez@email.com'),
(2, 1, NULL, '+1-212-999-8888', 'billing@neurolink.com'),
(3, 2, NULL, '+1-305-888-7777', 'finance@bluewavevc.com'),
(4, 3, NULL, '+52-55-7777-1212', 'accounts@solsticecg.com');

INSERT INTO reservation VALUES 
(1, 1, 1, 1, '2026-03-20 10:00:00', '2026-04-05', '2026-04-08', 'confirmed'),
(2, 1, 2, 2, '2026-03-22 14:30:00', '2026-04-10', '2026-04-13', 'confirmed'),
(3, 1, 3, 4, '2026-03-25 09:15:00', '2026-04-12', '2026-04-14', 'confirmed'),
(4, 1, 4, 5, '2026-03-28 16:20:00', '2026-04-18', '2026-04-20', 'pending');

INSERT INTO reservation_guest VALUES 
(1, 1, 1),
(2, 1, 2),
(3, 2, 3),
(4, 2, 4);

INSERT INTO reservation_room_request VALUES 
(1, 1, 'sleeping', 'nonsmoking', 2, 0, 1, 0, 1),
(2, 2, 'meeting', 'no_preference', 0, 80, 0, 1, 1),
(3, 3, 'suite', 'nonsmoking', 4, 10, 1, 1, 1),
(4, 4, 'hybrid', 'no_preference', 2, 30, 1, 0, 1);

INSERT INTO deposit VALUES 
(1, 1, 1, 250, '2026-03-25', '2026-03-25', 'paid'),
(2, 2, 2, 1000, '2026-04-01', NULL, 'pending'),
(3, 3, 3, 800, '2026-04-05', '2026-04-05', 'paid'),
(4, 4, 4, 600, '2026-04-10', NULL, 'pending');

INSERT INTO stay VALUES 
(1, 1, 1, 1, '2026-04-05 15:00:00', NULL, 'checked_in'),
(2, 1, 1, 2, '2026-04-05 15:10:00', '2026-04-08 11:00:00', 'checked_out'),
(3, 1, 2, 3, '2026-04-10 15:00:00', NULL, 'checked_in'),
(4, 1, 3, 4, '2026-04-12 15:00:00', NULL, 'checked_in'),
(5, 1, 3, 6, '2026-04-12 15:20:00', '2026-04-14 10:30:00', 'checked_out');

INSERT INTO stay_room VALUES 
(1, 1, 1, '2026-04-05 15:00:00', NULL),
(2, 2, 2, '2026-04-05 15:10:00', '2026-04-08 11:00:00'),
(3, 3, 3, '2026-04-10 15:00:00', NULL),
(4, 4, 2, '2026-04-12 15:00:00', NULL),
(5, 5, 6, '2026-04-12 15:20:00', '2026-04-14 10:30:00');

INSERT INTO event VALUES 
(1, 1, 2, 'AI & Future Systems Summit', '2026-04-11 09:00:00', '2026-04-11 18:00:00', 100, 40),
(2, 1, 3, 'Investor Strategy Retreat', '2026-04-12 10:00:00', '2026-04-12 16:00:00', 60, 25),
(3, 1, 4, 'Creative Leadership Workshop', '2026-04-19 09:30:00', '2026-04-19 15:30:00', 45, 18);

INSERT INTO facility_booking VALUES 
(1, 1, 4, '2026-04-11 09:00:00', '2026-04-11 18:00:00', 'scheduled', 100),
(2, 2, 5, '2026-04-12 10:00:00', '2026-04-12 16:00:00', 'scheduled', 60);

INSERT INTO service_item VALUES 
(1, 'In-Room Dining', 'food', 60),
(2, 'Ocean Spa Package', 'wellness', 150),
(3, 'Business Center Printing', 'business', 20);

INSERT INTO charge VALUES 
(1, 1, 1, NULL, NULL, 'room', '2026-04-05', 'Ocean-view room stay', 180),
(2, 2, NULL, 1, NULL, 'facility', '2026-04-11', 'Conference hall booking', 2000),
(3, 3, NULL, 2, NULL, 'facility', '2026-04-12', 'Executive meeting space', 1500),
(4, 1, NULL, NULL, 1, 'service', '2026-04-06', 'Late-night dining', 60),
(5, 2, NULL, NULL, 2, 'service', '2026-04-11', 'Spa package for guests', 300);

INSERT INTO payment VALUES 
(1, 1, '2026-04-06', 100, 'credit_card', 'TXN-A100'),
(2, 2, '2026-04-11', 1200, 'bank_transfer', 'TXN-B200'),
(3, 3, '2026-04-12', 800, 'credit_card', 'TXN-C300');
