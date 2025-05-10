import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime, timedelta
import logging
import math

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# MQTT broker parameters
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "energy/meters/"

# Number of smart meters to simulate
NUM_METERS = 500

# Interval in seconds between readings (5 minutes = 300 seconds)
READING_INTERVAL = 300

class SmartMeter:
    def __init__(self, meter_id):
        """Initialize a smart meter with a given ID"""
        self.meter_id = meter_id
        self.base_power = random.uniform(0.8, 2.5)  # Base power consumption in kW
        self.base_voltage = random.uniform(220, 240)  # Base voltage
        self.power_factor = random.uniform(0.9, 0.98)  # Power factor for calculating current
        
    def generate_reading(self, timestamp):
        """Generate a realistic meter reading for a given timestamp"""
        # Convert timestamp to hour (0-23)
        hour = timestamp.hour
        
        # Apply time-of-day pattern:
        # - Morning peak: 6-9 AM
        # - Evening peak: 6-9 PM
        # - Night low: 11 PM - 5 AM
        time_factor = 1.0
        if 6 <= hour < 9:
            time_factor = 1.5  # Morning peak
        elif 17 <= hour < 22:
            time_factor = 1.8  # Evening peak
        elif 22 <= hour or hour < 5:
            time_factor = 0.6  # Night low
            
        # Add some random variation (±10%)
        random_factor = random.uniform(0.9, 1.1)
        
        # Add weekday/weekend pattern
        is_weekend = timestamp.weekday() >= 5  # 5=Saturday, 6=Sunday
        day_factor = 1.2 if is_weekend else 1.0
        
        # Calculate power with all factors
        power = self.base_power * time_factor * random_factor * day_factor
        
        # Add some sine wave variation for more realism
        minute_of_day = hour * 60 + timestamp.minute
        sine_factor = 0.1 * math.sin(minute_of_day * 2 * math.pi / (60 * 24))
        power *= (1 + sine_factor)
        
        # Calculate voltage with minor fluctuations (±2%)
        voltage = self.base_voltage * random.uniform(0.98, 1.02)
        
        # Calculate current: P = V * I * PF → I = P / (V * PF)
        current = power * 1000 / (voltage * self.power_factor)
        
        # Calculate frequency with minor fluctuations around 50 Hz (±0.1 Hz)
        frequency = 50 + random.uniform(-0.1, 0.1)
        
        # Calculate energy consumed in this interval (kWh)
        # Power (kW) * time (h) = energy (kWh)
        energy = power * (READING_INTERVAL / 3600)  # Convert seconds to hours
        
        return {
            "timestamp": timestamp.isoformat(),
            "power": round(power, 3),
            "voltage": round(voltage, 1),
            "current": round(current, 3),
            "frequency": round(frequency, 2),
            "energy": round(energy, 4)
        }

def generate_meter_ids(count):
    """Generate unique 10-digit meter IDs"""
    meter_ids = []
    for i in range(count):
        # Create a 10-digit number
        meter_id = f"{random.randint(1000000000, 9999999999)}"
        meter_ids.append(meter_id)
    return meter_ids

# Copy all code from data_generator.py but modify the main function:

def main():
    # Create MQTT client
    client = mqtt.Client()
    
    try:
        # Connect to broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Generate meter IDs
        meter_ids = generate_meter_ids(NUM_METERS)
        smart_meters = {meter_id: SmartMeter(meter_id) for meter_id in meter_ids}
        
        # Set time range for 2 weeks of historical data
        end_time = datetime.now()
        start_time = end_time - timedelta(days=14)
        
        logging.info(f"Starting historical data generation from {start_time} to {end_time}")
        logging.info(f"Simulating {NUM_METERS} smart meters")
        
        # Main loop for data generation
        current_time = start_time
        readings_count = 0
        
        while current_time < end_time:
            for meter_id, meter in smart_meters.items():
                # Generate reading
                reading = meter.generate_reading(current_time)
                
                # Publish to MQTT
                topic = f"{MQTT_TOPIC_PREFIX}{meter_id}"
                payload = json.dumps(reading)
                client.publish(topic, payload)
                readings_count += 1
                
            # Log progress every 10,000 readings
            if readings_count % 10000 == 0:
                logging.info(f"Generated {readings_count} readings so far")
                
            # Advance time by the reading interval
            current_time += timedelta(seconds=READING_INTERVAL)
            
            # Sleep a tiny bit to avoid overwhelming the broker
            time.sleep(0.001)
        
        logging.info(f"Historical data generation complete. Generated {readings_count} readings.")
        
    except Exception as e:
        logging.error(f"Error in data generation: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()