import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Database connection parameters
DB_PARAMS = {
    'dbname': 'energy_monitoring',
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': '5432'
}

# Connect to the database
@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_PARAMS)

# Load data from database
@st.cache_data(ttl=300)
def load_real_time_data():
    conn = get_connection()
    query = """
    SELECT meter_id, timestamp, power, voltage, current, frequency, energy
    FROM energy_readings
    WHERE timestamp >= NOW() - INTERVAL '1 hour'
    ORDER BY timestamp DESC
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=3600)
def load_daily_data():
    conn = get_connection()
    query = """
    SELECT time_bucket('1 hour', timestamp) AS hour,
           AVG(power) as avg_power
    FROM energy_readings
    WHERE timestamp >= DATE_TRUNC('day', NOW())
    GROUP BY hour
    ORDER BY hour
    """
    today_data = pd.read_sql(query, conn)
    
    query = """
    SELECT time_bucket('1 hour', timestamp) AS hour,
           AVG(power) as avg_power
    FROM energy_readings
    WHERE timestamp >= DATE_TRUNC('day', NOW() - INTERVAL '1 day')
    AND timestamp < DATE_TRUNC('day', NOW())
    GROUP BY hour
    ORDER BY hour
    """
    yesterday_data = pd.read_sql(query, conn)
    
    return today_data, yesterday_data

@st.cache_data(ttl=3600)
def load_weekly_data():
    conn = get_connection()
    query = """
    SELECT time_bucket('1 day', timestamp) AS day,
           AVG(power) as avg_power,
           SUM(energy) as total_energy
    FROM energy_readings
    WHERE timestamp >= NOW() - INTERVAL '7 days'
    GROUP BY day
    ORDER BY day
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=3600)
def load_monthly_data():
    conn = get_connection()
    query = """
    SELECT LEFT(meter_id, 1) as region,
           SUM(energy) as total_energy
    FROM energy_readings
    WHERE timestamp >= DATE_TRUNC('month', NOW())
    GROUP BY region
    ORDER BY region
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=3600)
def load_performance_metrics():
    conn = get_connection()
    raw_query = """
    EXPLAIN ANALYZE
    SELECT meter_id, time_bucket('15 minutes', timestamp) AS bucket,
           AVG(power) as avg_power
    FROM energy_readings
    WHERE timestamp >= NOW() - INTERVAL '1 day'
    AND meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
    GROUP BY meter_id, bucket
    ORDER BY bucket
    """
    cursor = conn.cursor()
    cursor.execute(raw_query)
    raw_results = cursor.fetchall()
    
    agg_query = """
    EXPLAIN ANALYZE
    SELECT meter_id, bucket, avg_power
    FROM energy_readings_15min
    WHERE bucket >= NOW() - INTERVAL '1 day'
    AND meter_id = (SELECT meter_id FROM energy_readings LIMIT 1)
    ORDER BY bucket
    """
    cursor.execute(agg_query)
    agg_results = cursor.fetchall()
    
    # Extract execution times
    raw_time = None
    agg_time = None
    
    for row in raw_results:
        if 'Execution Time' in row[0]:
            raw_time = float(row[0].split('Execution Time:')[1].split('ms')[0].strip())
    
    for row in agg_results:
        if 'Execution Time' in row[0]:
            agg_time = float(row[0].split('Execution Time:')[1].split('ms')[0].strip())
    
    # Get compression metrics
    size_query = """
    SELECT hypertable_name,
           pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size
    FROM timescaledb_information.hypertables
    WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
    """
    compression_data = pd.read_sql(size_query, conn)
    
    return raw_time, agg_time, compression_data

def main():
    st.title("Smart Energy Grid Monitoring Dashboard")
    
    # Sidebar with navigation
    page = st.sidebar.selectbox("Navigate", ["Real-time Monitoring", "Daily Patterns", 
                                            "Weekly Trends", "Monthly Usage", "Performance Metrics"])
    
    if page == "Real-time Monitoring":
        st.header("Real-time Meter Readings (Last Hour)")
        data = load_real_time_data()
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Meters", data['meter_id'].nunique())
        col2.metric("Avg Power (kW)", f"{data['power'].mean():.2f}")
        col3.metric("Avg Voltage (V)", f"{data['voltage'].mean():.1f}")
        col4.metric("Total Energy (kWh)", f"{data['energy'].sum():.2f}")
        
        # Line chart of power over time
        st.subheader("Power Consumption (Last Hour)")
        
        # Group by 5 minute intervals to reduce noise
        data['time_bucket'] = pd.to_datetime(data['timestamp']).dt.floor('5T')
        agg_data = data.groupby('time_bucket').agg({'power': 'mean'}).reset_index()
        
        fig = px.line(agg_data, x='time_bucket', y='power', 
                      labels={'time_bucket': 'Time', 'power': 'Power (kW)'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Sample raw data
        st.subheader("Sample Raw Data")
        st.dataframe(data.head(10))
        
    elif page == "Daily Patterns":
        st.header("Daily Consumption Patterns")
        today_data, yesterday_data = load_daily_data()
        
        # Create comparison chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=today_data['hour'], 
            y=today_data['avg_power'],
            name='Today',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=yesterday_data['hour'], 
            y=yesterday_data['avg_power'],
            name='Yesterday',
            line=dict(color='gray', dash='dash')
        ))
        
        fig.update_layout(
            title='Today vs. Yesterday Power Consumption',
            xaxis_title='Hour of Day',
            yaxis_title='Average Power (kW)',
            legend_title='Day',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    elif page == "Weekly Trends":
        st.header("Weekly Energy Trends")
        weekly_data = load_weekly_data()
        
        # Create two charts: power and energy
        fig1 = px.line(weekly_data, x='day', y='avg_power',
                      labels={'day': 'Date', 'avg_power': 'Average Power (kW)'},
                      title='Average Power Consumption (Past Week)')
        
        fig2 = px.bar(weekly_data, x='day', y='total_energy',
                     labels={'day': 'Date', 'total_energy': 'Total Energy (kWh)'},
                     title='Total Energy Consumption (Past Week)')
        
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        
    elif page == "Monthly Usage":
        st.header("Monthly Energy Usage by Region")
        monthly_data = load_monthly_data()
        
        fig = px.pie(monthly_data, values='total_energy', names='region',
                    title='Energy Distribution by Region (Current Month)')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add a bar chart version as well
        fig2 = px.bar(monthly_data, x='region', y='total_energy',
                     labels={'region': 'Region', 'total_energy': 'Total Energy (kWh)'},
                     title='Energy Consumption by Region (Current Month)')
        
        st.plotly_chart(fig2, use_container_width=True)
        
    elif page == "Performance Metrics":
        st.header("TimescaleDB Performance Metrics")
        
        raw_time, agg_time, compression_data = load_performance_metrics()
        
        # Query performance comparison
        st.subheader("Query Execution Time: Raw Data vs. Aggregated View")
        
        # Create a comparison bar chart
        if raw_time is not None and agg_time is not None:
            perf_data = pd.DataFrame({
                'Data Source': ['Raw Data', 'Continuous Aggregation'],
                'Execution Time (ms)': [raw_time, agg_time]
            })
            
            fig = px.bar(perf_data, x='Data Source', y='Execution Time (ms)',
                        title='Query Performance Comparison')
            
            # Calculate performance improvement
            improvement = ((raw_time - agg_time) / raw_time) * 100
            st.metric("Performance Improvement", f"{improvement:.1f}%")
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Performance data not available")
            
        # Compression stats
        st.subheader("Storage Size by Chunk Strategy")
        if not compression_data.empty:
            # Rename the hypertable names for better display
            compression_data['hypertable_name'] = compression_data['hypertable_name'].replace({
                'energy_readings': '1-day chunks',
                'energy_readings_3h': '3-hour chunks',
                'energy_readings_week': '1-week chunks'
            })
            
            fig = px.bar(compression_data, x='hypertable_name', y='size',
                        labels={'hypertable_name': 'Chunk Strategy', 'size': 'Storage Size'},
                        title='Storage Size by Chunk Strategy (Compressed)')
            
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()