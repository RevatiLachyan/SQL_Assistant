import sqlite3
import random
from datetime import date, timedelta
from faker import Faker
from decimal import Decimal
import os

fake=Faker()
random.seed(42)
Faker.seed(42)

DB_PATH = "prop_mgmt.db"  
NUM_PROPERTIES = 8
NUM_UNITS = 120
NUM_TENANTS = 110
NUM_LEASES = 105


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def generate_property(n: int)->list[dict]:
    property_type=["residential"]
    cities=[
        ("Dallas","TX"),("Boston","MA"),("Phoenix","AZ"),("Charlotte","NC"),("Los Angeles","CA"),("Atlanta","GA"),("Denver","CO")
    ]

    records=[]
    i=1
    for i in range(i,n+1):
        city,state=random.choice(cities)
        units=random.choice([10,15,18,20,25])
        records.append({
            "property_id":     i,
            "property_name":   f"{fake.last_name()} {random.choice(['Apartments','Commons','Place','Residences','Flats'])}",
            "address":         fake.street_address(),
            "city":            city,
            "state":           state,
            "zip_code":        fake.zipcode()[:5],
            "units_count":     units,
            "property_type":   random.choice(property_type),
            "year_built":      random.randint(1985, 2020),
            "monthly_hoa_fee": round(random.uniform(50, 300), 2),
        })
    return records


def generate_units(properties:list[dict])->list[dict]:
    unit_types = ["studio", "1BR", "1BR", "2BR", "2BR", "2BR", "3BR", "penthouse"]
    rent_map = {"studio": (900, 1400), "1BR": (1200, 1900),
                "2BR": (1700, 2600), "3BR": (2400, 3500), "penthouse": (3500, 6000)}
    records = []
    uid=1
    for prop in properties:
        for i in range(prop["units_count"]):
            utype = random.choice(unit_types)
            lo, hi = rent_map[utype]
            beds = {"studio": 0, "1BR": 1, "2BR": 2, "3BR": 3, "penthouse": 3}[utype]
            baths = {"studio": 1.0, "1BR": 1.0, "2BR": 2.0, "3BR": 2.0, "penthouse": 3.0}[utype]
            records.append({
                "unit_id":      uid,
                "property_id":  prop["property_id"],
                "unit_number":  f"{random.randint(1,4)}{i:02d}",
                "bedrooms":     beds,
                "bathrooms":    baths,
                "sq_footage":   random.randint(450, 2200),
                "floor_number": random.randint(1, 4),
                "unit_type":    utype,
                "market_rent":  round(random.uniform(lo, hi), 2),
                "is_available": random.random() < 0.1,  # 10% vacant
            })
            uid+=1
    return records

def generate_tenants(n:int):
    records = []
    for i in range(1, n + 1):
        move_in = random_date(date(2022, 1, 1), date(2026, 5, 1))
        records.append({
            "tenant_id":               i,
            "first_name":              fake.first_name(),
            "last_name":               fake.last_name(),
            "email":                   fake.email(),
            "phone":                   fake.phone_number()[:20],
            "date_of_birth":           random_date(date(1965, 1, 1), date(2000, 12, 31)),
            "ssn_last4":               str(random.randint(1000, 9999)),
            "credit_score":            random.randint(580, 820),
            "move_in_date":            move_in,
            "emergency_contact_name":  fake.name(),
            "emergency_contact_phone": fake.phone_number()[:20],
        })
    return records

def has_overlap(existing_leases: list[dict], unit_id: int, start: date, end: date) -> bool:
    for lease in existing_leases:
        if lease["unit_id"] == unit_id:
            if start <= lease["lease_end"] and end >= lease["lease_start"]:
                return True
    return False

def generate_leases(tenants:list[dict],units:list[dict])->list[dict]:
    statuses = ["active", "active", "active", "active", "expired", "terminated", "pending"]
    lease_types = ["fixed", "fixed", "fixed", "month-to-month"]
    unit_ids = [u["unit_id"] for u in units]
    units_by_id={u["unit_id"]: u for u in units}
    records=[]
    for i,tenant in enumerate(tenants):
        start=tenant["move_in_date"]
        end=start+timedelta(days=random.choice([365,365,730,548]))
        shuffles_ids=random.sample(unit_ids,len(unit_ids))
        unit_id=next((uid for uid in shuffles_ids if not has_overlap(records,uid,start,end)),None)
        if unit_id is None:
            continue

        unit=units_by_id[unit_id]
        status=random.choice(statuses)
        if end<date.today() and status=="active":
            status="expired"
        monthly = round(unit["market_rent"] * random.uniform(0.9, 1.05), 2)
        records.append({
            "lease_id": i + 1,
            "tenant_id": tenant["tenant_id"],
            "unit_id": unit_id,
            "property_id": unit["property_id"],
            "lease_start": start,
            "lease_end": end,
            "monthly_rent": monthly,
            "security_deposit": monthly,
            "lease_status": status,
            "lease_type": random.choice(lease_types),
            "late_fee_pct": 5.0,
            "grace_period_days": random.choice([3, 5, 5]),
            "signed_date": start - timedelta(days=random.randint(7, 30)),
            "renewal_count": random.randint(0, 3),
        })
    return records

def next_month(d:date)->date:
    if d.month==12:
        return date(d.year+1,1,1)
    return date(d.year,d.month+1,1)

def generate_payments(leases:list[dict])->list[dict]:
    methods = ["ACH", "ACH", "ACH", "check", "credit_card", "portal", "cash"]
    records = []
    pid = 1

    for lease in leases:
        start = lease["lease_start"]
        end = min(lease["lease_end"], date.today())
        current = date(start.year, start.month, 1)

        while current <= end:
            due = date(current.year, current.month, 1)

            if random.random()>0.7:
                current=next_month(current)
                continue

            days_offset= random.choices(
                [-3, -2, -1, 0, 0, 0, 1, 3, 5, 8, 12, 20],
                weights=[2, 3, 5, 20, 20, 20, 5, 5, 5, 5, 5, 5],
                k=1
            )[0]

            paid_date=due+timedelta(days=days_offset)
            grace=lease["grace_period_days"]
            is_late=days_offset>grace
            amount_due=lease["monthly_rent"]
            if random.random() > 0.05:
                amount_paid = amount_due        # 95% of the time: full payment
            else:
                amount_paid = round(amount_due * random.uniform(0.5, 0.95), 2)

            records.append({
                "payment_id":      pid,
                "lease_id":        lease["lease_id"],
                "tenant_id":       lease["tenant_id"],
                "payment_date":    paid_date,
                "due_date":        due,
                "amount_due":      amount_due,
                "amount_paid":     amount_paid,
                "payment_method":  random.choice(methods),
                "payment_type":    "rent",
                "is_late":         is_late,
                "days_late":       max(0, days_offset - grace) if is_late else 0,
                "transaction_ref": fake.bothify("??######"),
                "notes":           None,
            })
            pid += 1
            current=next_month(current)
    return records


def generate_invoices(leases:list[dict])-> list[dict]:
    inv_types = [
        ("monthly_rent", 0.5), ("repair", 0.15), ("utility", 0.15),
        ("pet_fee", 0.08), ("parking", 0.07), ("storage", 0.05),
    ]
    statuses = {"paid": 0.65, "partial": 0.10, "unpaid": 0.20, "void": 0.05}
    inv_id=1
    records = []

    for lease in leases:
        num_invoices=random.randint(3,18)
        for i in range(1,num_invoices):
            inv_type=random.choices(
                 [t[0] for t in inv_types], weights=[t[1] for t in inv_types]
            )[0]

            amount=(
                 lease["monthly_rent"] if inv_type == "monthly_rent"
                else round(random.uniform(50, 800), 2)
            )
            inv_date = random_date(lease["lease_start"], min(lease["lease_end"], date.today()))
            due = inv_date + timedelta(days=30)
            due = inv_date + timedelta(days=30)
            status = random.choices(list(statuses.keys()), weights=list(statuses.values()))[0]
            paid = (
                amount if status == "paid"
                else round(amount * random.uniform(0.3, 0.8), 2) if status == "partial"
                else 0
            )
            records.append({
                "invoice_id":     inv_id,
                "lease_id":       lease["lease_id"],
                "tenant_id":      lease["tenant_id"],
                "invoice_date":   inv_date,
                "due_date":       due,
                "invoice_type":   inv_type,
                "amount":         amount,
                "amount_paid":    paid,
                "balance_due":    round(amount - paid, 2),
                "invoice_status": status,
                "description":    f"{inv_type.replace('_', ' ').title()} charge",
            })
            inv_id += 1
    return records


def generate_maintenance(units:list[dict],leases:list[dict])->list[dict]:
    categories = ["plumbing", "electrical", "appliance", "hvac", "structural", "pest_control"]
    priorities = ["emergency", "high", "medium", "medium", "low", "low"]
    statuses_w = {"open": 0.15, "in_progress": 0.10, "completed": 0.70, "cancelled": 0.05}
    descriptions = {
        "plumbing": ["Leaking faucet in bathroom", "Clogged drain", "Running toilet", "Low water pressure"],
        "electrical": ["Outlet not working", "Light fixture flickering", "Breaker keeps tripping", "No power in bedroom"],
        "appliance": ["Refrigerator not cooling", "Dishwasher leaking", "Oven not heating", "Washer making noise"],
        "hvac": ["AC not cooling", "Heat not working", "Strange smell from vents", "Thermostat unresponsive"],
        "structural": ["Window won't close", "Door lock broken", "Crack in wall", "Ceiling water stain"],
        "pest_control": ["Cockroach sighting", "Mouse in unit", "Ant infestation", "Bed bug concern"],
    }
    records = []
    req_id=1
    for lease in leases:
        num_requests=random.randint(0,5)
        for i in range(1,num_requests):
            cat=random.choice(categories)
            req_date = random_date(lease["lease_start"], min(lease["lease_end"], date.today()))
            status = random.choices(list(statuses_w.keys()), weights=list(statuses_w.values()))[0]
            resolved = req_date + timedelta(days=random.randint(1, 30)) if status == "completed" else None
            records.append({
                "request_id":      req_id,
                "unit_id":         lease["unit_id"],
                "tenant_id":       lease["tenant_id"],
                "property_id":     lease["property_id"],
                "request_date":    req_date,
                "category":        cat,
                "priority":        random.choice(priorities),
                "description":     random.choice(descriptions[cat]),
                "status":          status,
                "resolved_date":   resolved,
                "repair_cost":     round(random.uniform(50, 2000), 2) if resolved else None,
                "vendor_name":     fake.company() if resolved else None,
                "days_to_resolve": (resolved - req_date).days if resolved else None,
            })
            req_id+=1
    return records
            
def insert(con,table:str,rows:list[dict]):
    if not rows :
        return
    cols=", ".join(rows[0].keys())
    placeholders=", ".join(["?" for _ in rows[0]])
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    con.executemany(sql, [list(r.values()) for r in rows])
    print(f"Inserted {len(rows):>5} rows into {table}")
    


def load_to_db(con,property,tenant,unit,lease,payment,invoice,maintenance):
    cur=con.cursor()

    for table in ["maintenance_request", "payment", "invoice", 
              "lease", "tenant", "unit", "property"]:
        con.execute(f"DROP TABLE IF EXISTS {table}")

    with open("schema.sql","r")as f:
        schema=f.read()
    
    for statement in schema.split(";"):
        statement = statement.strip()
        if statement:
            con.execute(statement)
    
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables:", tables)

    print("Loading data into DuckDB")
    insert(con,"property", property)
    insert(con,"unit", unit)
    insert(con,"tenant", tenant)
    insert(con,"lease", lease)
    insert(con,"payment", payment)
    insert(con,"invoice", invoice)
    insert(con,"maintenance_request", maintenance)
    con.commit()

    con.close()
    print("Database records inserted")


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON") 
    print("Generating synthetic property management data.")
    props    = generate_property(NUM_PROPERTIES)
    units    = generate_units(props)
    tenants  = generate_tenants(NUM_TENANTS)
    leases   = generate_leases(tenants, units)
    payments = generate_payments(leases)
    invoices = generate_invoices(leases)
    maint    = generate_maintenance(units, leases)

    print(f"  Properties:  {len(props)}")
    print(f"  Units:       {len(units)}")
    print(f"  Tenants:     {len(tenants)}")
    print(f"  Leases:      {len(leases)}")
    print(f"  Payments:    {len(payments)}")
    print(f"  Invoices:    {len(invoices)}")
    print(f"  Maintenance: {len(maint)}")

    load_to_db(con,props, tenants, units, leases, payments, invoices, maint)





