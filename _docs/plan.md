# Medicine Center — MVP Specification

## 1. Purpose
Medicine Center is a web application for booking in-person
appointments at a single medical center.

Patients can book appointments online and attend them
physically at the center. Video consultations are excluded.

## 2. Users

### Patient
- Registers using first name, last name, email and password.
- Logs in and logs out.
- Browses doctors and their specialties.
- Selects a doctor, date and available appointment slot.
- Books an appointment.
- Views only their own appointments.
- Cancels their own future appointments.

### Administrator
- Logs in to a protected administration area.
- Adds and edits doctors.
- Provides each doctor's name, specialty and description.
- Creates appointment slots for doctors.
- Views all patient appointments.
- Cancels appointments.
- Marks appointments as completed.

## 3. Appointment Rules
- Each appointment lasts 30 minutes.
- All displayed dates and times use Asia/Almaty.
- Administrators create appointment slots.
- A slot can have only one active booking.
- Past slots cannot be booked.
- Cancelling a future appointment makes its slot available again.
- Booking requires an authenticated patient account.
- Appointment statuses are Booked, Cancelled and Completed.

## 4. Main Screens
- Registration
- Login
- Doctor list
- Doctor details and available slots
- Booking confirmation
- My Appointments
- Administration area for doctors, slots and appointments

## 5. Access and Data
- Patients can access only their own appointment records.
- Only administrators can manage doctors and slots.
- Public registration creates patient accounts only.
- Passwords must be stored using secure password hashing.
- Accounts, doctors, slots and appointments must persist
  after restarting the application.

## 6. Interface
- All interface text is in English.
- Forms show clear validation errors.
- Booking and cancellation show confirmation messages.
- Empty lists show an explanatory message.
- The interface works on desktop and mobile screens.

## 7. Out of Scope
- Video consultations
- Online payments
- SMS and email notifications
- Medical records
- Laboratory results

## 8. MVP Acceptance Scenarios
1. A patient registers, logs in and logs out.
2. An administrator adds a doctor and a future slot.
3. A patient books that slot and sees the appointment.
4. Another patient cannot book the occupied slot.
5. A patient cannot view or cancel another patient's booking.
6. Cancelling a future booking makes the slot available again.
7. Past slots cannot be booked.
8. An administrator can view, cancel and complete appointments.
9. Patients cannot access administration functions.
10. Saved data remains available after an application restart.

## 9. Details to Refine Before Implementation
The following details will be resolved during task refinement:
- Password validation and duplicate email handling.
- Preventing overlapping slots for the same doctor.
- Allowed appointment status transitions.
- Rules for marking an appointment as completed.
- Provisioning the initial administrator account.
- Handling simultaneous booking requests.

## 10. Development Approach
- Preserve the real brainstorming conversation.
- Choose the technology stack after reviewing this specification.
- Create a backlog and transfer tasks to GitHub Issues.
- Define agent instructions and PM, Engineer and QA roles.
- Refine each issue before implementation.
- Implement and test against its acceptance criteria.
- Close an issue only after QA reports PASS.
