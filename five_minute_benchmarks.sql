-- Benchmark queries optimized for 5-minute interval data

-- Query 1: Last hour of data (real-time monitoring)
EXPLAIN ANALYZE
SELECT meter_id, 
       timestamp, 
       power
FROM energy_readings
WHERE meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
  AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Query 2: Aggregation aligned with 15-minute boundaries
EXPLAIN ANALYZE
SELECT bucket, 
       avg_power
FROM energy_readings_15min_optimized
WHERE meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
  AND bucket >= NOW() - INTERVAL '1 day'
ORDER BY bucket DESC;

-- Query 3: Daily pattern with hourly granularity
EXPLAIN ANALYZE
SELECT bucket, 
       avg_power
FROM energy_readings_hourly_optimized
WHERE meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
  AND bucket >= DATE_TRUNC('day', NOW())
ORDER BY bucket;

-- Query 4: Weekly pattern with daily granularity
EXPLAIN ANALYZE
SELECT bucket, 
       avg_power,
       total_energy
FROM energy_readings_daily_optimized
WHERE meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
  AND bucket >= NOW() - INTERVAL '7 days'
ORDER BY bucket;
