import sqlite3

DB_PATH = 'hospital_mc.db'  # Path DB file


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def authorize_etl(username):
    from hospital_middleware import get_user_credentials
    ctx = get_user_credentials(username)
    return ctx and ctx['role_name'] == 'etl_service'


def run_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("      HOSPITAL SYSTEM - SECURITY AUDIT DASHBOARD      ")
    print("="*60)
    
    # 1. SUMMARY STATISTICS
    print("\n[1] ACCESS SUMMARY BY ROLE")
    cursor.execute("""
        SELECT r.name as Role, COUNT(l.log_id) as ActionCount
        FROM AuditLogs l
        JOIN Users u ON l.user_id = u.user_id
        JOIN UserRoles ur ON u.user_id = ur.user_id
        JOIN Roles r ON ur.role_id = r.role_id
        GROUP BY r.name
    """)
    rows = cursor.fetchall()
    
    # Header
    print(f"{'Role':<15} | {'Count':<10}")
    print("-" * 30)
    # Rows
    for r in rows:
        print(f"{r['Role']:<15} | {r['ActionCount']:<10}")

    # 2. SECURITY ALERTS
    print("\n[2] RECENT SECURITY ALERTS (Violations & Failures)")
    cursor.execute("""
        SELECT u.username, l.action, l.details, l.timestamp
        FROM AuditLogs l
        JOIN Users u ON l.user_id = u.user_id
        WHERE l.action IN ('ACCESS_DENIED', 'LOGIN_FAIL')
        ORDER BY l.timestamp DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print(">> No recent security violations detected.")
    else:
        print(f"{'User':<15} | {'Action':<15} | {'Time':<20} | {'Details'}")
        print("-" * 80)
        for r in rows:
            print(f"{r['username']:<15} | {r['action']:<15} | {r['timestamp'][11:19]:<20} | {r['details']}")

    # 3. CLINICAL ACCESS LOG
    print("\n[3] RECENT CLINICAL DATA ACCESS")
    cursor.execute("""
        SELECT u.username, l.action, l.details, l.timestamp
        FROM AuditLogs l
        JOIN Users u ON l.user_id = u.user_id
        WHERE l.action LIKE 'READ%'
        ORDER BY l.timestamp DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    
    if not rows:
        print(">> No recent clinical access recorded.")
    else:
        for r in rows:
            # Slicing timestamp [11:19] gives us just the HH:MM:SS time
            print(f"[{r['timestamp'][11:19]}] {r['username']} performed {r['action']}: {r['details']}")

    print("\n" + "="*60)
    conn.close()

if __name__ == "__main__":
    username = input("ETL username: ")
if not authorize_etl(username):
    print("ACCESS DENIED: Only etl_service may run dashboard.")
    exit()

    run_dashboard()