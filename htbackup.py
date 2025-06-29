import argparse
import csv
import json
import logging
import re
import sys
import textwrap

from htheatpump import HtHeatpump
from htheatpump.utils import Timer

_LOGGER = logging.getLogger(__name__)


# Main program
def main():
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """\
            Command line tool to create a backup of the Heliotherm heat pump data points.

            Example:

              $ python3 htbackup.py --baudrate 9600 --csv backup.csv
              'SP,NR=0' [Language]: VAL='0', MIN='0', MAX='4'
              'SP,NR=1' [TBF_BIT]: VAL='0', MIN='0', MAX='1'
              'SP,NR=2' [Rueckruferlaubnis]: VAL='1', MIN='0', MAX='1'
              ...
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            DISCLAIMER
            ----------

              Please note that any incorrect or careless usage of this program as well as
              errors in the implementation can damage your heat pump!

              Therefore, the author does not provide any guarantee or warranty concerning
              to correctness, functionality or performance and does not accept any liability
              for damage caused by this program or mentioned information.

              Thus, use it on your own risk!
            """
        )
        + "\r\n",
    )

    parser.add_argument(
        "-d",
        "--device",
        default="/dev/ttyUSB0",
        type=str,
        help="the serial device on which the heat pump is connected, default: %(default)s",
    )

    parser.add_argument(
        "-b",
        "--baudrate",
        default=115200,
        type=int,
        # the supported baudrates of the Heliotherm heat pump (HP08S10W-WEB):
        choices=[9600, 19200, 38400, 57600, 115200],
        help="baudrate of the serial connection (same as configured on the heat pump), default: %(default)s",
    )

    parser.add_argument(
        "-j", "--json", type=str, help="write the result to the specified JSON file"
    )

    parser.add_argument(
        "-c", "--csv", type=str, help="write the result to the specified CSV file"
    )

    parser.add_argument(
        "-t", "--time", action="store_true", help="measure the execution time"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="increase output verbosity by activating logging",
    )

    parser.add_argument(
        "--without-values",
        action="store_true",
        help="store heat pump data points without their current value (keep it blank)",
    )

    parser.add_argument(
        "--max-retries",
        default=2,
        type=int,
        choices=range(11),
        help="maximum number of retries for a data point request (0..10), default: %(default)s",
    )

    args = parser.parse_args()

    # activate logging with level DEBUG in verbose mode
    log_format = "%(asctime)s %(levelname)s [%(name)s|%(funcName)s]: %(message)s"
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    else:
        logging.basicConfig(level=logging.WARNING, format=log_format)

    hp = HtHeatpump(args.device, baudrate=args.baudrate)
    try:
        hp.open_connection()
        hp.login()

        rid = hp.get_serial_number()
        print("connected successfully to heat pump with serial number {:d}".format(rid))
        ver = hp.get_version()
        print("software version = {} ({:d})".format(ver[0], ver[1]))

        result = {}
        with Timer() as timer:
            for dp_type in ("SP", "MP"):  # for all known data point types
                result.update({dp_type: {}})
                i = 0  # start at zero for each data point type
                while True:
                    success = False
                    retry = 0
                    while not success and retry <= args.max_retries:
                        data_point = "{},NR={:d}".format(dp_type, i)
                        # send request for data point to the heat pump
                        hp.send_request(data_point)
                        # ... and wait for the response
                        try:
                            resp = hp.read_response()
                            # search for pattern "NAME=...", "VAL=...", "MAX=..." and "MIN=..." inside the answer
                            m = re.match(
                                r"^{},.*NAME=([^,]+).*VAL=([^,]+).*MAX=([^,]+).*MIN=([^,]+).*$".format(
                                    data_point
                                ),
                                resp,
                            )
                            if not m:
                                raise IOError(
                                    "invalid response for query of data point {!r} [{}]".format(
                                        data_point, resp
                                    )
                                )
                            # extract name, value, min and max
                            name, value, min_val, max_val = (
                                g.strip() for g in m.group(1, 2, 4, 3)
                            )
                            if args.without_values:
                                value = ""  # keep it blank (if desired)
                            print(
                                "{!r} [{}]: VAL={!r}, MIN={!r}, MAX={!r}".format(
                                    data_point, name, value, min_val, max_val
                                )
                            )
                            # store the determined data in the result dict
                            result[dp_type].update(
                                {
                                    i: {
                                        "name": name,
                                        "value": value,
                                        "min": min_val,
                                        "max": max_val,
                                    }
                                }
                            )
                            success = True
                        except Exception as e:
                            retry += 1
                            _LOGGER.warning(
                                "try #%d/%d for query of data point '%s' failed: %s",
                                retry,
                                args.max_retries + 1,
                                data_point,
                                e,
                            )
                            # try a reconnect, maybe this will help
                            hp.reconnect()  # perform a reconnect
                            try:
                                hp.login(max_retries=0)  # ... and a new login
                            except Exception:
                                pass  # ignore a potential problem
                    if not success:
                        _LOGGER.error(
                            "query of data point '%s' failed after %s try/tries",
                            data_point,
                            retry,
                        )
                        break
                    else:
                        i += 1
        exec_time = timer.elapsed

        if args.json:  # write result to JSON file
            with open(args.json, "w") as jsonfile:
                json.dump(result, jsonfile, indent=4, sort_keys=True)

        if args.csv:  # write result to CSV file
            with open(args.csv, "w") as csvfile:
                fieldnames = ["type", "number", "name", "value", "min", "max"]
                writer = csv.DictWriter(csvfile, delimiter=",", fieldnames=fieldnames)
                writer.writeheader()
                for dp_type, content in sorted(result.items(), reverse=True):
                    for i, data in content.items():
                        row_data = {"type": dp_type, "number": i}
                        row_data.update(data)
                        writer.writerow({n: row_data[n] for n in fieldnames})

        # print execution time only if desired
        if args.time:
            print("execution time: {:.2f} sec".format(exec_time))

    except Exception as ex:
        _LOGGER.exception(ex)
        sys.exit(1)
    finally:
        hp.logout()  # try to logout for an ordinary cancellation (if possible)
        hp.close_connection()

    sys.exit(0)


if __name__ == "__main__":
    main()
