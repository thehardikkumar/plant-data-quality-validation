-- MySQL 8.0+
CREATE DATABASE IF NOT EXISTS plant_dq;
USE plant_dq;

DROP TABLE IF EXISTS validation_log;
DROP TABLE IF EXISTS validation_rules;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS equipment_quarantine;
DROP TABLE IF EXISTS stg_equipment_raw;
DROP TABLE IF EXISTS stg_equipment;
DROP TABLE IF EXISTS vendor;
DROP TABLE IF EXISTS equipment_type;
DROP TABLE IF EXISTS material;

-- Lookup (reference) tables: these define what "valid" means
CREATE TABLE vendor (
    vendor_id   INT AUTO_INCREMENT PRIMARY KEY,
    vendor_name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE equipment_type (
    type_id    INT AUTO_INCREMENT PRIMARY KEY,
    type_name  VARCHAR(50) NOT NULL UNIQUE,
    tag_prefix VARCHAR(5)  NOT NULL
);
CREATE TABLE material (
    material_id   INT AUTO_INCREMENT PRIMARY KEY,
    material_name VARCHAR(60) NOT NULL UNIQUE
);

INSERT INTO vendor (vendor_name) VALUES
 ('Apex Flow Systems'), ('Northstar Process Equipment'), ('Meridian Valves Ltd'),
 ('Bluewave Heat Transfer'), ('Titan Fabricators'), ('Orion Instruments'), ('Sterling Pressure Vessels');
INSERT INTO equipment_type (type_name, tag_prefix) VALUES
 ('Pump','P'), ('Vessel','V'), ('Heat Exchanger','E'), ('Valve','XV'), ('Tank','T');
INSERT INTO material (material_name) VALUES
 ('Carbon Steel'), ('Stainless Steel 304'), ('Stainless Steel 316'), ('Duplex Stainless Steel');

-- Staging table: raw data is loaded here as-is (nullable, no constraints)
CREATE TABLE stg_equipment (
    record_id            INT AUTO_INCREMENT PRIMARY KEY,
    tag_number           VARCHAR(30),
    equipment_type       VARCHAR(50),
    service              VARCHAR(100),
    design_pressure_barg DECIMAL(10,2),
    design_temp_c        DECIMAL(10,2),
    material             VARCHAR(60),
    vendor               VARCHAR(100),
    po_number            VARCHAR(30),
    po_date              DATE,
    delivery_date        DATE,
    status               VARCHAR(30)
);

-- Validation framework
CREATE TABLE validation_rules (
    rule_id     VARCHAR(5) PRIMARY KEY,
    rule_name   VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    severity    ENUM('High','Medium','Low') NOT NULL
);
CREATE TABLE validation_log (
    log_id     INT AUTO_INCREMENT PRIMARY KEY,
    run_label  VARCHAR(10) NOT NULL,          -- 'BEFORE' or 'AFTER' cleaning
    record_id  INT NOT NULL,
    tag_number VARCHAR(30),
    rule_id    VARCHAR(5) NOT NULL,
    run_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES validation_rules(rule_id),
    INDEX idx_run_record (run_label, record_id)
);

-- Final clean (normalized) table: only records that pass every rule
CREATE TABLE equipment (
    record_id            INT PRIMARY KEY,
    tag_number           VARCHAR(30) NOT NULL UNIQUE,
    type_id              INT NOT NULL,
    service              VARCHAR(100),
    design_pressure_barg DECIMAL(10,2) NOT NULL,
    design_temp_c        DECIMAL(10,2),
    material_id          INT NOT NULL,
    vendor_id            INT NOT NULL,
    po_number            VARCHAR(30),
    po_date              DATE,
    delivery_date        DATE,
    status               VARCHAR(30),
    FOREIGN KEY (type_id)     REFERENCES equipment_type(type_id),
    FOREIGN KEY (material_id) REFERENCES material(material_id),
    FOREIGN KEY (vendor_id)   REFERENCES vendor(vendor_id)
);
