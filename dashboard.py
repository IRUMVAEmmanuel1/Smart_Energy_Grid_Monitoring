import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

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
    try:
        return psycopg2.connect(**DB_PARAMS)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# Load data from database
@st.cache_data(ttl=300)
def load_real_time_data():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    # Modify to get data from the last 24 hours instead of just 1 hour
    # This ensures we have some data even if no recent readings
    query = """
    SELECT meter_id, timestamp, power, voltage, current, frequency, energy
    FROM energy_readings
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
    ORDER BY timestamp DESC
    LIMIT 1000
    """
    try:
        df = pd.read_sql(query, conn)
        if len(df) == 0:
            st.warning("No data found in the last 24 hours. Please generate some data first.")
        return df
    except Exception as e:
        st.error(f"Error loading real-time data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_daily_data():
    conn = get_connection()
    if not conn:
        return pd.DataFrame(), pd.DataFrame()
    
    # Get any data from the most recent day with data
    query = """
    SELECT time_bucket('1 hour', timestamp) AS hour,
           AVG(power) as avg_power
    FROM energy_readings
    WHERE timestamp >= (SELECT DATE_TRUNC('day', MAX(timestamp)) FROM energy_readings)
    GROUP BY hour
    ORDER BY hour
    """
    
    try:
        today_data = pd.read_sql(query, conn)
        
        # Get data from the day before that
        query = """
        SELECT time_bucket('1 hour', timestamp) AS hour,
               AVG(power) as avg_power
        FROM energy_readings
        WHERE timestamp >= (SELECT DATE_TRUNC('day', MAX(timestamp)) FROM energy_readings) - INTERVAL '1 day'
          AND timestamp < (SELECT DATE_TRUNC('day', MAX(timestamp)) FROM energy_readings)
        GROUP BY hour
        ORDER BY hour
        """
        yesterday_data = pd.read_sql(query, conn)
        
        return today_data, yesterday_data
    except Exception as e:
        st.error(f"Error loading daily data: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def load_weekly_data():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    query = """
    SELECT time_bucket('1 day', timestamp) AS day,
           AVG(power) as avg_power,
           SUM(energy) as total_energy
    FROM energy_readings
    WHERE timestamp >= (SELECT MAX(timestamp) FROM energy_readings) - INTERVAL '7 days'
    GROUP BY day
    ORDER BY day
    """
    
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error loading weekly data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_monthly_data():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    
    query = """
    SELECT LEFT(meter_id, 1) as region,
           SUM(energy) as total_energy
    FROM energy_readings
    WHERE timestamp >= DATE_TRUNC('month', (SELECT MAX(timestamp) FROM energy_readings))
    GROUP BY region
    ORDER BY region
    """
    
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error loading monthly data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_performance_metrics():
    conn = get_connection()
    if not conn:
        return None, None, pd.DataFrame()
    
    try:
        # Get compression metrics
        size_query = """
        SELECT hypertable_name,
               pg_size_pretty(hypertable_size(format('%I', hypertable_name)::regclass)) AS size
        FROM timescaledb_information.hypertables
        WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
        """
        compression_data = pd.read_sql(size_query, conn)
        
        # Sample meter_id for performance testing
        meter_id_query = "SELECT meter_id FROM energy_readings LIMIT 1"
        cursor = conn.cursor()
        cursor.execute(meter_id_query)
        result = cursor.fetchone()
        
        if not result:
            return None, None, compression_data
            
        sample_meter_id = result[0]
        
        # Test raw query
        raw_query = f"""
        EXPLAIN ANALYZE
        SELECT meter_id, time_bucket('15 minutes', timestamp) AS bucket,
               AVG(power) as avg_power
        FROM energy_readings
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        AND meter_id = '{sample_meter_id}'
        GROUP BY meter_id, bucket
        ORDER BY bucket
        """
        cursor.execute(raw_query)
        raw_results = cursor.fetchall()
        
        # Try continuous aggregation query if the view exists
        try:
            agg_query = f"""
            EXPLAIN ANALYZE
            SELECT meter_id, bucket, avg_power
            FROM energy_readings_15min
            WHERE bucket >= NOW() - INTERVAL '7 days'
            AND meter_id = '{sample_meter_id}'
            ORDER BY bucket
            """
            cursor.execute(agg_query)
            agg_results = cursor.fetchall()
        except Exception:
            agg_results = []
            
        # Extract execution times
        raw_time = None
        agg_time = None
        
        for row in raw_results:
            if 'Execution Time' in row[0]:
                raw_time = float(row[0].split('Execution Time:')[1].split('ms')[0].strip())
        
        for row in agg_results:
            if 'Execution Time' in row[0]:
                agg_time = float(row[0].split('Execution Time:')[1].split('ms')[0].strip())
        
        return raw_time, agg_time, compression_data
    except Exception as e:
        st.error(f"Error loading performance metrics: {e}")
        return None, None, pd.DataFrame()

# Function to analyze 5-minute intervals
def show_five_minute_detail():
    st.header("5-Minute Interval Data Analysis")
    
    conn = get_connection()
    if not conn:
        return
    
    # Get a sample meter_id
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT meter_id FROM energy_readings LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            st.warning("No meter data found in the database.")
            return
            
        sample_meter_id = result[0]
        
        # Get the most recent readings for this meter
        query = f"""
        SELECT timestamp, power, voltage, current, frequency, energy
        FROM energy_readings
        WHERE meter_id = '{sample_meter_id}'
        AND timestamp >= (SELECT MAX(timestamp) FROM energy_readings) - INTERVAL '24 hours'
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        detailed_data = pd.read_sql(query, conn)
        
        if len(detailed_data) == 0:
            st.warning("No recent data available for interval analysis.")
            return
        
        # Reorder data chronologically for display
        detailed_data = detailed_data.sort_values('timestamp')
        
        # Calculate time between readings to verify 5-minute intervals
        if len(detailed_data) > 1:
            detailed_data['time_diff'] = detailed_data['timestamp'].diff()
            detailed_data['interval_minutes'] = detailed_data['time_diff'].dt.total_seconds() / 60
            
            avg_interval = detailed_data['interval_minutes'].mean()
            
            # Create a metrics row
            col1, col2, col3 = st.columns(3)
            col1.metric("Average Interval (minutes)", f"{avg_interval:.2f}")
            col2.metric("Readings Count", len(detailed_data))
            
            # Check if close to 5 minutes
            if 4.5 <= avg_interval <= 5.5:
                col3.metric("Status", "✅ Compliant")
                st.success("The data follows the required 5-minute reporting interval pattern")
            else:
                col3.metric("Status", "⚠️ Non-compliant")
                st.warning(f"The average interval ({avg_interval:.2f} min) differs from the required 5-minute interval")
            
            # Plot the detailed 5-minute interval data
            fig = px.line(detailed_data, x='timestamp', y='power',
                        labels={'timestamp': 'Time', 'power': 'Power (kW)'},
                        title=f'Power Readings for Meter {sample_meter_id}')
            
            # Add markers to highlight each reading
            fig.update_traces(mode='lines+markers')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Plot the interval distribution
            st.subheader("Time Interval Distribution")
            fig2 = px.histogram(detailed_data, x='interval_minutes',
                             title='Distribution of Time Intervals Between Readings',
                             labels={'interval_minutes': 'Interval (minutes)'},
                             nbins=20)
            
            # Add a vertical line at 5 minutes
            fig2.add_vline(x=5, line_dash="dash", line_color="red", 
                        annotation_text="Required 5-min interval", 
                        annotation_position="top right")
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # Show the raw data with intervals
            st.subheader("Raw Data with Intervals")
            # Format the interval for better display
            detailed_data['interval_minutes'] = detailed_data['interval_minutes'].round(2)
            st.dataframe(detailed_data)
            
            # Statistical analysis
            st.subheader("Statistical Analysis of Readings")
            stats_cols = st.columns(2)
            
            with stats_cols[0]:
                st.caption("Power Consumption Statistics")
                st.write(f"Minimum Power: {detailed_data['power'].min():.2f} kW")
                st.write(f"Maximum Power: {detailed_data['power'].max():.2f} kW")
                st.write(f"Average Power: {detailed_data['power'].mean():.2f} kW")
                st.write(f"Standard Deviation: {detailed_data['power'].std():.2f} kW")
                
            with stats_cols[1]:
                st.caption("Interval Statistics")
                st.write(f"Minimum Interval: {detailed_data['interval_minutes'].min():.2f} minutes")
                st.write(f"Maximum Interval: {detailed_data['interval_minutes'].max():.2f} minutes")
                st.write(f"Average Interval: {detailed_data['interval_minutes'].mean():.2f} minutes")
                st.write(f"Standard Deviation: {detailed_data['interval_minutes'].std():.2f} minutes")
                
            # Show a compliance summary
            compliant_intervals = detailed_data[(detailed_data['interval_minutes'] >= 4.5) & 
                                              (detailed_data['interval_minutes'] <= 5.5)]
            compliance_rate = len(compliant_intervals) / len(detailed_data) * 100
            
            st.metric("Interval Compliance Rate", f"{compliance_rate:.1f}%")
            
            if compliance_rate >= 95:
                st.success("The data collection is highly compliant with the 5-minute interval requirement.")
            elif compliance_rate >= 80:
                st.warning("The data collection is mostly compliant, but there are some deviations from the 5-minute interval.")
            else:
                st.error("The data collection shows significant deviations from the required 5-minute interval.")
        else:
            st.warning("Not enough data points to analyze intervals. Need at least 2 readings.")
    except Exception as e:
        st.error(f"Error analyzing interval data: {e}")

def main():
    st.title("Smart Energy Grid Monitoring Dashboard")
    
    # Check database connection first
    conn = get_connection()
    if not conn:
        st.error("Cannot connect to the database. Please make sure TimescaleDB is running.")
        return
        
    # Check if we have any data
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM energy_readings")
        row_count = cursor.fetchone()[0]
        
        if row_count == 0:
            st.warning("No data found in the database. Please run the data generator first.")
            st.info("Run 'python data_generator.py' in your terminal to generate some data.")
            return
    except Exception as e:
        st.error(f"Error checking database: {e}")
        return
    
    # Sidebar with navigation - Now includes the 5-Minute Interval Analysis
    page = st.sidebar.selectbox("Navigate", [
        "Real-time Monitoring", 
        "5-Minute Interval Analysis",  # Added to navigation
        "Daily Patterns", 
        "Weekly Trends", 
        "Monthly Usage", 
        "Performance Metrics"
    ])
    
    if page == "Real-time Monitoring":
        st.header("Real-time Meter Readings")
        data = load_real_time_data()
        
        if len(data) == 0:
            st.warning("No data available. Please generate some data first.")
            return
            
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Meters", data['meter_id'].nunique())
        col2.metric("Avg Power (kW)", f"{data['power'].mean():.2f}")
        col3.metric("Avg Voltage (V)", f"{data['voltage'].mean():.1f}")
        col4.metric("Total Energy (kWh)", f"{data['energy'].sum():.2f}")
        
        # Line chart of power over time
        st.subheader("Power Consumption Over Time")
        
        # Group by 5 minute intervals to highlight the reporting interval
        data['time_bucket'] = pd.to_datetime(data['timestamp']).dt.floor('5T')
        agg_data = data.groupby('time_bucket').agg({'power': 'mean'}).reset_index()
        
        fig = px.line(agg_data, x='time_bucket', y='power', 
                      labels={'time_bucket': 'Time', 'power': 'Power (kW)'})
        
        # Add markers to highlight 5-minute intervals
        fig.update_traces(mode='lines+markers')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Sample raw data
        st.subheader("Sample Raw Data")
        st.dataframe(data.head(10))
        
    elif page == "5-Minute Interval Analysis":
        # Call the function we defined to show 5-minute interval details
        show_five_minute_detail()
        
    elif page == "Daily Patterns":
        st.header("Daily Consumption Patterns")
        today_data, yesterday_data = load_daily_data()
        
        if len(today_data) == 0 and len(yesterday_data) == 0:
            st.warning("No data available for daily patterns. Please generate more data.")
            return
            
        # Create comparison chart
        fig = go.Figure()
        
        if len(today_data) > 0:
            fig.add_trace(go.Scatter(
                x=today_data['hour'], 
                y=today_data['avg_power'],
                name='Today',
                line=dict(color='blue')
            ))
        
        if len(yesterday_data) > 0:
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
        
        if len(weekly_data) == 0:
            st.warning("No data available for weekly trends. Please generate more data.")
            return
            
        # Create two charts: power and energy
        fig1 = px.line(weekly_data, x='day', y='avg_power',
                      labels={'day': 'Date', 'avg_power': 'Average Power (kW)'},
                      title='Average Power Consumption (Past Week)')
        
        fig1.update_traces(mode='lines+markers')
        
        fig2 = px.bar(weekly_data, x='day', y='total_energy',
                     labels={'day': 'Date', 'total_energy': 'Total Energy (kWh)'},
                     title='Total Energy Consumption (Past Week)')
        
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        
    elif page == "Monthly Usage":
        st.header("Monthly Energy Usage by Region")
        monthly_data = load_monthly_data()
        
        if len(monthly_data) == 0:
            st.warning("No data available for monthly usage. Please generate more data.")
            return
            
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
            st.info("Performance comparison data not available. This could be because continuous aggregation views haven't been set up yet, or there's not enough data.")
            
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
                        title='Storage Size by Chunk Strategy')
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Compression data not available.")

if __name__ == "__main__":
    main()