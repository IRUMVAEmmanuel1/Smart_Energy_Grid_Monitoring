SELECT hypertable_name, chunk_schema, chunk_name, range_start, range_end,
pg_size_pretty(pg_total_relation_size(format('%I.%I',
chunk_schema, chunk_name)::regclass)) as chunk_size
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
ORDER BY hypertable_name, range_start;
