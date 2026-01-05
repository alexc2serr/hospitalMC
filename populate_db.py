import sqlite3
import random
import hashlib

DB_PATH = 'hospital_mc.db'

# Lists for random generation
FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
SPECIALTIES = ["Cardiology", "Neurology", "Pediatrics", "Oncology", "Surgery", "General Practice"]
DEPARTMENTS = ["ER", "ICU", "Pediatrics", "General Ward", "Oncology Ward"]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def populate():
    conn = get_db()
    cursor = conn.cursor()
    
    print("--- STARTING BULK POPULATION ---")

    # 1. GENERATE 20 DOCTORS
    print("Generating 20 Doctors...")
    for i in range(1, 21):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        email = f"doctor{i}@hospital.com"
        username = f"Dr_{fname}_{i}"
        
        # Create User Account
        cursor.execute("INSERT OR IGNORE INTO Users (username, password_hash, full_name, email) VALUES (?, ?, ?, ?)",
                       (username, hash_pw("password123"), f"{fname} {lname}", email))
        user_id = cursor.lastrowid
        
        if user_id:
            # Assign Role (2 = Doctor)
            cursor.execute("INSERT OR IGNORE INTO UserRoles (user_id, role_id) VALUES (?, ?)", (user_id, 2))
            # Create Doctor Record
            cursor.execute("INSERT OR IGNORE INTO Doctors (first_name, last_name, specialty, email) VALUES (?, ?, ?, ?)",
                           (fname, lname, random.choice(SPECIALTIES), email))

    # 2. GENERATE 40 NURSES
    print("Generating 40 Nurses...")
    for i in range(1, 41):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        email = f"nurse{i}@hospital.com"
        username = f"Nurse_{fname}_{i}"
        
        cursor.execute("INSERT OR IGNORE INTO Users (username, password_hash, full_name, email) VALUES (?, ?, ?, ?)",
                       (username, hash_pw("password123"), f"{fname} {lname}", email))
        user_id = cursor.lastrowid
        
        if user_id:
            # Assign Role (3 = Nurse)
            cursor.execute("INSERT OR IGNORE INTO UserRoles (user_id, role_id) VALUES (?, ?)", (user_id, 3))
            cursor.execute("INSERT OR IGNORE INTO Nurses (first_name, last_name, department, email) VALUES (?, ?, ?, ?)",
                           (fname, lname, random.choice(DEPARTMENTS), email))

    # 3. GENERATE 5 PHARMACISTS
    print("Generating 5 Pharmacists...")
    for i in range(1, 6):
        fname = random.choice(FIRST_NAMES)
        email = f"pharma{i}@hospital.com"
        cursor.execute("INSERT OR IGNORE INTO Pharmacists (first_name, last_name, email) VALUES (?, ?, ?)",
                       (fname, "Pharma", email))
        # Note: We create the Staff record, but maybe not a User login for every single one if not needed for demo

        # 4. GENERATE 5 LAB TECHS
    print("Generating 5 Lab Techs...")
    for i in range(1, 6):
        fname = random.choice(FIRST_NAMES)
        email = f"lab{i}@hospital.com"
        cursor.execute("INSERT OR IGNORE INTO LabTechnicians (first_name, last_name, email) VALUES (?, ?, ?)",
                       (fname, "Tech", email))

    conn.commit()
    conn.close()
    print("--- POPULATION COMPLETE ---")

if __name__ == "__main__":
    populate()