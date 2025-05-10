-- Record disk space before compression
SELECT hypertable_name, 
       pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size_before_compression
FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week');

-- Run baseline queries before compression
-- Query 2 for energy_readings
EXPLAIN ANALYZE
SELECT time_bucket('15 minutes', timestamp) AS period,
       AVG(power) as avg_power
FROM energy_readings
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY period ORDER BY avg_power DESC LIMIT 10;

-- Query 3 for energy_readings
EXPLAIN ANALYZE
SELECT meter_id,
       DATE_TRUNC('month', timestamp) as month,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, month
ORDER BY month, total_energy DESC;

-- Apply compression
-- For the 1-day chunk hypertable
ALTER TABLE energy_readings SET (timescaledb.compress, 
                               timescaledb.compress_orderby = 'timestamp DESC');
SELECT add_compression_policy('energy_readings', INTERVAL '24 hours');

-- For the 3-hour chunk hypertable
ALTER TABLE energy_readings_3h SET (timescaledb.compress,
                                  timescaledb.compress_orderby = 'timestamp DESC');
SELECT add_compression_policy('energy_readings_3h', INTERVAL '24 hours');

-- For the 1-week chunk hypertable
ALTER TABLE energy_readings_week SET (timescaledb.compress,
                                    timescaledb.compress_orderby = 'timestamp DESC');
SELECT add_compression_policy('energy_readings_week', INTERVAL '24 hours');

-- Compress all chunks immediately
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings') AS chunk;
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings_3h') AS chunk;
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings_week') AS chunk;

-- Record disk usage after compression
SELECT hypertable_name, 
       pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size_after_compression
FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week');

-- Run same queries after compression 
-- Query 2 for energy_readings
EXPLAIN ANALYZE
SELECT time_bucket('15 minutes', timestamp) AS period,
       AVG(power) as avg_power
FROM energy_readings
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY period ORDER BY avg_power DESC LIMIT 10;

-- Query 3 for energy_readings
EXPLAIN ANALYZE
SELECT meter_id,
       DATE_TRUNC('month', timestamp) as month,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, month
ORDER BY month, total_energy DESC;
