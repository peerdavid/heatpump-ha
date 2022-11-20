from htheatpump import HtHeatpump

hp = HtHeatpump("/dev/ttyUSB0", baudrate=19200)
try:
    hp.open_connection()
    hp.login()
    # query for the outdoor temperature
    temp = hp.get_param("Temp. Aussen")
    print(temp)
    temp = hp.get_param("Temp. Vorlauf")
    print(temp)
    temp = hp.get_param("Temp. Ruecklauf")
    print(temp)
    temp = hp.get_param("Temp. Brauchwasser")
    print(temp)
    temp = hp.get_param("Hauptschalter")
    print(temp)
    temp = hp.get_param("WW Normaltemp.")
    print(temp)
    # ...
finally:
    hp.logout()  # try to logout for an ordinary cancellation (if possible)
    hp.close_connection()
