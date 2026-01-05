import sqlite3
import time
import sys
import hashlib
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
DB_PATH = 'hospital_mc.db'

# UPDATED: Coordinates from your debug log to ensure it detects the hit
TERMINAL_X = 76
TERMINAL_Y = 11
TERMINAL_Z = 48

# DEFAULT DATA
DEFAULT_DOB = "2004-05-01"

# DOOR COORDS
DOOR_X = 106
DOOR_Y = 11
DOOR_Z = 38

DOOR2_X = 106
DOOR2_Y = 11
DOOR2_Z = 37




# Attempt to load Minecraft library
try:
    from mcpi.minecraft import Minecraft
    MC_AVAILABLE = True
except ImportError:
    MC_AVAILABLE = False

# Global dictionary to track registration state for Minecraft players
mc_registration_state = {}

# ==========================================
# DATABASE CONNECTION LAYER
# ==========================================
def get_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"[DB ERROR] Connection failed: {e}")
        return None

def get_table_columns(table_name):
    """Get actual column names from a table"""
    conn = get_db()
    if not conn: return []
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        print(f"[DB ERROR] Could not get columns for {table_name}: {e}")
        conn.close()
        return []

# ==========================================
# SECURITY LAYER
# ==========================================

def hash_password(plain_password):
    return hashlib.sha256(plain_password.encode()).hexdigest()

def log_audit(user_id, username, action, table_name, details):
    conn = get_db()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO AuditLogs (user_id, action, table_name, details, timestamp) 
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (user_id, action, table_name, details))
        conn.commit()
    except Exception as e:
        print(f"[AUDIT ERROR] Failed to log: {e}")
    finally:
        conn.close()

def get_user_credentials(username_input):
    conn = get_db()
    if not conn: return None
    cursor = conn.cursor()
    query = """
    SELECT u.user_id, u.username, u.password_hash, u.email, u.full_name, r.name as role_name
    FROM Users u
    JOIN UserRoles ur ON u.user_id = ur.user_id
    JOIN Roles r ON ur.role_id = r.role_id
    WHERE u.username = ? AND u.is_active = 1
    """
    cursor.execute(query, (username_input,))
    result = cursor.fetchone()
    conn.close()
    return result

# ==========================================
# ADMIN USER MANAGEMENT
# ==========================================

def admin_create_user(admin_ctx):
    if admin_ctx['role_name'] != 'admin_db':
        return "ACCESS DENIED"

    print("\n--- CREATE NEW USER ---")
    username = input("New username: ").strip()
    password = input("Password: ").strip()
    email    = input("Email: ").strip()
    full     = input("Full name: ").strip()
    role     = input("Role (doctor/nurse/pharmacist/lab_tech/auditor/admin_db/patient): ").strip()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM Users WHERE username=?", (username,))
    if cur.fetchone():
        conn.close()
        return "Username already exists."

    pw_hash = hash_password(password)
    cur.execute("INSERT INTO Users (username,password_hash,email,full_name,is_active) VALUES (?,?,?,?,1)",
                (username,pw_hash,email,full))

    user_id = cur.lastrowid
    cur.execute("SELECT role_id FROM Roles WHERE name=?", (role,))
    role_id = cur.fetchone()

    if not role_id:
        conn.rollback()
        conn.close()
        return "Invalid role."

    cur.execute("INSERT INTO UserRoles (user_id,role_id) VALUES (?,?)", (user_id, role_id['role_id']))
    conn.commit()
    log_audit(admin_ctx['user_id'], admin_ctx['username'], "ADMIN_CREATE", "Users", f"Created {username}")
    conn.close()
    return f"User {username} created successfully."


def admin_delete_user(admin_ctx):
    if admin_ctx['role_name'] != 'admin_db':
        return "ACCESS DENIED"

    username = input("Username to DELETE: ").strip()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM Users WHERE username=?", (username,))
    r = cur.fetchone()
    if not r:
        conn.close()
        return "User not found."

    cur.execute("DELETE FROM Users WHERE username=?", (username,))
    conn.commit()
    log_audit(admin_ctx['user_id'], admin_ctx['username'], "ADMIN_DELETE", "Users", f"Deleted {username}")
    conn.close()
    return f"User {username} deleted."


# ==========================================
# REGISTRATION FUNCTIONS
# ==========================================

def register_new_patient_console(username):
    """Register a new patient via console input"""
    print("\n" + "="*50)
    print("      PATIENT REGISTRATION FORM")
    print("="*50)
    
    first_name = input("Enter First Name: ").strip()
    if not first_name:
        print("[!] Registration cancelled: First name is required.")
        return False
    
    last_name = input("Enter Last Name: ").strip()
    if not last_name:
        print("[!] Registration cancelled: Last name is required.")
        return False
    
    email = input("Enter Email: ").strip()
    if not email or '@' not in email:
        print("[!] Registration cancelled: Valid email is required.")
        return False
    
    password = input("Enter Password (min 4 characters): ").strip()
    if len(password) < 4:
        print("[!] Registration cancelled: Password must be at least 4 characters.")
        return False
    
    # Optional fields with defaults
    gender = input("Enter Gender (M/F/O): ").strip().upper()
    if gender not in ['M','F','O']:
        print("[!] Invalid gender.")
        return False

    ssn = input("Enter SSN (XXX-XX-XXXX): ").strip()
    if len(ssn) != 11 or ssn[3] != '-' or ssn[6] != '-':
        print("[!] Invalid SSN format.")
        return False

    phone_number = input("Enter Phone (XXX XXX XXX): ").strip()
    if len(phone_number) != 11:
        print("[!] Invalid phone format.")
        return False

    address = input("Enter Address: ").strip()
    if not address:
        print("[!] Address is required.")
        return False

    
    return register_patient_to_db(username, first_name, last_name, email, password,
                                ssn, phone_number, address, gender)


def register_patient_to_db(username, first_name, last_name, email, password, 
                           ssn=None, phone_number=None, address=None):
    """Insert new patient and user into database"""
    conn = get_db()
    if not conn:
        print("[!] Database connection failed.")
        return False
    
    cursor = conn.cursor()
    
    try:
        # Check if username already exists
        cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"[!] Username '{username}' already exists.")
            conn.close()
            return False
        
        # Check if email already exists
        cursor.execute("SELECT email FROM Users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"[!] Email '{email}' already registered.")
            conn.close()
            return False
        
        # Get actual Patients table columns
        patient_cols = get_table_columns("Patients")
        
        # Build dynamic INSERT based on available columns
        available_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }

        # FIX: dob is NOT NULL in DB, so provide default if column exists
        if 'dob' in patient_cols:
            available_data['dob'] = DEFAULT_DOB

        
        # Add optional fields only if columns exist
        if 'ssn' in patient_cols and ssn:
            available_data['ssn'] = ssn
        if 'phone' in patient_cols and phone_number:
            available_data['phone'] = phone_number
        if 'phone_number' in patient_cols and phone_number:
            available_data['phone_number'] = phone_number
        if 'address' in patient_cols and address:
            available_data['address'] = address
        
        # Create INSERT statement dynamically
        cols = ', '.join(available_data.keys())
        placeholders = ', '.join(['?' for _ in available_data])
        values = tuple(available_data.values())
        
        insert_query = f"INSERT INTO Patients ({cols}) VALUES ({placeholders})"
        cursor.execute(insert_query, values)
        
        patient_id = cursor.lastrowid
        
        # Insert into Users table
        password_hash = hash_password(password)
        full_name = f"{first_name} {last_name}"
        
        cursor.execute("""
            INSERT INTO Users (username, password_hash, email, full_name, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (username, password_hash, email, full_name))
        
        user_id = cursor.lastrowid
        
        # Get patient role_id
        cursor.execute("SELECT role_id FROM Roles WHERE name = 'patient'")
        role_result = cursor.fetchone()
        
        if not role_result:
            print("[!] Error: 'patient' role not found in database.")
            conn.rollback()
            conn.close()
            return False
        
        role_id = role_result['role_id']
        
        # Assign patient role
        cursor.execute("""
            INSERT INTO UserRoles (user_id, role_id)
            VALUES (?, ?)
        """, (user_id, role_id))
        
        conn.commit()
        
        # Log the registration
        log_audit(user_id, username, "REGISTER", "Users", f"New patient registered: {full_name}")
        
        print(f"\n[+] SUCCESS! Patient '{full_name}' registered with username '{username}'")
        print(f"[+] Patient ID: {patient_id} | User ID: {user_id}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"[!] Database error during registration: {e}")
        conn.rollback()
        conn.close()
        return False

def process_minecraft_registration(mc, player_name, chat_message):
    """Handle step-by-step registration via Minecraft chat"""
    
    # Initialize state if new player
    if player_name not in mc_registration_state:
        mc_registration_state[player_name] = {
            'step': 0,
            'data': {}
        }
    
    state = mc_registration_state[player_name]
    msg = chat_message.lower().strip()
    
    # Step 0: Ask if they want to register
    if state['step'] == 0:
        if msg in ['yes', 'y', 'si', 's']:
            state['step'] = 1
            mc.postToChat("Great! Let's start registration.")
            mc.postToChat("Step 1: Type your FIRST NAME in chat")
            return True
        else:
            mc.postToChat("Registration cancelled.")
            del mc_registration_state[player_name]
            return False
    
    # Step 1: First Name
    elif state['step'] == 1:
        if len(msg) < 2:
            mc.postToChat("Name too short. Try again:")
            return True
        state['data']['first_name'] = chat_message.strip()
        state['step'] = 2
        mc.postToChat(f"First Name: {state['data']['first_name']}")
        mc.postToChat("Step 2: Type your LAST NAME")
        return True
    
    # Step 2: Last Name
    elif state['step'] == 2:
        if len(msg) < 2:
            mc.postToChat("Name too short. Try again:")
            return True
        state['data']['last_name'] = chat_message.strip()
        state['step'] = 3
        mc.postToChat(f"Last Name: {state['data']['last_name']}")
        mc.postToChat("Step 3: Type your EMAIL")
        return True
    
    # Step 3: Email
    elif state['step'] == 3:
        if '@' not in msg:
            mc.postToChat("Invalid email. Must contain @. Try again:")
            return True
        state['data']['email'] = chat_message.strip()
        state['step'] = 4
        mc.postToChat(f"Email: {state['data']['email']}")
        mc.postToChat("Step 4: Type your PASSWORD (min 4 chars)")
        return True
    
    # Step 4: Password
    elif state['step'] == 4:
        if len(msg) < 4:
            mc.postToChat("Password too short (min 4). Try again:")
            return True
        state['data']['password'] = chat_message.strip()
        state['step'] = 5
        mc.postToChat("Password saved!")
        mc.postToChat("Finalizing registration...")
        
        # Complete registration
        success = register_patient_to_db(
            username=player_name,
            first_name=state['data']['first_name'],
            last_name=state['data']['last_name'],
            email=state['data']['email'],
            password=state['data']['password']
        )
        
        if success:
            mc.postToChat("=== REGISTRATION COMPLETE ===")
            mc.postToChat(f"Welcome {state['data']['first_name']}!")
            mc.postToChat("Hit the terminal again to login!")
            print(f"[MC REG] Successfully registered player: {player_name}")
        else:
            mc.postToChat("Registration failed. Username or email may already exist.")
            print(f"[MC REG] Failed to register player: {player_name}")
        
        del mc_registration_state[player_name]
        return False
    
    return True

# ==========================================
# BUSINESS LOGIC (MAC & RLS ENFORCEMENT)
# ==========================================

def request_patient_data(user_context, patient_id_requested):
    user_id = user_context['user_id']
    username = user_context['username']
    role = user_context['role_name']
    email = user_context['email']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Patients WHERE patient_id = ?", (patient_id_requested,))
    patient = cursor.fetchone()
    
    if not patient:
        log_audit(user_id, username, "READ_FAIL", "Patients", f"Invalid ID {patient_id_requested}")
        conn.close()
        return "Error: Patient record not found."

    response_msg = ""
    if role == 'doctor':
        cursor.execute("SELECT doctor_id FROM Doctors WHERE email = ?", (email,))
        doc_record = cursor.fetchone()
        if doc_record:
            log_audit(user_id, username, "READ_SENSITIVE", "Patients", f"Viewed full record ID {patient_id_requested}")
            cursor.execute("SELECT description, status FROM Treatments WHERE patient_id=?", (patient_id_requested,))
            treatments = cursor.fetchall()
            tx_str = ", ".join([f"{t['description']}" for t in treatments]) if treatments else "None"
            ssn_display = patient['ssn'] if patient['ssn'] else "N/A"
            response_msg = (f"DR VIEW: {patient['first_name']} {patient['last_name']} | SSN: {ssn_display} | Tx: {tx_str}")
        else:
             response_msg = "ERROR: User has Doctor role but no HR record found."
    elif role == 'nurse':
        log_audit(user_id, username, "READ_PARTIAL", "Patients", f"Viewed masked record ID {patient_id_requested}")
        if patient['ssn']:
            masked_ssn = "***-**-" + patient['ssn'][-4:]
        else:
            masked_ssn = "N/A"
        response_msg = (f"NURSE VIEW: {patient['first_name']} {patient['last_name']} | SSN: {masked_ssn} | Tx: [RESTRICTED]")
    elif role == 'admin_db':
        log_audit(user_id, username, "ACCESS_ATTEMPT", "Patients", "Admin accessed patient view")
        response_msg = f"ADMIN VIEW: Patient ID {patient['patient_id']} exists. Clinical Data Access: DENIED."

    # ETL SERVICE — Compliance Authority New Addition just for checking everything :)
    elif role == 'etl_service':
        return "ACCESS DENIED: Compliance role has no clinical privileges."
    
    elif role == 'patient':
        # Patients can only view their own records
        cursor.execute("SELECT patient_id FROM Patients WHERE email = ?", (email,))
        patient_record = cursor.fetchone()
        if patient_record and patient_record['patient_id'] == patient_id_requested:
            log_audit(user_id, username, "READ_OWN", "Patients", f"Patient viewed own record ID {patient_id_requested}")
            
            # Handle different possible column names
            phone = patient.get('phone') or patient.get('phone_number') or "N/A"
            
            response_msg = f"YOUR RECORD: {patient['first_name']} {patient['last_name']} | Email: {patient['email']} | Phone: {phone}"
        else:
            log_audit(user_id, username, "ACCESS_DENIED", "Patients", f"Patient attempted to view other record ID {patient_id_requested}")
            response_msg = "ACCESS DENIED: You can only view your own medical records."
    else:
        log_audit(user_id, username, "ACCESS_DENIED", "Patients", f"Role '{role}' attempted unauthorized read.")
        response_msg = "ACCESS DENIED: Insufficient Privileges."

    conn.close()
    return response_msg

# ==========================================
# INTERFACE MODES
# ==========================================

def run_minecraft_mode():
    if not MC_AVAILABLE:
        print("[!] Cannot start: 'mcpi' library not installed.")
        return
    
    try:
        mc = Minecraft.create()
        print(f"\n[SYSTEM] Minecraft Connected. Monitoring Block at {TERMINAL_X}, {TERMINAL_Y}, {TERMINAL_Z}...")
        mc.postToChat("Hospital Security Online.")
        mc.postToChat("Type 'REGISTER' in chat to sign up!")
        
        while True:
            # Check for chat messages (for registration)
            chat_posts = mc.events.pollChatPosts()
            for post in chat_posts:
                #player_name = post.entityId  # In some versions this is the player name or ID
                #message = post.message

                entity_id = post.entityId
                player_name = mc.entity.getName(entity_id)
                message = post.message

                # Handle registration flow
                if message.lower().strip() == 'register' and player_name not in mc_registration_state:
                    # Check if already registered
                    user_context = get_user_credentials(player_name)
                    if not user_context:
                        mc.postToChat(f"{player_name}: Starting registration...")
                        mc.postToChat("Do you want to register as a patient? (Type 'yes' or 'no')")
                        mc_registration_state[player_name] = {'step': 0, 'data': {}}
                    else:
                        mc.postToChat(f"{player_name}: Already registered! Hit the terminal.")
                
                # Process ongoing registration
                elif player_name in mc_registration_state:
                    process_minecraft_registration(mc, player_name, message)
            
            # Check for block hits (terminal access)
            hits = mc.events.pollBlockHits()
            for hit in hits:
                print(f"[DEBUG] Block hit at: {hit.pos.x}, {hit.pos.y}, {hit.pos.z}")
                if (TERMINAL_X - 1 <= hit.pos.x <= TERMINAL_X + 1) and \
                   (TERMINAL_Z - 1 <= hit.pos.z <= TERMINAL_Z + 1):
                    
                    player_name = mc.entity.getName(hit.entityId)
                    user_context = get_user_credentials(player_name)
                    
                    if user_context:
                        # User exists - show their info
                        role = user_context['role_name']
                        mc.postToChat(f"Greetings {player_name}! Role: {role}")
                        
                        result = request_patient_data(user_context, 1) 
                        mc.postToChat(result)
                        print(f"[MC] Data sent to {player_name} ({role})")
                    else:
                        # User not found - prompt registration
                        mc.postToChat(f"User '{player_name}' not registered.")
                        mc.postToChat("Type 'REGISTER' in chat to sign up!")
                        print(f"[!] Unregistered player: {player_name}")
                
                # ---- PHYSICAL DOOR (MAC ZONE) ----
                # ---- PHYSICAL DOOR (MAC ZONE) ----
                if (
                    (hit.pos.x == DOOR_X  and hit.pos.y == DOOR_Y  and hit.pos.z == DOOR_Z) or
                    (hit.pos.x == DOOR2_X and hit.pos.y == DOOR2_Y and hit.pos.z == DOOR2_Z)
                ):

                    player_name = mc.entity.getName(hit.entityId)
                    user_ctx = get_user_credentials(player_name)

                    if not user_ctx:
                        mc.postToChat("🚫 You must be registered to enter this ward.")
                        continue

                    if not enforce_physical_door_access(mc, user_ctx, hit.pos):
                        log_audit(user_ctx['user_id'], player_name, "PHYSICAL_DENY", "WardDoor", "Blocked from ward")
                        continue


                    log_audit(user_ctx['user_id'], player_name, "PHYSICAL_GRANT", "WardDoor", "Entered ward")
                    continue


            
            time.sleep(0.2)
    except Exception as e:
        print(f"[MC ERROR] {e}")

def run_console_simulation_mode():
    print("\n" + "="*50)
    print("      HOSPITAL SECURITY - CONSOLE SIMULATION      ")
    print("="*50)

    while True:
        print("-" * 30)
        username_input = input("Enter Username (or 'q' to exit): ").strip()
        if username_input.lower() == 'q': break
        
        user_context = get_user_credentials(username_input)
        if not user_context:
            print(f"[!] User '{username_input}' not found in system.")
            register_choice = input("Would you like to register as a patient? (yes/no): ").strip().lower()
            
            if register_choice in ['yes', 'y', 'si', 's']:
                if register_new_patient_console(username_input):
                    print("[+] Registration successful! Please login with your new credentials.")
                else:
                    print("[!] Registration failed. Please try again.")
            else:
                print("[*] Registration cancelled.")
            continue
            
        password_input = input(f"Enter Password for {username_input}: ").strip()
        if hash_password(password_input) == user_context['password_hash']:
            # Greeting with Role
            role = user_context['role_name']
            print(f"\n[+] Greetings {user_context['full_name']}! Your role is: {role}")
            
            while True:
                if role == 'admin_db':
                    print("   1) Create User")
                    print("   2) Delete User")
                    print("   3) Logout")
                    c = input("   Select: ").strip()

                    if c == '1':
                        print(admin_create_user(user_context))
                    elif c == '2':
                        print(admin_delete_user(user_context))
                    else:
                        break
                else:
                    cmd = input(f"   ({username_input}) Enter Patient ID or 'logout': ").strip()
                    if cmd.lower() == 'logout': break
                    if not cmd.isdigit(): 
                        print("   [!] Please enter a valid Patient ID number.")
                        continue

                    print(f"   [*] Verifying Access Policies...")
                    result = request_patient_data(user_context, int(cmd))
                    print(f"   >> RESPONSE: {result}\n")

                if cmd.lower() == 'logout': break
                if not cmd.isdigit(): 
                    print("   [!] Please enter a valid Patient ID number.")
                    continue
                
                print(f"   [*] Verifying Access Policies...")
                result = request_patient_data(user_context, int(cmd))
                print(f"   >> RESPONSE: {result}\n")
        else:
            print(f"[!] AUTH FAILED: Invalid Password.")
            log_audit(user_context['user_id'], username_input, "LOGIN_FAIL", "Users", "Invalid password")

# ==========================================
# DOOR SECTION
# ==========================================


def enforce_physical_door_access(mc, user_ctx, pos):
    # Normalize to bottom half of the door
    base_y = pos.y
    block = mc.getBlockWithData(pos.x, pos.y, pos.z)

    # If player clicked top half, move down one block
    if block.data & 0x8:
        base_y = pos.y - 1

    if user_ctx['role_name'] != 'doctor':
        mc.postToChat("🚫 ACCESS DENIED: Only doctors may enter this ward.")
        time.sleep(0.12)

        bottom = mc.getBlockWithData(pos.x, base_y, pos.z)
        top    = mc.getBlockWithData(pos.x, base_y + 1, pos.z)

        closed_bottom = bottom.data & ~0x4
        closed_top    = top.data & ~0x4

        mc.setBlock(pos.x, base_y, pos.z, bottom.id, closed_bottom)
        mc.setBlock(pos.x, base_y + 1, pos.z, top.id, closed_top)
        return False

    mc.postToChat("✅ ACCESS GRANTED: Welcome Doctor.")
    return True


# ==========================================
# MAIN EXECUTION MENU
# ==========================================

if __name__ == "__main__":
    print("--- HOSPITAL SECURITY MIDDLEWARE ---")
    
    # Check database schema on startup
    print("\n[SYSTEM] Checking database schema...")
    patient_cols = get_table_columns("Patients")
    if patient_cols:
        print(f"[OK] Patients table columns: {', '.join(patient_cols)}")
    else:
        print("[ERROR] Could not read Patients table schema")
        sys.exit(1)
    
    print("\nSelect Mode:")
    print("1. Minecraft Mode")
    print("2. Console Simulation Mode")
    
    choice = input("\nSelect (1/2): ").strip()
    
    if choice == '1':
        run_minecraft_mode()
    elif choice == '2':
        run_console_simulation_mode()
    else:
        print("Invalid choice. Exiting.")