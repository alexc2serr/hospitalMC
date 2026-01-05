-- ==========================================================
-- GROUP ASSESSMENT: HOSPITAL INFORMATION SYSTEM
-- DATABASE: SQLite
-- AUTHORS: Alejandro Serrano, Alba Prats, Tomas Usón
-- ==========================================================

-- 1. CONFIGURATION
-- Enable Foreign Key enforcement (Required for SQLite)
PRAGMA foreign_keys = ON;

-- 2. DROP TABLES (Cleanup for fresh installation)
-- We drop in reverse order of dependencies
DROP TABLE IF EXISTS AuditLogs;
DROP TABLE IF EXISTS LabResults;
DROP TABLE IF EXISTS Prescriptions;
DROP TABLE IF EXISTS Treatments;
DROP TABLE IF EXISTS LabTechnicians;
DROP TABLE IF EXISTS Pharmacists;
DROP TABLE IF EXISTS Nurses;
DROP TABLE IF EXISTS Doctors;
DROP TABLE IF EXISTS Patients;
DROP TABLE IF EXISTS UserRoles;
DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS Roles;

-- ==========================================================
-- 3. TABLE CREATION (SCHEMA)
-- ==========================================================

-- A. AUTHENTICATION
CREATE TABLE Roles (
    role_id      INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT
);

CREATE TABLE Users (
    user_id          INTEGER PRIMARY KEY,
    username         TEXT NOT NULL UNIQUE, -- The Minecraft/System Token
    password_hash    TEXT NOT NULL,        -- SHA-256 Hash
    salt             TEXT,
    full_name        TEXT NOT NULL,
    email            TEXT UNIQUE,          -- Logical Link to Staff Tables
    is_active        INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at    TEXT
);

CREATE TABLE UserRoles (
    user_id   INTEGER NOT NULL,
    role_id   INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES Roles(role_id) ON DELETE CASCADE
);

-- B. CLINICAL ASSETS
CREATE TABLE Patients (
    patient_id   INTEGER PRIMARY KEY,
    first_name   TEXT NOT NULL,
    last_name    TEXT NOT NULL,
    dob          TEXT NOT NULL CHECK (date(dob) IS NOT NULL), 
    gender       TEXT CHECK (gender IN ('M','F','O')),
    -- SSN Format Check: ###-##-####
    ssn          TEXT UNIQUE CHECK (ssn GLOB '[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]'), 
    -- Phone Format Check: ### ### ###
    phone        TEXT CHECK (phone GLOB '[0-9][0-9][0-9] [0-9][0-9][0-9] [0-9][0-9][0-9]'),
    email        TEXT NOT NULL CHECK (email LIKE '%@%.%'), 
    address      TEXT, 
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT,
    last_modified_by INTEGER
);

-- C. STAFFING
CREATE TABLE Doctors (
    doctor_id   INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    specialty   TEXT NOT NULL,
    phone       TEXT,
    email       TEXT UNIQUE, -- Logical Link to Users
    active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE Nurses (
    nurse_id    INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    department  TEXT NOT NULL,
    phone       TEXT,
    email       TEXT UNIQUE, -- Logical Link to Users
    active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE Pharmacists (
    pharmacist_id INTEGER PRIMARY KEY,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    phone         TEXT,
    email         TEXT UNIQUE
);

CREATE TABLE LabTechnicians (
    lab_tech_id INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    phone       TEXT,
    email       TEXT UNIQUE
);

-- D. OPERATIONS
CREATE TABLE Treatments (
    treatment_id INTEGER PRIMARY KEY,
    patient_id   INTEGER NOT NULL,
    doctor_id    INTEGER NOT NULL,
    description  TEXT NOT NULL, -- Sensitive Data
    start_date   TEXT NOT NULL,
    end_date     TEXT,
    status       TEXT NOT NULL CHECK (status IN ('PLANNED','ONGOING','COMPLETED','CANCELLED')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT,
    last_modified_by INTEGER,
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    FOREIGN KEY (doctor_id)  REFERENCES Doctors(doctor_id)
);

CREATE TABLE Prescriptions (
    prescription_id INTEGER PRIMARY KEY,
    patient_id      INTEGER NOT NULL,
    doctor_id       INTEGER NOT NULL,
    pharmacist_id   INTEGER,
    medication      TEXT NOT NULL,
    dosage          TEXT NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    dispensed_at    TEXT,
    last_modified_by INTEGER,
    FOREIGN KEY (patient_id)    REFERENCES Patients(patient_id),
    FOREIGN KEY (doctor_id)     REFERENCES Doctors(doctor_id),
    FOREIGN KEY (pharmacist_id) REFERENCES Pharmacists(pharmacist_id)
);

CREATE TABLE LabResults (
    lab_result_id INTEGER PRIMARY KEY,
    patient_id    INTEGER NOT NULL,
    lab_tech_id   INTEGER NOT NULL,
    test_name     TEXT NOT NULL,
    result_value  TEXT NOT NULL,
    unit          TEXT,
    test_date     TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_modified_by INTEGER,
    FOREIGN KEY (patient_id)   REFERENCES Patients(patient_id),
    FOREIGN KEY (lab_tech_id)  REFERENCES LabTechnicians(lab_tech_id)
);

-- E. COMPLIANCE
CREATE TABLE AuditLogs (
    log_id     INTEGER PRIMARY KEY,
    user_id    INTEGER,
    action     TEXT NOT NULL,
    table_name TEXT,
    timestamp  TEXT NOT NULL DEFAULT (datetime('now')),
    details    TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- ==========================================================
-- 4. INITIAL DATA POPULATION (Team Members)
-- ==========================================================

-- ROLES (Standard definitions)
INSERT INTO Roles (role_id, name, description) VALUES
  (1, 'admin_db', 'Database Administrator'),
  (2, 'doctor', 'Medical Doctor - Full Patient Access'),
  (3, 'nurse', 'Nurse - Limited Access (No SSN)'),
  (4, 'auditor', 'Compliance Officer - View Logs Only'),
  (5, 'pharmacist', 'Pharmacist'),
  (6, 'lab_tech', 'Lab Technician'),
  (7, 'patient', 'Default role for registered patients'),
  (8, 'etl_service', 'Automated Backup & Recovery Service');

-- USERS (Linked to Minecraft Names)
-- Password for all is 'password123' (SHA-256 Hash)
INSERT INTO Users (user_id, username, password_hash, full_name, email) VALUES 
(1, 'Alba_MC',  'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Alba Prats',      'alba@hospital.com'),
(2, 'Alex_MC',  'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Alejandro Serrano', 'alex@hospital.com'),
(3, 'Tomas_MC', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Tomas Uson',      'tomas@hospital.com');

-- USER ROLES (Assigning Privileges)
INSERT INTO UserRoles (user_id, role_id) VALUES (1, 2); -- Alba = Doctor
INSERT INTO UserRoles (user_id, role_id) VALUES (2, 3); -- Alex = Nurse
INSERT INTO UserRoles (user_id, role_id) VALUES (3, 1); -- Tomas = Admin

-- STAFF PROFILES (The Logical Link via Email)
-- 1. Doctor Profile for Alba (Matches alba@hospital.com)
INSERT INTO Doctors (doctor_id, first_name, last_name, specialty, email) VALUES
(101, 'Alba', 'Prats', 'Cyber-Surgery', 'alba@hospital.com'); 

-- 2. Nurse Profile for Alex (Matches alex@hospital.com)
INSERT INTO Nurses (nurse_id, first_name, last_name, department, email) VALUES
(201, 'Alejandro', 'Serrano', 'Emergency', 'alex@hospital.com');

-- Note: Tomas is Admin, so he does not need a record in Doctor/Nurse tables, 
-- but he will have access to AuditLogs via the Admin role.

-- PATIENTS (Sensitive Data for Demo)
INSERT INTO Patients (patient_id, first_name, last_name, dob, gender, ssn, phone, email, address) VALUES
(1, 'Bruce', 'Wayne', '1980-02-19', 'M', '999-00-1234', '555 123 456', 'bruce@wayne.com', '1007 Mountain Drive'),
(2, 'Clark', 'Kent', '1978-04-18', 'M', '111-22-3333', '555 987 654', 'clark@dailyplanet.com', '344 Clinton St');

-- CLINICAL HISTORY
-- Assigned to Doctor ID 101 (Alba)
INSERT INTO Treatments (patient_id, doctor_id, description, start_date, status) VALUES
(1, 101, 'Back straightening surgery', '2025-01-10', 'COMPLETED');