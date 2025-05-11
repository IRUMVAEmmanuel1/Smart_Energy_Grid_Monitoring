-- Analyze current chunk distribution
SELECT hypertable_name, 
       count(*) as chunk_count,
       min(range_start) as oldest_data,
       max(range_end) as newest_data
FROM timescaledb_information.chunks
GROUP BY hypertable_name;

-- Calculate optimal chunk sizes for 5-minute data
-- For a system with 500 meters reporting every 5 minutes:
-- 500 meters * (60/5) readings per hour = 6,000 readings per hour
-- 6,000 * 24 = 144,000 readings per day
-- We can estimate chunk size based on this data volume

-- Display the approximate number of readings in each chunk
SELECT 
    hypertable_name,
    chunk_name,
    range_start,
    range_end,
    (EXTRACT(EPOCH FROM (range_end - range_start)) / 300) * 500 AS estimated_row_count,
    pg_size_pretty(pg_total_relation_size(format('%I.%I', chunk_schema, chunk_name)::regclass)) as chunk_size,
    pg_total_relation_size(format('%I.%I', chunk_schema, chunk_name)::regclass) / 
        NULLIF((EXTRACT(EPOCH FROM (range_end - range_start)) / 300) * 500, 0) AS bytes_per_reading
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
ORDER BY hypertable_name, range_start;
