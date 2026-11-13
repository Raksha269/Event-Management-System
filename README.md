# Gather — Event Management System (EMS)

[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.15+-red.svg)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-104%20Passing-brightgreen.svg)]()
[![Security](https://img.shields.io/badge/Security-TLS%201.2%2B%20%7C%20PCI--DSS%20%7C%20RBAC-success.svg)]()

**Gather** is a full-featured, secure, and robust Event Management System designed to handle event publishing, multi-tier ticketing, high-concurrency attendee registration, mock payment processing with QR e-tickets, comprehensive financial reporting, administrator user governance, and real-time security monitoring.

---

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
3. [Implemented Feature Modules](#implemented-feature-modules)
   - [Authentication & Account Governance](#1-authentication--account-governance)
   - [Event Management Workflows (Issue #4)](#2-event-management-workflows-issue-4)
   - [Ticketing, Payments & Refunds](#3-ticketing-payments--refunds)
   - [Reporting & Analytics (Issue #8)](#4-reporting--analytics-issue-8)
   - [Security & Incident Response (Issue #10)](#5-security--incident-response-issue-10)
4. [Non-Functional Requirements & Operations](#non-functional-requirements--operations)
5. [Software Test Plan & Verification Matrix](#software-test-plan--verification-matrix)
6. [REST API Documentation](#rest-api-documentation)
7. [Getting Started & Local Development](#getting-started--local-development)

---

## Architectural Overview

Gather is built on Django 5.2 and Django REST Framework, adopting a layered architecture:

- **Presentation Layer**: Mobile-responsive Django templates (`base.html`, `organizer_dashboard.html`, `admin_user_list.html`, `admin_alerts.html`, `event_report.html`) paired with RESTful JSON endpoints.
- **Service & Domain Layer**: Dedicated service routines (`events/services.py`, `events/reports.py`, `events/security.py`) handling transactional capacity locks, payment tokenization, cryptographic validation, and velocity anomaly detection.
- **Persistence Layer**: Relational data models (`Event`, `TicketType`, `Registration`, `Payment`, `Refund`, `Ticket`, `UserProfile`, `SecurityAlert`) enforced by database constraints, transaction isolation, and row-level locking.

---

## Role-Based Access Control (RBAC)

The system defines three core roles in `accounts/roles.py`:

| Role | Permissions & Access Scope |
| :--- | :--- |
| **Attendee** | Browse published events, register for tickets, receive QR e-tickets, request refunds, manage personal profile. |
| **Organizer** | Create events (Draft), edit event details before start date, manage multi-tier ticket tiers, publish/unpublish owned events, access real-time attendee rosters and CSV export, view financial analytics. |
| **Administrator** | Access system administration portal, list and search user accounts, toggle user active/deactivated status, reassign user roles, monitor real-time security alerts and resolve incidents. |

*RBAC is strictly enforced on every route and API endpoint using `@role_required` decorators, DRF permission classes (`IsOrganizer`, `IsAdministrator`, `IsEventOwner`), returning `403 Forbidden` for unauthorized attempts.*

---

## Implemented Feature Modules

### 1. Authentication & Account Governance
- **Self-Service Registration (`EMS-F-001`)**: Account creation with email format and password strength validation.
- **Email Verification (`EMS-F-002`)**: Cryptographic URL tokens dispatched on registration; activates account upon verification.
- **Session Management (`EMS-F-003`, `EMS-F-004`)**: Secure login and logout with brute-force lockout safeguards.
- **User Administration (`EMS-F-051`, Issue #8)**:
  - Admin Web UI (`/admin-portal/users/`) and REST API (`/api/v1/admin/users/`).
  - Search by username or email, filter by role.
  - One-click account activation / deactivation (immediate session rejection for deactivated users).
  - Role promotion and reassignment (`attendee`, `organizer`, `administrator`).
  - Self-governance safety checks: Administrators cannot deactivate their own account or change their own role.

### 2. Event Management Workflows (Issue #4)
- **Draft Creation (`EMS-F-010`)**: Organizers create events with title, category, date, venue, capacity, and default ticket price. Events default to `DRAFT` status and remain hidden from attendees.
- **Event Modification (`EMS-F-011`)**: Organizers edit event metadata prior to the start date. Editing is rejected after event commencement. Non-owning organizers are blocked with `403 Forbidden`.
- **Multi-Tier Ticketing (`EMS-F-014`)**: Support for customized tiers (e.g., General Admission, VIP Pass, Early Bird) each with distinct pricing and quantity caps.
- **Event Publication (`EMS-F-012`)**: Organizers publish events to `PUBLISHED` status once details and ticket tiers are ready.
- **Event Unpublishing (`EMS-F-013`)**: Allows organizers to retract events to `UNPUBLISHED` status, immediately hiding them from public browsing.
- **Public Discovery & Search (`EMS-F-015`)**: Full-text search by title, description, venue, and filtering by category. Unpublished/Draft events are strictly excluded.
- **Overselling Prevention (`EMS-F-014`)**: Concurrency-safe registration pipeline using database row-level locking (`select_for_update`) and thread synchronization to guarantee event capacity and ticket-tier limits are never exceeded.

### 3. Ticketing, Payments & Refunds
- **Payment Processing (`EMS-F-016`)**: Mock payment gateway returning opaque UUID tokens (`transaction_id`).
- **QR Code E-Tickets (`EMS-F-017`)**: High-resolution PNG QR codes generated via Pillow/qrcode containing unique verification payloads.
- **Refunds & Cancellations (`EMS-F-020`)**: Registrations can be cancelled and refunded, updating payment status to `REFUNDED` and returning capacity back to the event pool.

### 4. Reporting & Analytics (Issue #8)
- **Attendee Roster & Live Export (`EMS-F-030`)**:
  - Live attendee roster display for owning organizers and administrators.
  - Direct CSV download (`/events/<pk>/report/attendees.csv` and `/api/v1/events/<pk>/reports/attendees.csv`) containing complete attendee registration details, ticket tiers, amounts, and timestamps matching on-screen metrics.
- **Financial & Capacity Analytics (`EMS-F-031`)**:
  - Metrics calculation including Gross Revenue, Completed Refunds, Net Revenue, Confirmed Attendees, and Remaining Capacity.
  - Per-tier breakdown tracking tickets sold, revenue per tier, and capacity fill rate.

### 5. Security & Incident Response (Issue #10)
- **TLS 1.2+ Transport Security (`EMS-SR-001`, `TC-Sec-01`)**:
  - Protocol validator (`verify_tls_version`) strictly enforcing TLS 1.2 and TLS 1.3 while rejecting legacy protocols (`SSLv2`, `SSLv3`, `TLS 1.0`, `TLS 1.1`).
  - Production security headers: `SECURE_BROWSER_XSS_FILTER = True`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = 'DENY'`, `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`.
- **Payment Data Tokenization (`EMS-SR-002`, `TC-Sec-02`)**:
  - PCI-DSS compliant storage auditing (`inspect_payment_data_storage`) verifying zero raw credit card numbers (PAN), CVVs, expiration dates, or magnetic track data exist in the database schema.
  - `Payment` model references opaque UUID tokens.
- **Modern Salted Password Hashing (`EMS-SR-003`, `TC-Sec-03`)**:
  - Django `PASSWORD_HASHERS` configured with PBKDF2 (`pbkdf2_sha256`), Argon2, and BCrypt.
  - Password algorithm prefix verification confirming salted hash storage and rejecting plaintext passwords.
- **RBAC Endpoint Authorization (`EMS-SR-004`, `TC-Sec-04`)**:
  - Uniform `403 Forbidden` responses returned for unauthorized roles or non-owners across all Web views and REST API endpoints.
- **Suspicious Activity Monitoring & Incident Response (`EMS-SR-005`, `TC-Sec-05`)**:
  - **Login Failure Burst Detection**: Alerts triggered on 3+ consecutive failed login attempts.
  - **Account Lockout**: 5 consecutive failed login attempts trigger an immediate 15-minute account lockout and generate an alert of type `ACCOUNT_LOCKOUT` with `HIGH` severity. Locked accounts are rejected even if the correct password is provided. Successful logins reset the failure counter.
  - **Abnormal Registration Velocity Detection**: Alerts triggered when registration velocity spikes (> 5 registrations in under 60 seconds on an event).
  - **Security Alerts Monitoring Panel**: Administrator dashboard (`/admin-portal/alerts/`) and REST API (`/api/v1/admin/alerts/`) with KPI cards (Total, Unresolved, High/Critical, Lockouts), severity/type filters, and resolution actions (`/api/v1/admin/alerts/<id>/resolve/`).

---

## Non-Functional Requirements & Operations

The application now includes implementation support for the NFRs. Production targets still need measurements from the deployed environment; local SQLite runs cannot establish the 500-user concurrency or monthly availability targets.

| Requirement | Application support | Verification target / evidence |
| :--- | :--- | :--- |
| `EMS-NF-001` Performance | Composite indexes for event discovery and registration lookups; collection APIs support bounded pagination with `?limit=50&offset=0` (maximum 100). | Run the Software Test Plan search/load scenario; record p95 response time (target <= 2 seconds) and load profile. |
| `EMS-NF-002` Availability | `/health/ready/` checks database connectivity and returns 503 if unavailable; production HTTPS, secure cookies, HSTS, and configurable database connection reuse are enabled when `DJANGO_DEBUG=false`. | Monitor endpoint and record monthly uptime against the SRS target of 99.5%, excluding scheduled maintenance; retain alert, backup, failover, and restore evidence. |
| `EMS-NF-003` Scalability | Production PostgreSQL configuration is supported through environment variables; registration transactions use database row locks; registration queries are indexed. | Run 500 concurrent registration attempts and the SRS 10,000-attempt load test against PostgreSQL. SQLite is for local development and does not provide production row-lock semantics. |
| `EMS-NF-004` Usability | Responsive viewport metadata and flexible layouts are included in the web UI. | Capture checks at 360, 768, and 1440 px and record clipping/overflow and accessibility findings. |
| `EMS-NF-005` Audit retention | Append-only `AuditEvent` records cover authentication, event create/update/publication, registration, payment/refund, security alerts, and administrator user changes. Administrator audit access is read-only. | Records default to 1,095 days (three years). Schedule `python manage.py purge_audit_events`; verify retrieval before expiry and retain archive/deletion-policy evidence. |

Audit entries exclude passwords, raw payment details, and request bodies. A server-generated `X-Request-ID` is included in responses and stored with audit events created within a request. Retention defaults to the SRS minimum of three years. The purge command permanently deletes expired records, so schedule it only after any required external archival is configured.

### Production configuration

Set `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY`, and comma-separated `DJANGO_ALLOWED_HOSTS`. For PostgreSQL set `EMS_DB_ENGINE=postgresql`, `EMS_DB_NAME`, `EMS_DB_USER`, `EMS_DB_PASSWORD`, `EMS_DB_HOST`, and optionally `EMS_DB_PORT`, `EMS_DB_CONN_MAX_AGE`, and `EMS_DB_SSLMODE`. Keep the database on a private network and provision recurring backups and an external uptime monitor. Configure the TLS-terminating proxy for TLS 1.2+ and forward the HTTPS protocol header.

Operational validation is **not yet executed** in this repository workspace. Record actual load, availability, backup-restore, and viewport results before marking the NFR verification cases as passed.

Local evidence: readiness/request-ID behavior, optional pagination, administrator-only audit retrieval, audit immutability, and expiry-boundary deletion are covered by automated tests. Chromium checked the public discovery page at 360, 768, and 1440 px with no horizontal document overflow; full workflow and WCAG 2.1 AA checks remain. The existing final-ticket concurrency case passes on the local SQLite development backend. This does not establish the PostgreSQL 500-user/10,000-attempt target; those load cases remain partial. The three-year archive/retrieval boundary has not been simulated end-to-end.

---

## Software Test Plan & Verification Matrix

Automated tests map directly to the IEEE Software Test Plan:

| Test Case ID | Requirement | Description | Status |
| :--- | :--- | :--- | :---: |
| **TC-01** | `EMS-F-010` | Organizer creates event; verifies default Draft status and capacity validation | **PASS** |
| **TC-02** | `EMS-F-011` | Organizer edits event before start date; non-owners blocked with 403 Forbidden | **PASS** |
| **TC-03** | `EMS-F-012` | Owning organizer publishes event; unpublished events hidden from public search | **PASS** |
| **TC-04** | `EMS-F-013` | Organizer unpublishes event; returns to Unpublished status and hidden from search | **PASS** |
| **TC-05** | `EMS-F-014` | High-concurrency registration test (multi-threading) ensures zero overselling | **PASS** |
| **TC-06** | `EMS-F-014` | Multi-tier ticket capacity limit and "Sold Out" validation | **PASS** |
| **TC-07** | `EMS-F-015` | Public event discovery, text query, and category filters | **PASS** |
| **TC-08** | `EMS-F-030` | Attendee roster display and CSV export matching on-screen metrics | **PASS** |
| **TC-09** | `EMS-F-031` | Financial analytics reflect ticket sales and deduct refunds from net revenue | **PASS** |
| **TC-10** | `EMS-F-051` | Admin user account management: toggle active status and change user roles | **PASS** |
| **TC-Sec-01**| `EMS-SR-001` | TLS 1.2+ protocol compliance check and security transport headers | **PASS** |
| **TC-Sec-02**| `EMS-SR-002` | PCI-DSS database audit verifies zero raw PAN or CVV storage; UUID tokenization | **PASS** |
| **TC-Sec-03**| `EMS-SR-003` | Database inspection confirms modern salted password hashing; rejects plaintext | **PASS** |
| **TC-Sec-04**| `EMS-SR-004` | RBAC matrix enforcement across roles returns 403 Forbidden on unauthorized endpoints | **PASS** |
| **TC-Sec-05**| `EMS-SR-005` | 5 failed logins trigger 15m lockout, abnormal velocity alert, admin resolve API | **PASS** |
| **TC-NF-01** | `EMS-NF-001` | Search p95 at normal load (up to 500 concurrent users; <= 2 sec target) | **NOT EXECUTED** |
| **TC-NF-02** | `EMS-NF-002` | 99.5% monthly uptime (excluding scheduled maintenance), failure recovery and restore evidence | **NOT EXECUTED** |
| **TC-NF-03** | `EMS-NF-003` | 500 concurrent registrations and 10,000-attempt load on PostgreSQL | **PARTIAL** |
| **TC-NF-04** | `EMS-NF-004` | Usability at 360, 768, 1440 px | **PARTIAL** |
| **TC-NF-05** | `EMS-NF-005` | Audit completeness, retrieval, access and retention boundary | **PARTIAL** |

### Test Execution Summary
- **Main Test Suite (`events`)**: 80 passed in 78.4s (`python manage.py test`)
- **RBAC Module (`RBAC`)**: 24 passed in 20.3s (`cd RBAC && python manage.py test`)
- **Total Tests**: **104 passing automated tests (100% pass rate)**

---

## REST API Documentation

### Event Endpoints
- `GET /api/v1/events/`: Search and browse published events (supports `?q=` and `?category=`).
- Collection endpoints accept optional `?limit=` and `?offset=` parameters (maximum page size 100); omitting them preserves the existing array response shape.
- `POST /api/v1/events/`: Create a new event in Draft status *(Organizer only)*.
- `GET /api/v1/events/{id}/`: Retrieve event details.
- `PUT/PATCH /api/v1/events/{id}/`: Edit event metadata before start date *(Owning Organizer only)*.
- `POST /api/v1/events/{id}/publish/`: Publish event *(Owning Organizer only)*.
- `POST /api/v1/events/{id}/unpublish/`: Unpublish event *(Owning Organizer only)*.
- `GET/POST /api/v1/events/{id}/ticket-types/`: Manage ticket tiers *(Owning Organizer only)*.
- `POST /api/v1/events/{id}/registrations/`: Register attendee for event with ticket tier.
- `GET /api/v1/events/{id}/reports/attendees.csv`: Export attendee CSV report *(Owning Organizer or Admin)*.

### Administration & User Management Endpoints
- `GET /api/v1/admin/users/`: List all users with query and role filters *(Administrator only)*.
- `GET /api/v1/admin/users/{id}/`: Retrieve user details *(Administrator only)*.
- `PATCH /api/v1/admin/users/{id}/`: Update user `is_active` status or `role` *(Administrator only)*.

### Security Monitoring & Alerts Endpoints
- `GET /api/v1/admin/alerts/`: List security alerts with `?severity=`, `?type=`, and `?is_resolved=` filters *(Administrator only)*.
- `POST /api/v1/admin/alerts/{id}/resolve/`: Mark a security alert as resolved *(Administrator only)*.
- `GET /api/v1/admin/audit-events/?limit=50&offset=0`: Read retained audit events *(Administrator only; max 100 rows per page)*.

---

## Getting Started & Local Development

### Prerequisites
- Python 3.10+ (tested on Python 3.12 and 3.14)
- SQLite3

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/rahulb/Event-Management-System.git
cd Event-Management-System

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
python manage.py migrate
```

### 3. Run Automated Tests
```bash
# Run all core event, reporting, and security tests
python manage.py test

# Run isolated RBAC unit tests
cd RBAC && python manage.py test
```

### 4. Start Local Development Server
```bash
python manage.py runserver
```
Visit `http://localhost:8000/` in your browser to access the Gather portal.
