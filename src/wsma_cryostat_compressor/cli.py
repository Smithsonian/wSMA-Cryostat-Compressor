"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mwsma_cryostat_selector` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``wsma_cryostat_selector.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``wsma_cryostat_selector.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import os
import argparse

import wsma_cryostat_compressor

default_compressor = os.environ.get("WSMACOMPRESSOR", None)
default_inverter = os.environ.get("WSMAINVERTER", None)

parser = argparse.ArgumentParser(description="Communicate with a Cryomech compressor's "
                                             "digital control panel.")

parser.add_argument("-v", "--verbosity", action="store_true",
                    help="Display detailed output from compressor")
parser.add_argument("-a", "--address", default=default_compressor,
                    help="The IP address of the compressor, defaults to $WSMACOMPRESSOR")
parser.add_argument("-i", "--inverter_address", default=default_inverter,
                    help="The IP address of the compressor's inverter, defaults to $WSMAINVERTER")
parser.add_argument("--debug", action="store_true")

group = parser.add_mutually_exclusive_group()
group.add_argument("--on", action="store_true", help="Turn the compressor on")
group.add_argument("--off", action="store_true", help="Turn the compressor off")

parser.add_argument("-f", "--freq", default=None, help="Set the inverter frequency")


def main(args=None):
    args = parser.parse_args(args=args)

    if args.debug:
        print(args)
    # Create the compressor object for communication with the controller
    # If address is 'test', create a dummy compressor for testing purposes.
    if args.address == "test":
        print(args)
        return None
        # comp = wsma_cryostat_compressor.DummyCompressor()
    elif args.address is None:
        print("Compressor address not given")
        print()
        parser.print_help()
    else:
        if args.inverter_address:
            if args.inverter_address.startswith("/dev/tty") or args.inverter_address.startswith("COM"):
                inverter = 'rs485'
            else:
                inverter = 'rs485_ethernet'
        else:
            # v3 software compressors with internal inverter will be detected automatically
            inverter = None
        comp = wsma_cryostat_compressor.Compressor(ip_address=args.address, inverter=inverter, inverter_address=args.inverter_address, debug=args.debug)

        if args.verbosity:
            comp.verbose = True

        if args.off:
            if comp.state_code == 0:
                print("{} compressor {} at {} is already off".format(comp.model, comp.serial, comp.ip_address))
            elif comp.state_code == 5:
                print("{} compressor {} at {} is already stopping".format(comp.model, comp.serial, comp.ip_address))
            elif comp.state_code == 2:
                print("{} compressor {} at {} is still starting, please try again later".format(comp.model,
                                                                                                comp.serial,
                                                                                                comp.ip_address))
            else:
                try:
                    print("Turning {} compressor {} at {} off".format(comp.model, comp.serial, comp.ip_address))
                    comp.off()
                except RuntimeError:
                    print("Could not turn compressor off")
                    print("")
                    print("State: {}".format(comp.state))
                    print("Errors:")
                    print(" \n".join(comp.errors.split(",")))
            if args.verbosity:
                print()
                print(comp.status)

        elif args.on:
            if comp.state_code == 2 or comp.state_code == 3:
                print("{} compressor {} at {} is already on".format(comp.model, comp.serial, comp.ip_address))
            elif comp.state_code != 0:
                print("{} compressor {} at {} cannot start at this time".format(comp.model,
                                                                                comp.serial, comp.ip_address))
            else:
                print("Turning {} compressor {} at {} on".format(comp.model, comp.serial, comp.ip_address))
                try:
                    comp.on()
                except RuntimeError:
                    print("Could not turn compressor on")
                    print("")
                    print("State: {}".format(comp.state))
                    print("Errors:")
                    print(" \n".join(comp.errors.split(",")))
            if args.verbosity:
                print()
                print(comp.status)
                
        elif args.freq:
            if comp.inverter:
                comp.set_inverter_freq(float(args.freq))
            else:
                print("Inverter not present")

        else:
            print(comp)
