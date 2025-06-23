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


def set_electro_heat(hp_client: HtHeatpump, mqtt_client: mqtt.Client):
    # Read value with mqtt
    mqtt_id = "home/heatpump/2_stufe_ww_betriebs"
    try:
        value = mqtt_client.subscribe(mqtt_id)
        print(f"Current value of {mqtt_id} is {value}.")
    except Exception as e:
        print(f"Could not read {mqtt_id}: {e}")

    # print("Set 2. Stufe WW Betriebs to", value)
    # hp_client.set_param("2. Stufe WW Betriebs", value, True)

    


#
# M A I N
#
def main():
    sensors = get_all_sensors(current_path)
    hp_client = create_heatpump_client()
    mqtt_client = create_mqtt_client()

    while(True):
        try:
            hp_client.open_connection()
            hp_client.login()

            # sync_hp_to_mqtt(hp_client, mqtt_client, sensors)
            set_electro_heat(hp_client, mqtt_client)
        except Exception as e:
            print(f"Failed to sync heatpump with MQTT: {e}")
        finally:
            hp_client.logout()  # try to logout for an ordinary cancellation (if possible)
            hp_client.close_connection()
            sleep(10)

if __name__ == "__main__":
    main()