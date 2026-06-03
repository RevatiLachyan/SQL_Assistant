SELECT 'property'            AS tbl, COUNT(*) AS row_count FROM property
UNION ALL
SELECT 'unit',                         COUNT(*) FROM unit
UNION ALL
SELECT 'tenant',                       COUNT(*) FROM tenant
UNION ALL
SELECT 'lease',                        COUNT(*) FROM lease
UNION ALL
SELECT 'payment',                      COUNT(*) FROM payment
UNION ALL
SELECT 'invoice',                      COUNT(*) FROM invoice
UNION ALL
SELECT 'maintenance_request',          COUNT(*) FROM maintenance_request
ORDER BY tbl;


-- Leases pointing to non-existent tenants
SELECT 'orphan lease->tenant' AS check_name, COUNT(*) AS violations
FROM lease l
LEFT JOIN tenant t ON l.tenant_id = t.tenant_id
WHERE t.tenant_id IS NULL

UNION ALL

-- Leases pointing to non-existent units
SELECT 'orphan lease->unit', COUNT(*)
FROM lease l
LEFT JOIN unit u ON l.unit_id = u.unit_id
WHERE u.unit_id IS NULL

UNION ALL

-- Payments pointing o non-existent leases
SELECT 'orphan payment->lease', COUNT(*)
FROM payment p
LEFT JOIN lease l ON p.lease_id = l.lease_id
WHERE l.lease_id IS NULL

UNION ALL

-- Invoices pointing to non-existent tenants
SELECT 'orphan invoice->tenant', COUNT(*)
FROM invoice i
LEFT JOIN tenant t ON i.tenant_id = t.tenant_id
WHERE t.tenant_id IS NULL

UNION ALL

-- Maintenance pointing to non-existent units
SELECT 'orphan maintenance->unit', COUNT(*)
FROM maintenance_request m
LEFT JOIN unit u ON m.unit_id = u.unit_id
WHERE u.unit_id IS NULL;


--Lease end date should be after start
SELECT 'lease end before start' AS check_name, COUNT(*) AS violations
FROM lease
WHERE lease_end <= lease_start;

--Active leases should end in the future
SELECT 
    lease_status,
    COUNT(*)                                    AS count,
    SUM(CASE WHEN lease_end < CURRENT_DATE THEN 1 ELSE 0 END) AS already_ended
FROM lease
GROUP BY lease_status
ORDER BY lease_status;

--Units per property: should match units_count column
SELECT
    p.property_id,
    p.property_name,
    p.units_count          AS declared_units,
    COUNT(u.unit_id)       AS actual_units,
    p.units_count - COUNT(u.unit_id) AS discrepancy
FROM property p
LEFT JOIN unit u ON p.property_id = u.property_id
GROUP BY p.property_id, p.property_name, p.units_count
ORDER BY p.property_id;

--Late flag consistency: is_late should be TRUE when days_late > 0
SELECT 'late flag mismatch' AS check_name, COUNT(*) AS violations
FROM payment
WHERE (is_late = TRUE AND days_late = 0)
   OR (is_late = FALSE AND days_late > 0);

--tenants with balances more than $500
SELECT
    t.first_name || ' ' || t.last_name AS tenant_name,
    COUNT(i.invoice_id)                AS open_invoices,
    ROUND(SUM(i.balance_due), 2)       AS total_owed
FROM invoice i
JOIN tenant t ON i.tenant_id = t.tenant_id
WHERE i.invoice_status IN ('unpaid', 'partial')
GROUP BY t.tenant_id, tenant_name
HAVING SUM(i.balance_due) > 500
ORDER BY total_owed DESC
LIMIT 10;

--Average days to resolve maintenance by category
SELECT
    category,
    COUNT(*)                              AS total_requests,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
    ROUND(AVG(CASE WHEN status = 'completed' THEN days_to_resolve END), 1) AS avg_days_to_resolve,
    ROUND(AVG(repair_cost), 2)            AS avg_repair_cost
FROM maintenance_request
GROUP BY category
ORDER BY avg_days_to_resolve DESC;

--Monthly rent revenue trend (last 12 months)
SELECT
    strftime('%Y-%m-01', payment_date)   AS month,
    COUNT(*)                              AS payments_received,
    ROUND(SUM(amount_paid), 2)            AS total_collected
FROM payment
WHERE payment_date >= date('now', '-12 months')
  AND payment_type = 'rent'
GROUP BY 1
ORDER BY 1;

--Vacancy summary by property
SELECT
    p.property_name,
    p.units_count                                              AS total_units,
    SUM(CASE WHEN u.is_available THEN 1 ELSE 0 END)           AS vacant,
    ROUND(100.0 * SUM(CASE WHEN u.is_available THEN 1 ELSE 0 END)
          / p.units_count, 1)                                 AS vacancy_rate_pct
FROM property p
JOIN unit u ON p.property_id = u.property_id
GROUP BY p.property_id, p.property_name, p.units_count
ORDER BY vacancy_rate_pct DESC;