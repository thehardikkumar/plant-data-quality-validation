-- MySQL 8.0+
USE plant_dq;

SET SQL_SAFE_UPDATES = 0;  -- Workbench safe mode blocks DELETE without a key in WHERE
DELETE FROM validation_log WHERE log_id > 0;
DELETE FROM validation_rules WHERE rule_id <> '';

INSERT INTO validation_rules (rule_id, rule_name, description, severity) VALUES
('R01','Duplicate tag number','Same tag number appears more than once (extra occurrences flagged)','High'),
('R02','Vendor missing','Vendor is NULL or blank','High'),
('R03','Material missing','Material is NULL or blank','High'),
('R04','Design pressure missing','Design pressure is NULL','High'),
('R05','Design pressure out of range','Design pressure <= 0 or > 420 barg','High'),
('R06','Design temperature out of range','Design temperature < -196 C or > 650 C','Medium'),
('R07','Tag format invalid','Tag must match PREFIX-NNN[A], e.g. P-101 or XV-2045A (uppercase)','Medium'),
('R08','Delivery before PO date','Delivery date earlier than PO date','Medium'),
('R09','Equipment type not allowed','Equipment type not in equipment_type lookup (exact spelling)','Medium'),
('R10','Material not standard','Material not in material lookup (exact spelling)','Low'),
('R11','Vendor not in lookup','Vendor not in vendor lookup (exact spelling)','Low');

DROP PROCEDURE IF EXISTS sp_run_validation;
DELIMITER $$
CREATE PROCEDURE sp_run_validation(IN p_run VARCHAR(10))
BEGIN
    DELETE FROM validation_log WHERE run_label = p_run AND log_id > 0;

    -- R01: duplicate tag numbers (window function; first occurrence is kept, extras flagged)
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R01'
    FROM (
        SELECT record_id, tag_number,
               ROW_NUMBER() OVER (PARTITION BY tag_number ORDER BY record_id) AS rn
        FROM stg_equipment
        WHERE tag_number IS NOT NULL
    ) d
    WHERE rn > 1;

    -- R02: vendor missing
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R02'
    FROM stg_equipment WHERE vendor IS NULL OR TRIM(vendor) = '';

    -- R03: material missing
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R03'
    FROM stg_equipment WHERE material IS NULL OR TRIM(material) = '';

    -- R04: design pressure missing
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R04'
    FROM stg_equipment WHERE design_pressure_barg IS NULL;

    -- R05: design pressure out of range
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R05'
    FROM stg_equipment
    WHERE design_pressure_barg IS NOT NULL
      AND (design_pressure_barg <= 0 OR design_pressure_barg > 420);

    -- R06: design temperature out of range
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R06'
    FROM stg_equipment
    WHERE design_temp_c IS NOT NULL
      AND (design_temp_c < -196 OR design_temp_c > 650);

    -- R07: tag format (case-sensitive regex)
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R07'
    FROM stg_equipment
    WHERE tag_number IS NULL
       OR NOT REGEXP_LIKE(tag_number, '^[A-Z]{1,2}-[0-9]{3,4}[A-Z]?$', 'c');

    -- R08: delivery date before PO date
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, record_id, tag_number, 'R08'
    FROM stg_equipment
    WHERE po_date IS NOT NULL AND delivery_date IS NOT NULL AND delivery_date < po_date;

    -- R09: equipment type not in lookup (exact, case-sensitive match)
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, s.record_id, s.tag_number, 'R09'
    FROM stg_equipment s
    WHERE NOT EXISTS (
        SELECT 1 FROM equipment_type t
        WHERE t.type_name COLLATE utf8mb4_bin = s.equipment_type COLLATE utf8mb4_bin
    );

    -- R10: material not in lookup (only when material is present)
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, s.record_id, s.tag_number, 'R10'
    FROM stg_equipment s
    WHERE s.material IS NOT NULL AND TRIM(s.material) <> ''
      AND NOT EXISTS (
        SELECT 1 FROM material m
        WHERE m.material_name COLLATE utf8mb4_bin = s.material COLLATE utf8mb4_bin
    );

    -- R11: vendor not in lookup (only when vendor is present)
    INSERT INTO validation_log (run_label, record_id, tag_number, rule_id)
    SELECT p_run, s.record_id, s.tag_number, 'R11'
    FROM stg_equipment s
    WHERE s.vendor IS NOT NULL AND TRIM(s.vendor) <> ''
      AND NOT EXISTS (
        SELECT 1 FROM vendor v
        WHERE v.vendor_name COLLATE utf8mb4_bin = s.vendor COLLATE utf8mb4_bin
    );

    -- summary returned to the caller
    SELECT p_run AS run_label,
           (SELECT COUNT(*) FROM stg_equipment) AS total_records,
           COUNT(DISTINCT record_id) AS failed_records,
           COUNT(*) AS total_issues
    FROM validation_log WHERE run_label = p_run;
END$$
DELIMITER ;
