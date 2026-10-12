# Initial MVP Backlog

This is the initial planning document.
After transfer, GitHub Issues will be the only active backlog.

## 1. Bootstrap the Django project
Goal: Create a runnable project with a passing test.
Description: Set up dependencies, project settings and a custom
email-based user model before the first migration. Add a basic
home page, a smoke test and local setup instructions.

## 2. Implement patient authentication
Goal: Patients can register, log in and log out.
Description: Add registration using first name, last name,
email and password. Validate inputs, reject duplicate emails
and ensure public registration cannot create administrators.

## 3. Manage and display doctors
Goal: Administrators manage doctors and patients browse them.
Description: Add doctor profiles with name, specialty and
description. Provide protected administration controls,
a public doctor list and doctor detail pages.

## 4. Create and display appointment slots
Goal: Administrators create valid 30-minute slots.
Description: Add timezone-aware slots and display available
future slots for each doctor in Asia/Almaty time.
Reject overlapping slots for the same doctor.

## 5. Implement appointment booking
Goal: Authenticated patients can book available future slots.
Description: Create bookings with server-side validation.
Prevent duplicate active bookings, including simultaneous
requests, and show a booking confirmation.

## 6. Implement patient appointment management
Goal: Patients can view and cancel their own appointments.
Description: Display appointment history and statuses.
Allow cancellation of future booked appointments and release
their slots. Block access to other patients' appointments.

## 7. Implement administrator appointment management
Goal: Administrators can review and update appointments.
Description: Show all appointments in the administration area.
Support cancellation and completion with explicit status
transition rules. Prevent patients from accessing these actions.

## 8. Verify the complete MVP and document the demo
Goal: The application meets the specification and is reproducible.
Description: Test complete patient and administrator workflows,
permissions, booking conflicts and persistence.
Check English text and mobile layouts. Document setup,
administrator creation, test commands and demo steps.
