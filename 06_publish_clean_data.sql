-- Run AFTER: CALL sp_run_validation('AFTER');
USE plant_dq;

-- 1) Records that pass every rule go into the clean, normalized table
TRUNCATE TABLE equipment;
INSERT INTO equipment (record_id, tag_number, type_id, service, design_pressure_barg, design_temp_c,
                       material_id, vendor_id, po_number, po_date, delivery_date, status)
SELECT s.record_id, s.tag_number, t.type_id, s.service, s.design_pressure_barg, s.design_temp_c,
       m.material_id, v.vendor_id, s.po_number, s.po_date, s.delivery_date, s.status
FROM stg_equipment s
JOIN equipment_type t ON t.type_name = s.equipment_type
JOIN material m       ON m.material_name = s.material
JOIN vendor v         ON v.vendor_name = s.vendor
WHERE NOT EXISTS (
    SELECT 1 FROM validation_log l
    WHERE l.run_label = 'AFTER' AND l.record_id = s.record_id
);

-- 2) Records that still fail go to quarantine for manual review
DROP TABLE IF EXISTS equipment_quarantine;
CREATE TABLE equipment_quarantine AS
SELECT s.*, COUNT(l.log_id) AS issue_count,
       GROUP_CONCAT(l.rule_id ORDER BY l.rule_id) AS failed_rules
FROM stg_equipment s
JOIN validation_log l ON l.record_id = s.record_id AND l.run_label = 'AFTER'
GROUP BY s.record_id;

-- 3) Quick numbers for README / resume
SELECT 'BEFORE' AS run_label,
       (SELECT COUNT(*) FROM stg_equipment_raw) AS total_records,
       COUNT(DISTINCT record_id) AS failed_records,
       ROUND(100 * (1 - COUNT(DISTINCT record_id) / (SELECT COUNT(*) FROM stg_equipment_raw)), 1) AS data_quality_pct
FROM validation_log WHERE run_label = 'BEFORE'
UNION ALL
SELECT 'AFTER',
       (SELECT COUNT(*) FROM stg_equipment),
       COUNT(DISTINCT record_id),
       ROUND(100 * (1 - COUNT(DISTINCT record_id) / (SELECT COUNT(*) FROM stg_equipment)), 1)
FROM validation_log WHERE run_label = 'AFTER';

-- Issues per rule, before vs after
SELECT r.rule_id, r.rule_name, r.severity,
       SUM(l.run_label = 'BEFORE') AS issues_before,
       SUM(l.run_label = 'AFTER')  AS issues_after
FROM validation_rules r
LEFT JOIN validation_log l ON l.rule_id = r.rule_id
GROUP BY r.rule_id, r.rule_name, r.severity
ORDER BY r.rule_id;
