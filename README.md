# Clinic Appointment Booking API

A REST API built with Django REST Framework for managing clinic appointments. The system allows patients to book appointments with doctors, view availability, cancel existing bookings, reschedule appointments, and retrieve upcoming appointments.

Appointments use fixed 30-minute slots. The API validates doctor working hours, booking notice requirements, and existing appointments before accepting a booking.

**Project status:** Deployed; automated CI/CD configured.

**Live API:** [Live API](https://clinic-appointment-api-isyt.onrender.com)

**Source code:** [GitHub repository](https://github.com/Petermagaga/clinic-appointment-api)

---

## 1. Overview

The Clinic Appointment Booking API provides the backend functionality required for a basic clinic appointment scheduling system.

The main objectives are to:

- Allow patients to book appointments with doctors.

- Expose available appointment slots for a specified doctor and date.

- Prevent bookings outside working hours and conflicts with existing appointments.

- Support cancellation with a recorded reason.

- Allow patients to reschedule eligible appointments.

- Retrieve a patient's upcoming appointments in chronological order.

- Maintain appointment records rather than deleting cancelled bookings.

The application is designed around a clear separation between HTTP handling, request validation, appointment business logic, and database persistence.

## 2. Technology Stack

| Technology | Purpose |
| --- | --- |
| Python | Application programming language |
| Django | Backend framework |
| Django REST Framework | REST API views, serializers, and HTTP responses |
| PostgreSQL | Production relational database |
| SQLite | Local development database when no ``DATABASE_URL`` is configured |
| Django testing tools | Automated tests for appointment functionality |
| GitHub Actions | Automated checks, tests, and deployment workflow |
| Render | API hosting and production deployment |

## 3. System Design

### 3.1 Architecture

The application follows a layered design:

```text

Client / API Testing Tool

          |

          v

Django REST Framework Views

          |

          v

Serializers and Input Validation

          |

          v

Appointment Service Layer

          |

          v

Django ORM and Database Constraints

          |

          v

PostgreSQL (Production)

```

**Responsibilities of each layer**

- **Views:** Receive HTTP requests, call the relevant application logic, and return HTTP responses.

- **Serializers:** Validate incoming request data and format response data.

- **Appointment service layer:** Apply business rules for booking, cancellation, and rescheduling.

- **Django ORM and database:** Persist records, maintain relationships, and enforce database-level integrity constraints.

Keeping booking rules in the service layer allows booking and rescheduling to reuse the same validation logic instead of implementing separate, potentially inconsistent rules in each endpoint.

### 3.2 Data Model

#### Doctor

Represents a doctor who can receive appointments.

- `id`

- `name`

- `speciality`

- `is_active`

An inactive doctor cannot accept new appointments.

#### Patient

Represents a patient who books appointments.

- `id`

- `full_name`

- `email`

- `phone` (optional)

#### DoctorWorkingHours

Defines a doctor's regular working hours for a weekday.

- `id`

- `doctor` — foreign key to Doctor

- `weekday`

- `starts_time`

- `ends_time`

Working hours repeat weekly. The initial implementation supports one working-hours interval per doctor per weekday.

#### Appointment

Represents a booking between one patient and one doctor.

- `id`

- `doctor` — foreign key to Doctor

- `patient` — foreign key to Patient

- `starts_at`

- `ends_at`

- `status` — booked or cancelled

- `cancellation_reason` (optional)

- `created_at`

- `updated_at`

Appointment records are retained after cancellation to preserve the booking history and cancellation reason.

### 3.3 Entity Relationships

- One doctor can have multiple working-hours records.

- One doctor can have many appointments.

- One patient can have many appointments.

- Each appointment belongs to one doctor and one patient.

- Each working-hours record belongs to one doctor.

The relational model keeps doctor, patient, schedule, and appointment data separate while connecting them through foreign keys.

## 4. Appointment Booking Rules

The following rules govern appointment creation and rescheduling:

1\. Each appointment must last exactly 30 minutes.

2\. The start time must align with a valid 30-minute slot boundary.

3\. The appointment must not be in the past.

4\. The booking must satisfy the minimum one-hour notice requirement.

5\. The doctor must exist and be active.

6\. The requested slot must fall within the doctor's working hours for that weekday.

7\. A doctor cannot have overlapping booked appointments.

8\. Cancelled appointments do not block a slot.

9\. A cancelled appointment cannot be cancelled again or rescheduled.

10\. Rescheduling validates the new slot using the same rules as a new booking.

11\. Availability excludes slots that are already booked and slots that do not satisfy the booking notice requirement.

12\. Invalid requests return appropriate API errors.

### Conflict prevention

Application-level validation checks whether a requested slot overlaps an existing booked appointment.

Database-level constraints provide an additional safeguard against duplicate active bookings at the same doctor and start time.

The booking service also uses a database transaction and locks the doctor record during booking operations to help coordinate concurrent requests.

The database constraint and application validation serve different purposes: validation produces useful errors, while database constraints protect data integrity.

## 5. API Endpoints

All endpoints use the `/api/` prefix.

| Method | Endpoint                                          | Purpose                                      |

| ------ | ------------------------------------------------- | -------------------------------------------- |

| POST   | `/api/appointments/`                              | Create an appointment                        |

| GET    | `/api/doctors/{id}/availability/?date=YYYY-MM-DD` | Retrieve available 30-minute slots           |

| PATCH  | `/api/appointments/{id}/cancel/`                  | Cancel an appointment                        |

| PATCH  | `/api/appointments/{id}/reschedule/`              | Reschedule an appointment                    |

| GET    | `/api/patients/{id}/appointments/`                | Retrieve upcoming appointments for a patient |

The patient appointments endpoint is an additional feature beyond the core booking, availability, cancellation, and rescheduling operations.

### 5.1 Create an Appointment

**Request**

`POST /api/appointments/`

```json

{

  "doctor": 1,

  "patient": 1,

  "starts_at": "2026-10-29T10:00:00+03:00",

  "ends_at": "2026-10-29T10:30:00+03:00"

}

```

**Expected result:**** A successful creation response containing the new appointment's details, including its identifier, doctor, patient, start and end times, and status.

The example uses East Africa Time (`+03:00`). The requested slot must be valid at the time the API receives it; update the date and time when testing.

### 5.2 Retrieve Doctor Availability

**Request**

`GET /api/doctors/1/availability/?date=2026-10-29`

The endpoint returns available 30-minute slots for the requested doctor and date, subject to the doctor's working hours, existing bookings, and minimum booking notice.

**Example of a slot representation**

```json

{

  "start": "2026-10-29T10:00:00+03:00",

  "end": "2026-10-29T10:30:00+03:00"

}

```

This illustrates the slot's time representation; use the actual response structure returned by the deployed API when documenting the complete response.

### 5.3 Cancel an Appointment

**Request**

`PATCH /api/appointments/2/cancel/`

```json

{

  "cancellation_reason": "Patient requested cancellation"

}

```

A successful cancellation changes the appointment status to `cancelled` and records the reason. The appointment remains in the database, and its slot becomes available for another booking if it otherwise satisfies the booking rules.

Attempting to cancel the same appointment again is rejected.

### 5.4 Reschedule an Appointment

**Request**

`PATCH /api/appointments/3/reschedule/`

```json

{

  "starts_at": "2026-10-29T11:00:00+03:00",

  "ends_at": "2026-10-29T11:30:00+03:00"

}

```

The new slot is validated using the same booking rules as a new appointment.

A successful reschedule updates the existing appointment rather than creating a separate appointment. The old slot becomes available again, provided it meets the availability rules.

Rescheduling a cancelled appointment is rejected.

### 5.5 Retrieve Upcoming Patient Appointments

**Request**

`GET /api/patients/1/appointments/`

The endpoint returns upcoming booked appointments for the specified patient, ordered by start time in ascending order. Cancelled appointments and past appointments are excluded.

An unknown patient identifier returns a not-found response.

## 6. Validation and Error Handling

The API rejects invalid booking operations instead of accepting appointments that violate scheduling rules.

| Situation                                   | Expected behavior                                      |

| ------------------------------------------- | ------------------------------------------------------ |

| Invalid or missing request fields           | Return a validation error                              |

| Unknown doctor or patient                   | Return an appropriate not-found or validation response |

| Inactive doctor                             | Reject the booking                                     |

| Appointment in the past                     | Reject the booking                                     |

| Insufficient booking notice                 | Reject the booking                                     |

| Outside working hours                       | Reject the booking                                     |

| Slot already occupied                       | Reject the conflicting booking                         |

| Invalid appointment duration                | Reject the booking                                     |

| Cancelling an already-cancelled appointment | Reject the operation                                   |

| Rescheduling a cancelled appointment        | Reject the operation                                   |

| Unknown appointment identifier              | Return a not-found response                            |

The exact HTTP status and response body should be confirmed against the implemented views and live API. The API uses Django REST Framework's validation and exception-handling mechanisms.

## 7. Timezone Handling

The application uses Django's timezone-aware datetime support and configures the project timezone as `Africa/Nairobi`.

Appointment requests should include explicit UTC offsets, such as `+03:00`, to avoid ambiguity when submitting local appointment times.

The API validates dates and times using the configured timezone-aware application logic. Availability is requested for a specific calendar date using the `YYYY-MM-DD` format.

## 8. Key Design Decisions and Trade-offs

### Django REST Framework

Django REST Framework provides serializers, API views, structured request validation, and testing support suited to this API.

### Relational data model

Doctors, patients, working hours, and appointments are separate entities linked through foreign keys. This reduces unnecessary duplication and makes relationships explicit.

### Service-layer business logic

Booking, cancellation, and rescheduling rules are kept in dedicated application logic. Rescheduling reuses booking validation to reduce duplication and inconsistent behavior.

### Cancellation instead of deletion

Cancelled appointments remain stored with their cancellation reason. This preserves useful history and makes it possible to distinguish cancelled appointments from appointments that never existed.

### Transactional booking

Booking operations use database transactions and doctor-row locking, together with validation and database constraints, to improve protection against concurrent booking attempts.

### Fixed appointment duration

The assessment uses fixed 30-minute appointments. This simplifies slot generation and overlap checking but would need to be extended for clinics with appointments of different lengths.

## 9. Testing Strategy

The project includes automated tests for appointment business logic and API behavior.

The test suite covers the core booking lifecycle, including booking validation, cancellation, rescheduling, availability, and the upcoming patient appointments endpoint.

Run the tests locally from the Django project directory:

```bash

python manage.py check

python manage.py test appointments

```

The Django check identifies configuration and application issues. The appointment test suite verifies expected behavior without requiring manual testing for every code change.

The GitHub Actions workflow runs the Django check and appointment tests. Pull requests targeting `main` are tested, and pushes to `main` run the tests before the deployment job is allowed to execute.

## 10. Local Development Setup

### Prerequisites

- Python 3.13

- Git

- The project source code

### Installation

Clone the repository:

```bash

git clone https://github.com/Petermagaga/clinic-appointment-api.git

cd clinic-appointment-api/clinic-appointment-api

```

Create and activate a virtual environment.

**Windows PowerShell**

```powershell

python -m venv .venv

.\\.venv\Scripts\Activate.ps1

```

Install the dependencies:

```bash

python -m pip install -r requirements.txt

```

Configure the environment variables required by the project's settings. At minimum, use a development secret key and configure the debug setting for local development. If using PostgreSQL locally, configure `DATABASE_URL` with the appropriate database connection string. Do not commit secrets or database credentials to Git.

The project supports SQLite for local development when `DATABASE_URL` is not configured.

Apply migrations:

```bash

python manage.py migrate

```

Run the checks and tests:

```bash

python manage.py check

python manage.py test appointments

```

Start the development server:

```bash

python manage.py runserver

```

The API is then available locally at `http://127.0.0.1:8000/`.

## 11. Deployment and CI/CD

### Production deployment

- **Hosting:** Render

- **Production database:** PostgreSQL

- **Application server:** Gunicorn

- **Static-file handling:** WhiteNoise and Django's static-file collection

- **Source control:** GitHub

Live API: [Live API](https://clinic-appointment-api-isyt.onrender.com)

### CI/CD workflow**

The workflow is defined in `.github/workflows/ci-cd.yml`.

1\. A pull request targeting `main` triggers the automated Django check and appointment tests.

2\. A push to `main` runs the checks and tests again.

3\. The deployment job depends on successful completion of the test job.

4\. On a successful push to `main`, GitHub Actions invokes the Render deployment hook.

5\. Render builds and deploys the application.

The deployment hook is stored in GitHub Actions repository secrets as `RENDER_DEPLOY_HOOK_URL`, rather than being committed to source control.

This setup prevents the workflow's deployment step from running when the test job fails. Branch protection or repository rules can additionally be configured to require successful checks before merging pull requests.

### Post-deployment verification

A successful GitHub Actions workflow and Render deployment confirm that the configured checks and deployment process completed. They do not, by themselves, prove that every live API workflow works correctly. Before assessment, manually verify the deployed API and admin login, and perform a safe live smoke test using valid test data. Avoid creating or changing real appointments unintentionally. Automated post-deployment smoke tests are listed as a future improvement.

## 12. Assumptions and Limitations

- Working hours repeat weekly.

- Each doctor has one working-hours interval per weekday.

- Appointments have a fixed duration of 30 minutes.

- Appointments must start on valid 30-minute boundaries.

- A minimum of one hour's notice is required for booking.

- The initial version does not implement patient authentication, payments, notifications, or a frontend.

- The API does not attempt to provide a complete clinic management system.

- The current design can be extended to support multiple working intervals, different appointment durations, authentication, and additional clinic workflows.

## Admin Demo Access

The Django administration interface is available on the deployed application. The reviewer has been sent the assessment login credentials privately by email. For security, the password is not published in this README or committed to source control.

**Admin Login URL:** [Open the Django Admin Dashboard](https://clinic-appointment-api-isyt.onrender.com/admin/)

### Assessment Credentials

- **Username:** `AbminDoctor` *(confirm this spelling matches the active production account before submission; if not, replace it with the verified username sent to the reviewer).*
- **Password:** Provided privately to the reviewer by email.

### Access Instructions

1. Open the [Django Admin Dashboard](https://clinic-appointment-api-isyt.onrender.com/admin/).
2. Enter the username and password sent privately to the reviewer.
3. Click **[Log in to the Django Admin Dashboard](https://clinic-appointment-api-isyt.onrender.com/admin/)**.
4. Explore the available application models and administrative functionality.

**Security note:** The assessment account must exist in the production database and have the appropriate permissions. Verify the username and test the credentials before submission. Never commit passwords, database URLs, or deployment secrets to the repository.

# AI Use and Engineering Reflection

This section documents how AI assistance supported the development, testing, and deployment of the Clinic Appointment API. AI was used as a technical reasoning and troubleshooting aid, while implementation decisions were evaluated against the application's code, automated tests, and deployment behavior.

## One useful AI prompt

**Prompt used:**

"Review the appointment-booking service for correctness. Identify how the implementation validates appointment requests, prevents duplicate bookings for the same doctor and time slot, and handles concurrent requests. Recommend a solution consistent with Django's transaction management and the application's existing models. Explain how the proposed behavior should be tested."

**How it helped:**

The discussion helped me reason about appointment booking as a data-integrity problem rather than simply an API request that creates a database record. Two requests attempting to reserve the same time slot must not both result in conflicting appointments.

It also reinforced the distinction between application-level validation and database transaction safety. Django transaction management, including `transaction.atomic()` and appropriate locking strategies, provides a foundation for handling competing booking requests. However, the appropriate locking and constraint strategy depends on the database backend and the application's data model.

**Verification:**

I used the Django test suite to validate the appointment-booking implementation. The project had five passing tests during an earlier debugging stage, and the suite subsequently reached 20 passing tests. I also used the automated test suite in GitHub Actions, where the Django checks and appointment tests completed successfully.

These results provided evidence that the tested behavior worked in the test environment. They do not, by themselves, establish that every concurrency scenario is safe in production PostgreSQL; that requires additional database-specific tests.

## One incomplete or incorrect AI suggestion

**Suggestion:****

During deployment troubleshooting, the proposed approach to creating an administrative user initially needed a more explicit distinction between the local development database and the production PostgreSQL database. Running Django's `createsuperuser` command successfully does not establish that the account was created in the production database.

**How I identified the issue:****

The application used SQLite locally and PostgreSQL in production. I recognized that the same Django management command could operate on different databases depending on the environment configuration.

Consequently, a successful command in the local terminal was insufficient evidence that the production administrator account existed. The production admin login behavior also required further investigation rather than assuming that the account had been configured correctly.

**What I changed:**

I adopted a verification-first approach: inspect Django's active database configuration without displaying credentials, confirm the database host and name, inspect the administrator account's status, and only then create or reset the account against the intended database.

This approach makes the target environment explicit and reduces the risk of changing the wrong database. The relevant verification commands and production login still need to be evaluated against the actual deployment before claiming the issue is fully resolved.

## Two decisions I made without relying on AI

### Decision 1 — Preserve a separate local development environment and production database

I chose to maintain a local development database for development and automated tests while using PostgreSQL for the deployed application.

An alternative would have been to use the production database for local testing. I rejected that approach because development and test operations should not unnecessarily affect live patient and appointment records.

Separating the environments also makes automated testing more repeatable and reduces the risk of accidental changes to production data. The CI workflow uses its own test environment rather than requiring production database credentials.

### Decision 2 — Require automated checks before triggering deployment

I implemented a GitHub Actions workflow that installs the project's dependencies, runs Django's system check, executes the appointment tests, and triggers a Render deployment only after the test job succeeds on a push to `main`.

An alternative would have been to rely entirely on Render's automatic deployment after every code push. I chose the CI/CD workflow because it introduces an explicit testing stage before the deployment request is made.

I verified the pipeline through GitHub Actions. The test job and deployment job both completed successfully, and I confirmed that the Render service was live.

This verifies that the pipeline executed successfully. It does not replace post-deployment API tests or prove that every production behavior is correct. I would add live health checks and integration tests to strengthen the release process further.

---

The main lesson from this development process is that AI-generated advice should be treated as a proposal, not as proof of correctness. I used tests, configuration inspection, and deployment results to evaluate suggestions and distinguish successful execution from verified application behavior.

## 14. Future Improvements

The current implementation provides a foundation for appointment management, automated testing, and deployment. The following improvements would strengthen security, scheduling flexibility, data integrity, and production observability.

1\. **Patient authentication and authorization:** Introduce patient accounts and enforce role-based permissions so patients can access their own appointments while authorized staff can manage scheduling operations.

2\. **Multiple working intervals per day:** Support split shifts, lunch breaks, and other scheduling arrangements instead of assuming a single continuous working interval.

3\. **Configurable appointment durations:** Allow appointment lengths to be configured according to the doctor's specialty, appointment type, or clinic scheduling policy.

4\. **Appointment reminders and notifications:***Add email or SMS reminders, delivery-status tracking, retry handling, and configurable notification schedules.

5\. **Detailed audit history:**** Record significant events such as bookings, cancellations, rescheduling, and administrative changes, including timestamps and the responsible actor.

6\. **Stronger concurrent-booking tests:** Add integration tests against PostgreSQL to verify that simultaneous booking requests cannot create conflicting appointments. Evaluate appropriate transaction locking, database constraints, and conflict-handling behavior.

7\. **Production monitoring and health checks:** Introduce structured logging, application health endpoints, error monitoring, and alerts for failed requests or deployment problems.

8\. **Post-deployment verification:** Extend CI/CD with deployment-status checks and automated smoke tests against the live API. A deployment should be considered operationally verified only after the application responds as expected.

9\. **Deployment security and recovery:** Review environment-variable management, secret rotation, database backups, migration procedures, and rollback strategies to improve operational resilience.

These improvements would help evolve the API from a working appointment-booking application into a more secure, maintainable, and production-ready service.
