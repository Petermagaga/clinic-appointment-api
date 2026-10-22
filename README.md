# Clinic Appointment Booking API

## 1. Overview

A REST API that allows patients to view doctor availability, book appointments, cancel bookings, and reschedule appointments. Each appointment lasts 30 minutes.

The initial system supports five doctors but is designed to accommodate additional doctors and patients.

## 2. Technology Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- Django automated testing tools
- GitHub Actions for CI/CD

## 3. Data Model

### Doctor
- id
- name
- specialty
- is_active

### Patient
- id
- full_name
- email
- phone

### DoctorWorkingHours
- id
- doctor (foreign key)
- weekday
- start_time
- end_time

Each record defines a doctor's working hours for a day of the week.

### Appointment
- id
- doctor (foreign key)
- patient (foreign key)
- starts_at
- ends_at
- status: booked or cancelled
- cancellation_reason (optional)
- created_at
- updated_at

## 4. Main Relationships

- One doctor can have multiple working-hour records.
- One doctor can have many appointments.
- One patient can have many appointments.
- Each appointment belongs to one doctor and one patient.

## 5. Booking Rules

1. Appointments last exactly 30 minutes.
2. The requested slot must fall within the doctor's working hours.
3. The appointment must not be in the past.
4. A doctor cannot have overlapping active appointments.
5. Cancelled appointments do not block the slot.
6. A cancelled appointment cannot be cancelled or rescheduled again.
7. Rescheduling validates the new slot using the same rules as a new booking.
8. Invalid requests return meaningful error responses.
9. The database enforces uniqueness for active bookings at the same doctor and start time. Application-level validation handles the remaining business rules.

## 6. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/appointments/ | Create a booking |
| GET | /api/doctors/{id}/availability/?date=YYYY-MM-DD | Retrieve available slots |
| PATCH | /api/appointments/{id}/cancel/ | Cancel a booking |
| PATCH | /api/appointments/{id}/reschedule/ | Reschedule a booking |
| GET | /api/patients/{id}/appointments/ | List upcoming appointments |

The patient appointments endpoint is a bonus feature.

## 7. Architecture

Client or API testing tool
        |
        v
Django REST Framework views
        |
        v
Serializers and booking validation
        |
        v
Booking domain logic
        |
        v
PostgreSQL database

The API layer handles HTTP requests and responses.
Serializers validate request data.
Booking logic enforces appointment rules.
The database persists records and protects against duplicate active bookings.

## 8. Key Design Decisions and Trade-offs

### Django REST Framework
It matches the project's requirements and supports structured APIs, serialization, validation, and automated testing.

### Relational database
PostgreSQL fits the relationships between doctors, patients, working hours, and appointments.

### Cancellation instead of deletion
Cancelled appointments remain in the database so the system preserves booking history and the cancellation reason.

### Database-level conflict protection
Application validation alone can fail when concurrent requests attempt the same slot. A database constraint provides an additional safeguard against duplicate active bookings.

### Fixed appointment duration
A fixed 30-minute duration simplifies slot generation and conflict checking for this assessment.

## 9. Assumptions and Scope

- Working hours repeat weekly.
- Each doctor has one working-hours interval per weekday in the initial version.
- Appointments must start on valid 30-minute slot boundaries.
- Timezone handling will be explicit and consistent.
- The initial version does not include payments, patient authentication, or a frontend.
- More advanced features can be added after the required functionality is complete.
