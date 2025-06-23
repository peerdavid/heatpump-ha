import os
import argparse
from time import sleep
from htheatpump import HtHeatpump
import paho.mqtt.client as mqtt
from pathlib import Path

current_path = Path(__file__).parent.absolute()


#
# ARGS
#
parser = argparse.ArgumentParser(description='Integrate your heatpump into HomeAssistant.')
parser.add_argument('--serial_port', default="/dev/ttyUSB0", help='Port of rapspberry connected to your heatpump.')
parser.add_argument('--baud_rate', default=19200, help='Baudrate of serial port.')
parser.add_argument('--mqtt_server', default="localhost", help='MQTT server host.')
parser.add_argument('--mqtt_port', default=1883, help='MQTT server port.')
parser.add_argument('--mqtt_user', default="user", help='MQTT user.')
parser.add_argument('--mqtt_passwd', default="passwd", help='MQTT password.')
args = parser.parse_args()

pv_modus = -1
pv_ww = -1


#
# Helper
#
def create_heatpump_client() -> HtHeatpump:
    return HtHeatpump(args.serial_port, baudrate=args.baud_rate)


def create_mqtt_client() -> mqtt.Client:
    mqtt_client = mqtt.Client("heatpumpreader")
    mqtt_client.username_pw_set(args.mqtt_user, args.mqtt_passwd)
    mqtt_client.connect(args.mqtt_server, port=args.mqtt_port)
    mqtt_client.loop_start()
    return mqtt_client


def sync_hp_to_mqtt(hp: HtHeatpump, mqtt_client: mqtt.Client, sensors):    
    for ht_id, mqtt_id in sensors:
        try:
            value = hp.get_param(ht_id)
            print(f"{mqtt_id} = {value}.")
        except:
            print(f"Could not read {ht_id}")

        mqtt_id = f"home/heatpump/{mqtt_id}"
        mqtt_client.publish(mqtt_id, value)


def get_all_sensors(path):
    sensors = []
    file_path = os.path.join(path, "sensors.csv")
    with open(file_path, "r") as fp:
        for row in fp:
            ht_id = row.split(",")[0]
            sensor = row.split(",")[0].lower().replace(" (", "(").replace("(", "").replace(")", "").replace(" ", "_").replace(".", "")
            mp_sp = row.split(",")[1].lower()
            mqtt_id = f"{mp_sp}_{sensor}"

            sensors.append((ht_id, mqtt_id))

    return sensors


def subscribe_ww(mqtt_client: mqtt.Client):
    # Set the callback for incoming messages
    mqtt_id = "home/heatpump/pv/ww"
    mqtt_client.subscribe(mqtt_id)

    def on_message(client, userdata, message):
        global pv_ww
        try:
            # Decode the message payload
            value = message.payload.decode('utf-8')
            pv_ww = int(value)
            print(f"Received message on {message.topic}: {pv_ww}")
        except Exception as e:
            print(f"Error processing message: {e}")

    mqtt_client.on_message = on_message

def subscribe_pv_modus(mqtt_client: mqtt.Client):
    # Set the callback for incoming messages
    mqtt_id = "home/heatpump/pv/modus"
    mqtt_client.subscribe(mqtt_id)

    def on_message(client, userdata, message):
        global pv_modus
        try:
            # Decode the message payload
            value = message.payload.decode('utf-8')
            pv_modus = int(value)
            print(f"Received message on {message.topic}: {pv_modus}")
        except Exception as e:
            print(f"Error processing message: {e}")

    mqtt_client.on_message = on_message

def set_pv(hp_client: HtHeatpump):
    global pv_modus
    global pv_ww

    print(pv_modus)
    print(pv_ww)

    # Read value with mqtt
    if pv_modus < 0:
        print("NO PV Modus received yet.")
        return
    
    if pv_ww < 0:
        print("NO PV WW received yet.")
        return
    
    print("Set PV modus to", pv_modus)
    print("Set PV WW to", pv_ww)
    # print("Set 2. Stufe WW Betriebs to", value)
    # hp_client.set_param("2. Stufe WW Betriebs", value, True)

    


#
# M A I N
#
def main():
    print("Starting heatpump HA bridge...")
    sensors = get_all_sensors(current_path)
    hp_client = create_heatpump_client()
    mqtt_client = create_mqtt_client()
    subscribe_pv_modus(mqtt_client)
    subscribe_ww(mqtt_client)

    while(True):
        try:
            hp_client.open_connection()
            hp_client.login()

            # sync_hp_to_mqtt(hp_client, mqtt_client, sensors)
            set_pv(hp_client)
        except Exception as e:
            print(f"Failed to sync heatpump with MQTT: {e}")
        finally:
            hp_client.logout()  # try to logout for an ordinary cancellation (if possible)
            hp_client.close_connection()
            sleep(10)

if __name__ == "__main__":
    main()