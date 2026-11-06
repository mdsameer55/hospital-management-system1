# CarePoint Hospital Management System

Flask + MySQL 8.0 college DBMS project.

## Windows setup
1. Install Python 3.10+ and MySQL Server 8.0. Start the MySQL80 service.
2. In MySQL Workbench, open and execute `database/schema.sql`.
3. Open PowerShell in this folder:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
4. Edit `.env` and set the actual MySQL password. Keep DB_NAME as `hospital_management`.
5. Insert sample departments, 5 doctors, 15 patients, appointments, beds, medicines and admin:
```powershell
python -m database.seed
```
6. Start the app:
```powershell
python app.py
```
7. Open http://127.0.0.1:5000

**Demo admin:** `admin` / `Admin@123`

## Modules
Dashboard, patient registration/search, doctor management, appointment booking and status, admissions and discharge with bed availability, invoices and partial payments, prescriptions, medicine inventory and stock movements, monthly reports and admin audit log. All application records are persisted in MySQL.

## Verify in MySQL Workbench
```sql
USE hospital_management;
SELECT * FROM users;
SELECT * FROM patients;
SELECT * FROM doctors;
SELECT * FROM appointments;
SELECT * FROM admissions;
SELECT * FROM invoices;
SELECT * FROM payments;
SELECT * FROM audit_logs;
SELECT * FROM medicines;
```

## Database overview
Roles -> users. Patients link to appointments, admissions, prescriptions and invoices. Doctors link to appointments and prescriptions. Wards contain beds; admissions reserve beds. Invoices have payment transactions. Medicines have stock transaction history. User actions are stored in audit_logs.

## Important scope note
This is an academic demo, not production clinical software. The implemented UI covers the primary workflows. Some schema tables (medical_records, staff, invoice line items) are prepared for extension but do not yet have full management screens. Before real deployment, add CSRF protection, password change/reset, full doctor-user provisioning, backups, HTTPS, stronger audit immutability, privacy controls and security review. Do not enter real patient data.
