-- 1. Compare chunk strategies: execution times for a simple query
-- 1-day chunks (original)
EXPLAIN ANALYZE
SELECT time_bucket('1 hour', timestamp) AS hour,
       AVG(power) as avg_power
FROM energy_readings
WHERE timestamp >= DATE_TRUNC('day', NOW())
GROUP BY hour ORDER BY hour;

-- 3-hour chunks
EXPLAIN ANALYZE
SELECT time_bucket('1 hour', timestamp) AS hour,
       AVG(power) as avg_power
FROM energy_readings_3h
WHERE timestamp >= DATE_TRUNC('day', NOW())
GROUP BY hour ORDER BY hour;

-- 1-week chunks
EXPLAIN ANALYZE
SELECT time_bucket('1 hour', timestamp) AS hour,
       AVG(power) as avg_power
FROM energy_readings_week
WHERE timestamp >= DATE_TRUNC('day', NOW())
GROUP BY hour ORDER BY hour;

-- 2. Analyze chunk distribution
SELECT hypertable_name, count(*) as chunk_count
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
GROUP BY hypertable_name;

-- 3. Measure disk usage before compression
SELECT hypertable_name, 
       pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week');

-- 4. Apply compression only to one table for testing
ALTER TABLE energy_readings SET (timescaledb.compress, 
                               timescaledb.compress_orderby = 'timestamp DESC');

-- Compress chunks immediately
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings') AS chunk;

-- 5. Measure disk usage after compression (only for the compressed table)
SELECT hypertable_name, 
       pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size
FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week');

-- 6. Create a simple continuous aggregation
CREATE MATERIALIZED VIEW energy_readings_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', timestamp) AS bucket,
       AVG(power) as avg_power,
       MAX(power) as max_power
FROM energy_readings
GROUP BY bucket;

-- 7. Compare performance: raw vs. continuous aggregation
-- Raw data query
EXPLAIN ANALYZE
SELECT time_bucket('1 hour', timestamp) AS hour,
       AVG(power) as avg_power
FROM energy_readings
WHERE timestamp >= NOW() - INTERVAL '1 day'
GROUP BY hour ORDER BY hour;

-- Continuous aggregation query
EXPLAIN ANALYZE
SELECT bucket AS hour,
       avg_power
FROM energy_readings_hourly
WHERE bucket >= NOW() - INTERVAL '1 day'
ORDER BY hour;
