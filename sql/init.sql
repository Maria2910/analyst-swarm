-- Инициализация БД analytics для Analyst Swarm

-- Таблица продаж по регионам и кварталам
CREATE TABLE IF NOT EXISTS sales (
    id              SERIAL PRIMARY KEY,
    region          VARCHAR(50) NOT NULL,
    quarter         VARCHAR(10) NOT NULL,
    sales           NUMERIC(12, 2) NOT NULL,
    marketing_spend NUMERIC(12, 2),
    customers       INTEGER
);

INSERT INTO sales (region, quarter, sales, marketing_spend, customers) VALUES
    ('North', 'Q1', 150000, 20000, 1200),
    ('North', 'Q2', 142000, 22000, 1150),
    ('North', 'Q3', 128000, 21000, 980),
    ('North', 'Q4', 127500, 23000, 950),
    ('South', 'Q1', 180000, 25000, 1500),
    ('South', 'Q2', 175000, 26000, 1480),
    ('South', 'Q3', 162000, 24000, 1320),
    ('South', 'Q4', 153000, 25000, 1240),
    ('West',  'Q1', 220000, 30000, 1800),
    ('West',  'Q2', 210000, 32000, 1750),
    ('West',  'Q3', 195000, 31000, 1600),
    ('West',  'Q4', 187000, 33000, 1520),
    ('East',  'Q1', 95000, 15000, 800),
    ('East',  'Q2', 92000, 16000, 780),
    ('East',  'Q3', 85000, 15000, 700),
    ('East',  'Q4', 80750, 15500, 650);

-- Таблица клиентов
CREATE TABLE IF NOT EXISTS customers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    region      VARCHAR(50) NOT NULL,
    joined_at   DATE NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE
);

INSERT INTO customers (name, region, joined_at, is_active) VALUES
    ('ООО Альфа',    'North', '2023-01-15', TRUE),
    ('ИП Иванов',    'North', '2023-06-20', TRUE),
    ('ООО Бета',     'South', '2022-11-05', FALSE),
    ('ООО Гамма',    'South', '2023-03-12', TRUE),
    ('ИП Петров',    'West',  '2022-08-01', TRUE),
    ('ООО Дельта',   'West',  '2023-05-18', TRUE),
    ('ООО Эпсилон',  'East',  '2023-02-28', FALSE),
    ('ИП Сидоров',   'East',  '2023-09-10', TRUE),
    ('ООО Дзета',    'North', '2023-04-22', TRUE),
    ('ООО Эта',      'West',  '2023-07-14', TRUE);

-- Индексы для быстрых запросов
CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region);
CREATE INDEX IF NOT EXISTS idx_sales_quarter ON sales(quarter);
CREATE INDEX IF NOT EXISTS idx_customers_region ON customers(region);