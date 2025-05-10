import paho.mqtt.client as mqtt
import psycopg2
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection parameters
DB_PARAMS = {
    'dbname': 'energy_monitoring',
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': '5432'
}

# MQTT broker parameters
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "energy/meters/#"

def connect_to_db():
    """Connect to the PostgreSQL database and return connection"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None

def on_connect(client, userdata, flags, rc):
    """Callback when client connects to the broker"""
    if rc == 0:
        logging.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
    else:
        logging.error(f"Failed to connect to MQTT broker with code: {rc}")

def on_message(client, userdata, msg):
    """Callback when a message is received"""
    try:
        # Decode the message
        payload = json.loads(msg.payload.decode('utf-8'))
        
        # Extract meter_id from the topic
        # Topic format: energy/meters/{meter_id}
        meter_id = msg.topic.split('/')[-1]
        
        # Insert data into database
        conn = connect_to_db()
        if conn:
            cursor = conn.cursor()
            
            # Insert query
            insert_query = """
            INSERT INTO energy_readings 
            (meter_id, timestamp, power, voltage, current, frequency, energy)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Data to insert
            data = (
                meter_id,
                payload.get('timestamp', datetime.now().isoformat()),
                payload.get('power', 0.0),
                payload.get('voltage', 0.0),
                payload.get('current', 0.0),
                payload.get('frequency', 0.0),
                payload.get('energy', 0.0)
            )
            
            cursor.execute(insert_query, data)
            conn.commit()
            cursor.close()
            conn.close()
            
            logging.info(f"Data from meter {meter_id} stored successfully")
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def main():
    # Connect to MQTT broker
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        
        # Start the loop
        client.loop_forever()
    except Exception as e:
        logging.error(f"MQTT connection error: {e}")

if __name__ == "__main__":
    main()