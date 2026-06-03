CREATE TABLE IF NOT EXISTS property (
    property_id     INTEGER PRIMARY KEY,
    property_name   VARCHAR(100) NOT NULL,
    address         VARCHAR(200),
    city            VARCHAR(50),
    state           CHAR(2),
    zip_code        CHAR(5),
    units_count     INTEGER,
    property_type   VARCHAR(30),   -- 'residential', 'commercial', 'mixed'
    year_built      INTEGER,
    monthly_hoa_fee DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS unit (
    unit_id         INTEGER PRIMARY KEY,
    property_id     INTEGER REFERENCES property(property_id),
    unit_number     VARCHAR(10) NOT NULL,  -- e.g. '101', '2B'
    bedrooms        INTEGER,
    bathrooms       DECIMAL(3,1),
    sq_footage      INTEGER,
    floor_number    INTEGER,
    unit_type       VARCHAR(20),   -- 'studio','1BR','2BR','3BR','penthouse'
    market_rent     DECIMAL(10,2), -- current asking rent
    is_available    BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS tenant (
    tenant_id       INTEGER PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(100),
    phone           VARCHAR(20),
    date_of_birth   DATE,
    ssn_last4       CHAR(4),       -- last 4 only, realistic for prop mgmt
    credit_score    INTEGER,
    move_in_date    DATE,
    emergency_contact_name  VARCHAR(100),
    emergency_contact_phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS lease (
    lease_id        INTEGER PRIMARY KEY,
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    unit_id         INTEGER REFERENCES unit(unit_id),
    property_id     INTEGER REFERENCES property(property_id),
    lease_start     DATE NOT NULL,
    lease_end       DATE NOT NULL,
    monthly_rent    DECIMAL(10,2) NOT NULL,
    security_deposit DECIMAL(10,2),
    lease_status    VARCHAR(20),   -- 'active','expired','terminated','pending'
    lease_type      VARCHAR(20),   -- 'fixed','month-to-month'
    late_fee_pct    DECIMAL(5,2) DEFAULT 5.00,  -- % charged after grace period
    grace_period_days INTEGER DEFAULT 5,
    signed_date     DATE,
    renewal_count   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payment (
    payment_id      INTEGER PRIMARY KEY,
    lease_id        INTEGER REFERENCES lease(lease_id),
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    payment_date    DATE NOT NULL,
    due_date        DATE NOT NULL,
    amount_due      DECIMAL(10,2) NOT NULL,
    amount_paid     DECIMAL(10,2) NOT NULL,
    payment_method  VARCHAR(30),   -- 'ACH','check','credit_card','cash','portal'
    payment_type    VARCHAR(30),   -- 'rent','late_fee','deposit','pet_fee'
    is_late         BOOLEAN,
    days_late       INTEGER DEFAULT 0,
    transaction_ref VARCHAR(50),   -- check # or ACH trace number
    notes           VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS invoice (
    invoice_id      INTEGER PRIMARY KEY,
    lease_id        INTEGER REFERENCES lease(lease_id),
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    invoice_date    DATE NOT NULL,
    due_date        DATE NOT NULL,
    invoice_type    VARCHAR(50),   -- 'monthly_rent','repair','utility','pet_fee'
    amount          DECIMAL(10,2) NOT NULL,
    amount_paid     DECIMAL(10,2) DEFAULT 0,
    balance_due     DECIMAL(10,2), -- amount - amount_paid
    invoice_status  VARCHAR(20),   -- 'paid','partial','unpaid','void'
    description     VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS maintenance_request (
    request_id      INTEGER PRIMARY KEY,
    unit_id         INTEGER REFERENCES unit(unit_id),
    tenant_id       INTEGER REFERENCES tenant(tenant_id),
    property_id     INTEGER REFERENCES property(property_id),
    request_date    DATE NOT NULL,
    category        VARCHAR(50),   -- 'plumbing','electrical','appliance','hvac'
    priority        VARCHAR(20),   -- 'emergency','high','medium','low'
    description     VARCHAR(1000),
    status          VARCHAR(20),   -- 'open','in_progress','completed','cancelled'
    resolved_date   DATE,
    repair_cost     DECIMAL(10,2),
    vendor_name     VARCHAR(100),
    days_to_resolve INTEGER        -- computed: resolved_date - request_date
);