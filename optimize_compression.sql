-- Optimize compression policies for 5-minute interval data

-- For the 1-day chunk hypertable
ALTER TABLE energy_readings SET (timescaledb.compress, 
                               timescaledb.compress_orderby = 'timestamp DESC');

-- For 5-minute data, compress after 1 day for optimal balance
SELECT add_compression_policy('energy_readings', INTERVAL '1 day');

-- For the 3-hour chunk hypertable
ALTER TABLE energy_readings_3h SET (timescaledb.compress,
                                  timescaledb.compress_orderby = 'timestamp DESC');
SELECT add_compression_policy('energy_readings_3h', INTERVAL '1 day');

-- For the 1-week chunk hypertable
ALTER TABLE energy_readings_week SET (timescaledb.compress,
                                    timescaledb.compress_orderby = 'timestamp DESC');
SELECT add_compression_policy('energy_readings_week', INTERVAL '1 day');

-- Compress all chunks immediately to see the effect
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings') AS chunk;
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings_3h') AS chunk;
SELECT compress_chunk(chunk) FROM show_chunks('energy_readings_week') AS chunk;

-- Verify compression status
SELECT hypertable_name, 
       chunk_name, 
       is_compressed,
       pg_size_pretty(pg_total_relation_size(format('%I.%I', chunk_schema, chunk_name)::regclass)) as chunk_size
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
ORDER BY hypertable_name, chunk_name;
