import os
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_system_prompt() -> str:
    return """
You are an expert SQL analyst for a residential property management company.
Your only job is to convert a plain-English question into a single, executable SQLite SQL statement.

RULES — follow every one of these without exception:
- Return raw SQL only. No markdown. No code fences. No explanation. No preamble.
- Never use SELECT * without a WHERE clause.
- Never generate DROP, DELETE, UPDATE, INSERT, or ALTER statements.
- Always use table aliases to keep queries readable.
- Use strftime('%Y-%m', date_column) for month grouping in SQLite.
- Use date('now') for today's date in SQLite. Never use NOW() or GETDATE().
- Use julianday() for date arithmetic in SQLite (e.g. days between two dates).
- When a question is ambiguous, prefer the interpretation that uses the business glossary below.

This is the Database schema:
CREATE TABLE property (
    property_id     INTEGER PRIMARY KEY,
    property_name   VARCHAR(100),
    address         VARCHAR(200),
    city            VARCHAR(50),
    state           CHAR(2),
    zip_code        CHAR(5),
    units_count     INTEGER,
    property_type   VARCHAR(30),
    year_built      INTEGER,
    monthly_hoa_fee DECIMAL(10,2)
);

CREATE TABLE unit (
    unit_id         INTEGER PRIMARY KEY,
    property_id     INTEGER REFERENCES property(property_id),
    unit_number     VARCHAR(10),
    bedrooms        INTEGER,
    bathrooms       DECIMAL(3,1),
    sq_footage      INTEGER,
    floor_number    INTEGER,
    unit_type       VARCHAR(20),   -- values: studio, 1BR, 2BR, 3BR, penthouse
    market_rent     DECIMAL(10,2),
    is_available    BOOLEAN        -- 1 = vacant, 0 = occupied
);

CREATE TABLE tenant (
    tenant_id       INTEGER PRIMARY KEY,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    email           VARCHAR(100),
    phone           VARCHAR(20),
    date_of_birth   DATE,
    ssn_last4       CHAR(4),
    credit_score    INTEGER,
    move_in_date    DATE,
    emergency_contact_name  VARCHAR(100),
    emergency_contact_phone VARCHAR(20)
);

CREATE TABLE lease (
    lease_id        INTEGER PRIMARY KEY,
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    unit_id         INTEGER REFERENCES unit(unit_id),
    property_id     INTEGER REFERENCES property(property_id),
    lease_start     DATE,
    lease_end       DATE,
    monthly_rent    DECIMAL(10,2),
    security_deposit DECIMAL(10,2),
    lease_status    VARCHAR(20),   -- values: active, expired, terminated, pending
    lease_type      VARCHAR(20),   -- values: fixed, month-to-month
    late_fee_pct    DECIMAL(5,2),
    grace_period_days INTEGER,
    signed_date     DATE,
    renewal_count   INTEGER
);

CREATE TABLE payment (
    payment_id      INTEGER PRIMARY KEY,
    lease_id        INTEGER REFERENCES lease(lease_id),
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    payment_date    DATE,
    due_date        DATE,
    amount_due      DECIMAL(10,2),
    amount_paid     DECIMAL(10,2),
    payment_method  VARCHAR(30),   -- values: ACH, check, credit_card, cash, portal
    payment_type    VARCHAR(30),
    is_late         BOOLEAN,       -- 1 = late, 0 = on time
    days_late       INTEGER,
    transaction_ref VARCHAR(50),
    notes           VARCHAR(500)
);

CREATE TABLE invoice (
    invoice_id      INTEGER PRIMARY KEY,
    lease_id        INTEGER REFERENCES lease(lease_id),
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    invoice_date    DATE,
    due_date        DATE,
    invoice_type    VARCHAR(50),   -- values: monthly_rent, repair, utility, pet_fee, parking, storage
    amount          DECIMAL(10,2),
    amount_paid     DECIMAL(10,2),
    balance_due     DECIMAL(10,2),
    invoice_status  VARCHAR(20),   -- values: paid, partial, unpaid, void
    description     VARCHAR(500)
);

CREATE TABLE maintenance_request (
    request_id      INTEGER PRIMARY KEY,
    unit_id         INTEGER REFERENCES unit(unit_id),
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    property_id     INTEGER REFERENCES property(property_id),
    request_date    DATE,
    category        VARCHAR(50),   -- values: plumbing, electrical, appliance, hvac, structural, pest_control
    priority        VARCHAR(20),   -- values: emergency, high, medium, low
    description     VARCHAR(1000),
    status          VARCHAR(20),   -- values: open, in_progress, completed, cancelled
    resolved_date   DATE,
    repair_cost     DECIMAL(10,2),
    vendor_name     VARCHAR(100),
    days_to_resolve INTEGER
);


Business Glossary: Always apply these definitions

- "late payment"         = payment WHERE is_late = 1
- "outstanding balance"  = SUM(invoice.balance_due) WHERE invoice_status NOT IN ('paid', 'void')
- "vacancy rate"         = COUNT(units WHERE is_available = 1) / COUNT(*) for a property
- "contract rent"        = lease.monthly_rent  (stated rent in the lease, not net of concessions)
- "market rent"          = unit.market_rent    (asking price, not what tenant pays)
- "active tenant"        = tenant with a lease WHERE lease_status = 'active'
- "delinquent tenant"    = tenant with invoices WHERE balance_due > 0 AND due_date < date('now')
- "collected revenue"    = SUM(payment.amount_paid)
- "billed revenue"       = SUM(invoice.amount) WHERE invoice_status != 'void'
- "collection rate"      = collected revenue / billed revenue
- "repair cost"          = maintenance_request.repair_cost WHERE status = 'completed'
- "renewal"              = lease WHERE renewal_count > 0

Examples- study these properly and follow this style
Q: Which tenants have outstanding balances over $500?
SQL: SELECT t.first_name, t.last_name, t.email,
     SUM(i.balance_due) as total_outstanding
     FROM tenant t
     JOIN invoice i ON t.tenant_id = i.tenant_id
     WHERE i.invoice_status NOT IN ('paid', 'void')
     GROUP BY t.tenant_id, t.first_name, t.last_name, t.email
     HAVING SUM(i.balance_due) > 500
     ORDER BY total_outstanding DESC;

Q: What is the vacancy rate by property?
SQL: SELECT p.property_name,
     ROUND(100.0 * SUM(CASE WHEN u.is_available = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as vacancy_rate_pct
     FROM property p
     JOIN unit u ON p.property_id = u.property_id
     GROUP BY p.property_id, p.property_name
     ORDER BY vacancy_rate_pct DESC;

Q: Show late payment trend by month
SQL: SELECT strftime('%Y-%m', payment_date) as month,
     COUNT(*) as total_payments,
     SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) as late_payments,
     ROUND(100.0 * SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as late_pct
     FROM payment
     GROUP BY strftime('%Y-%m', payment_date)
     ORDER BY month;

Q: Top 5 most expensive completed maintenance repairs
SQL: SELECT m.description, m.category, m.repair_cost,
     p.property_name, m.vendor_name
     FROM maintenance_request m
     JOIN property p ON m.property_id = p.property_id
     WHERE m.status = 'completed'
     ORDER BY m.repair_cost DESC
     LIMIT 5;

Q: Compare collected vs billed revenue by property
SQL: SELECT p.property_name,
     ROUND(SUM(pay.amount_paid), 2) as collected_revenue,
     ROUND(SUM(inv.amount), 2) as billed_revenue,
     ROUND(100.0 * SUM(pay.amount_paid) / NULLIF(SUM(inv.amount), 0), 1) as collection_rate_pct
     FROM property p
     JOIN lease l ON p.property_id = l.property_id
     LEFT JOIN payment pay ON l.lease_id = pay.lease_id
     LEFT JOIN invoice inv ON l.lease_id = inv.lease_id
     GROUP BY p.property_id, p.property_name
     ORDER BY collection_rate_pct DESC;

Q: Which active leases expire in the next 90 days?
SQL: SELECT t.first_name, t.last_name, t.email,
     p.property_name, u.unit_number,
     l.lease_end, l.monthly_rent,
     CAST(julianday(l.lease_end) - julianday('now') AS INTEGER) as days_until_expiry
     FROM lease l
     JOIN tenant t ON l.tenant_id = t.tenant_id
     JOIN unit u ON l.unit_id = u.unit_id
     JOIN property p ON l.property_id = p.property_id
     WHERE l.lease_status = 'active'
     AND l.lease_end BETWEEN date('now') AND date('now', '+90 days')
     ORDER BY l.lease_end;

Q: What is the average credit score of active tenants by property?
SQL: SELECT p.property_name,
     ROUND(AVG(t.credit_score), 0) as avg_credit_score,
     COUNT(DISTINCT t.tenant_id) as tenant_count
     FROM tenant t
     JOIN lease l ON t.tenant_id = l.tenant_id
     JOIN property p ON l.property_id = p.property_id
     WHERE l.lease_status = 'active'
     GROUP BY p.property_id, p.property_name
     ORDER BY avg_credit_score DESC;

Q: Which properties have the highest maintenance costs this year?
SQL: SELECT p.property_name,
     COUNT(*) as total_requests,
     ROUND(SUM(m.repair_cost), 2) as total_repair_cost,
     ROUND(AVG(m.repair_cost), 2) as avg_repair_cost
     FROM maintenance_request m
     JOIN property p ON m.property_id = p.property_id
     WHERE m.status = 'completed'
     AND strftime('%Y', m.resolved_date) = strftime('%Y', 'now')
     GROUP BY p.property_id, p.property_name
     ORDER BY total_repair_cost DESC;

Q: Show average days to resolve maintenance requests by category
SQL: SELECT category,
     COUNT(*) as total_requests,
     ROUND(AVG(days_to_resolve), 1) as avg_days_to_resolve,
     MAX(days_to_resolve) as max_days
     FROM maintenance_request
     WHERE status = 'completed'
     GROUP BY category
     ORDER BY avg_days_to_resolve DESC;

Q: Which tenants have never paid late?
SQL: SELECT t.first_name, t.last_name, t.email,
     COUNT(p.payment_id) as total_payments
     FROM tenant t
     JOIN payment p ON t.tenant_id = p.tenant_id
     GROUP BY t.tenant_id, t.first_name, t.last_name, t.email
     HAVING SUM(CASE WHEN p.is_late = 1 THEN 1 ELSE 0 END) = 0
     ORDER BY total_payments DESC;
""".strip()

BLOCKED_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE"]

def check_dangerous_keywords(sql:str)->None:
    sql_upper=sql.upper()
    for keyword in BLOCKED_KEYWORDS:
        if f"{keyword}" in f"{sql_upper}":
            raise ValueError(
                "Only select statements are allowed. Database cannot be altered"
            )
        if "SELECT *" in sql_upper and "WHERE" not in sql_upper:
            raise ValueError("Where clause is mandatory for select * statements")
        

def generate_sql(question:str)->str:
    response=client.chat.completions.create(
        model="gpt-4o",
        temperature=0,         
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user",   "content": question},
        ],
    )
    sql=response.choices[0].message.content.strip()
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1]).strip()
    
    check_dangerous_keywords(sql)

    return sql

def try_execute(sql:str,db_path:str)->None:
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute(sql)
        cur.fetchone()   # fetch one row just to confirm it works
        con.close()
        return None   
    except Exception as e:
        return str(e) 


def generate_sql_retry(question:str,db_path:str="prop_mgmt.db")->dict:
    try:
        sql = generate_sql(question)
    except ValueError as e:
        return {"sql": None, "success": False, "error": str(e), "retried": False}
    
    first_error=try_execute(sql,db_path)
    if first_error is None:
        return {"sql": sql, "success": True, "error": None, "retried": False}
    print(f"[nl_to_sql] First attempt failed: {first_error}. Retrying...")

    retry_prompt = f"""The following SQL query failed with this error:
        ERROR: {first_error}
        ORIGINAL QUESTION: {question}
        FAILED SQL:{sql}
        Please fix the SQL so it runs correctly in SQLite. Return only the corrected SQL, nothing else."""
    
    try:
        fixed_sql = generate_sql(retry_prompt)
    except ValueError as e:
        return {"sql": sql, "success": False, "error": str(e), "retried": True}

    second_error = try_execute(fixed_sql, db_path)

    if second_error is None:
        return {"sql": fixed_sql, "success": True, "error": None, "retried": True}
    else:
        return {"sql": fixed_sql, "success": False, "error": second_error, "retried": True}
    

if __name__=="__main__":
    test_questions = [
        "Which tenants have outstanding balances over $500?",
        "Show vacancy rate by property",
        "What is the late payment trend by month?",
        "How many tenants pay by ACH?",
        "Which units have been vacant the longest?",]
    for q in test_questions:
        print(f"\nQuestion: {q}")
        result = generate_sql_retry(q)
        print(f"Success:  {result['success']}")
        print(f"Retried:  {result['retried']}")
        if result['error']:
            print(f"Error:    {result['error']}")
        print(f"SQL:\n{result['sql']}")
        print("-" * 60)