# Performance Results

## Baseline Queries with 1-day chunks

| Query | Description | Execution Time |
|-------|-------------|---------------|
| 1 | Average power consumption per hour today | ... ms |
| 2 | Find peak consumption periods in the past week | ... ms |
| 3 | Monthly consumption per meter | ... ms |
| 4 | Full dataset scan | ... ms |


## Chunk Interval Comparison Results

| Query | Description | 3-hour chunks | 1-day chunks | 1-week chunks |
|-------|-------------|--------------|--------------|---------------|
| 1 | Average power consumption per hour today | ... ms | 1.957 ms | ... ms |
| 2 | Find peak consumption periods in the past week | ... ms | 2.745 ms | ... ms |
| 3 | Monthly consumption per meter | ... ms | 10.545 ms | ... ms |
| 4 | Full dataset scan | ... ms | 2.390 ms | ... ms |