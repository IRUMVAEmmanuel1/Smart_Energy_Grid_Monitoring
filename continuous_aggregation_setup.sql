-- Create 15-minute aggregations
CREATE MATERIALIZED VIEW energy_readings_15min
WITH (timescaledb.continuous) AS
SELECT meter_id,
       time_bucket('15 minutes', timestamp) AS bucket,
       AVG(power) as avg_power,
       MAX(power) as max_power,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, bucket;

-- Create hourly aggregations
CREATE MATERIALIZED VIEW energy_readings_hourly
WITH (timescaledb.continuous) AS
SELECT meter_id,
       time_bucket('1 hour', timestamp) AS bucket,
       AVG(power) as avg_power,
       MAX(power) as max_power,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, bucket;

-- Create daily aggregations
CREATE MATERIALIZED VIEW energy_readings_daily
WITH (timescaledb.continuous) AS
SELECT meter_id,
       time_bucket('1 day', timestamp) AS bucket,
       AVG(power) as avg_power,
       MAX(power) as max_power,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, bucket;

-- Add refresh policies
SELECT add_continuous_aggregate_policy('energy_readings_15min',
                                     start_offset => INTERVAL '3 days',
                                     end_offset => INTERVAL '1 hour',
                                     schedule_interval => INTERVAL '15 minutes');

SELECT add_continuous_aggregate_policy('energy_readings_hourly',
                                     start_offset => INTERVAL '7 days',
                                     end_offset => INTERVAL '1 hour',
                                     schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('energy_readings_daily',
                                     start_offset => INTERVAL '30 days',
                                     end_offset => INTERVAL '1 hour',
                                     schedule_interval => INTERVAL '1 day');

-- Compare performance of raw data vs. continuous aggregations
-- First, query using raw data
EXPLAIN ANALYZE
SELECT meter_id, time_bucket('15 minutes', timestamp) AS bucket,
       AVG(power) as avg_power
FROM energy_readings
WHERE timestamp >= NOW() - INTERVAL '1 day'
AND meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
GROUP BY meter_id, bucket
ORDER BY bucket;

-- Then, query using continuous aggregation view
EXPLAIN ANALYZE
SELECT meter_id, bucket, avg_power
FROM energy_readings_15min
WHERE bucket >= NOW() - INTERVAL '1 day'
AND meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
ORDER BY bucket;
