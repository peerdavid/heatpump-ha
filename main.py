from time import sleep
from typing import Any
from htheatpump import HtHeatpump
import paho.mqtt.client as mqtt

#
# Params to read
#
sensor_dict = {
    "home/heatpump/ruecklauf": "Temp. Ruecklauf"
}



#
# ARGS
#
parser = argparse.ArgumentParser(description='Integrate your heatpump into HomeAssistant.')
parser.add_argument('--log_console', required=False, help='Loag all energy values to console.')
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


def sync_hp_to_mqtt(hp: HtHeatpump, mqtt_client: mqtt.Client):
    try:
        hp.open_connection()
        hp.login()
        hp = HtHeatpump(args.serial_port, baudrate=args.baud_rate)
        for mqtt_id, ht_id in sensor_dict:
            print("Sending value {ht_id} to {mqtt_id}.")
            value = hp.get_param(ht_id)
            mqtt_client.publish(mqtt_id, value)

    finally:
        hp.logout()  # try to logout for an ordinary cancellation (if possible)
        hp.close_connection()


#
# M A I N
#
def main():
    hp_client = create_heatpump_client()
    mqtt_client = create_mqtt_client()

    while(True):
        sync_hp_to_mqtt(hp_client, mqtt_client)
        sleep(60)

if __name__ == "__main__":
    main()