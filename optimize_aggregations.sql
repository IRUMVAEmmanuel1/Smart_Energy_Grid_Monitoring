-- Create optimized continuous aggregations for 5-minute data

-- Check if views already exist and drop them if needed
DROP MATERIALIZED VIEW IF EXISTS energy_readings_15min_optimized;
DROP MATERIALIZED VIEW IF EXISTS energy_readings_hourly_optimized;
DROP MATERIALIZED VIEW IF EXISTS energy_readings_daily_optimized;

-- 15-minute aggregation (combines 3 readings at 5-minute intervals)
CREATE MATERIALIZED VIEW energy_readings_15min_optimized
WITH (timescaledb.continuous) AS
SELECT meter_id,
       time_bucket('15 minutes', timestamp) AS bucket,
       COUNT(*) as num_readings,  -- Track number of readings to verify we're getting 3 per bucket
       AVG(power) as avg_power,
       MAX(power) as max_power,
       MIN(power) as min_power,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, bucket;

-- Hourly aggregation (combines 12 readings at 5-minute intervals)
CREATE MATERIALIZED VIEW energy_readings_hourly_optimized
WITH (timescaledb.continuous) AS
SELECT meter_id,
       time_bucket('1 hour', timestamp) AS bucket,
       COUNT(*) as num_readings,  -- Track number of readings to verify we're getting 12 per bucket
       AVG(power) as avg_power,
       MAX(power) as max_power,
       MIN(power) as min_power,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, bucket;

-- Daily aggregation (combines 288 readings at 5-minute intervals)
CREATE MATERIALIZED VIEW energy_readings_daily_optimized
WITH (timescaledb.continuous) AS
SELECT meter_id,
       time_bucket('1 day', timestamp) AS bucket,
       COUNT(*) as num_readings,  -- Track number of readings to verify we're getting 288 per bucket
       AVG(power) as avg_power,
       MAX(power) as max_power,
       MIN(power) as min_power,
       SUM(energy) as total_energy
FROM energy_readings
GROUP BY meter_id, bucket;

-- Add refresh policies aligned with reporting intervals
SELECT add_continuous_aggregate_policy('energy_readings_15min_optimized',
                                     start_offset => INTERVAL '3 days',
                                     end_offset => INTERVAL '5 minutes',  -- Align with data reporting interval
                                     schedule_interval => INTERVAL '15 minutes');

SELECT add_continuous_aggregate_policy('energy_readings_hourly_optimized',
                                     start_offset => INTERVAL '7 days',
                                     end_offset => INTERVAL '5 minutes',  -- Align with data reporting interval
                                     schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('energy_readings_daily_optimized',
                                     start_offset => INTERVAL '30 days',
                                     end_offset => INTERVAL '5 minutes',  -- Align with data reporting interval
                                     schedule_interval => INTERVAL '1 day');
