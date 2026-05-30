# MedTour: Global Medical Tourism Platform

MedTour is a comprehensive, enterprise-grade marketplace designed to bridge the gap between international patients and top-tier accredited hospitals worldwide. The platform facilitates the entire medical tourism lifecycle—from hospital discovery and inquiry to subscription-based lead generation and financial reconciliation.

---

## 🌟 Key Features

### 🏥 Hospital Management
- **Accreditation Tracking**: Support for JCI, NABH, ISO, and other international standards.
- **Dynamic Profiles**: Hospitals can manage doctors, upload facilities photos, and define detailed treatment packages.
- **Multistage Approval**: New registrations are reviewed by Admins/Coordinators. Includes an "Aged Approval" escalation system for delayed reviews.

### 💳 Subscription & Billing System
- **Tiered Plans**:
    - **Basic (Free)**: Limited visibility and package slots.
    - **Premium ($199/mo)**: Enhanced ranking, 25 treatment slots, dedicated coordinator.
    - **Elite Executive ($499/mo)**: Homepage priority, unlimited slots, 0% commission on initial leads.
- **Prorated Billing**: Smart logic for upgrades/downgrades that calculates unused credit and prevents double-charging.
- **Lead Wallet**: A centralized wallet system for hospitals to manage subscription payments and lead-generation fees.
- **Automated Renewals**: Background task logic to handle recurring billing and wallet debits.

### 📨 Patient Engagement
- **Smart Search**: Advanced filtering by treatment specialty, destination country, and budget.
- **Inquiry Workflow**: Secure submission of medical needs with a follow-up quote system.
- **Reviews & Ratings**: Verified patient stories to build trust and transparency.

### 🛡️ Security & Administration
- **Role-Based Access (RBAC)**: Distinct dashboards for Admins, Coordinators, Hospitals, and Patients.
- **Secure Authentication**: OTP-based email verification and "hold-to-see" password security UI.
- **Admin Dashboard**: High-level overview of platform revenue, hospital growth, and urgent pending actions.

---

## 🛠️ Technology Stack
- **Backend**: Django (Python)
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Frontend**: Tailwind CSS, Alpine.js (for reactive UI components like modals and calculators)
- **Email**: Integrated SMTP support with HTML templates for all lifecycle events.

---

## 📁 Project Structure

```bash
├── accounts/           # Auth, Roles, Profile Management, Staff Invitations
├── hospitals/          # Hospital Core, Subscriptions, Doctors, Wallet logic
├── treatments/         # Treatment catalog and Homepage Search
├── inquiries/          # Quote requests, Contact forms, Messaging
├── reviews/            # Patient feedback and rating system
├── medtour/            # Project configuration (settings, root URLs)
├── templates/          # Global UI components and shared layouts
└── static/             # CSS (Tailwind), JS, and Image assets
```

---

## ⚙️ Deployment & Task Scheduling

### Background Task Workaround (Free Tier Hosting)
Since some free hosting providers (like PythonAnywhere) do not allow standard Cron jobs, MedTour includes a **Web Trigger** workaround for processing subscriptions:

1.  **Endpoint**: `/hospitals/run-tasks/subscriptions/?token=YOUR_SECRET_TOKEN`
2.  **Usage**: Set up an external monitoring service (like [Cron-job.org](https://cron-job.org/)) to "ping" this URL once every 24 hours.
3.  **Action**: This trigger calls the internal `process_subscriptions` management command to handle daily billing.

### Installation
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Start the server: `python manage.py runserver`

---

## 📈 Database Schema Highlights
- **User**: Custom model extending AbstractUser with roles (PATIENT, HOSPITAL, ADMIN, COORDINATOR).
- **Hospital**: Linked to User, tracks status, accreditation, and subscription state.
- **WalletTransaction**: Ledger tracking all credits/debits with high precision.
- **TreatmentPackage**: The primary "product" offered by hospitals, defining services and pricing.

---

*Last Updated: May 2026*
