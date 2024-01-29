#!/usr/bin/env python3

import sys
import esptool
import argparse
import esp32firmware as esp32
from makeelf.elf import *
from esp32exceptions import *
from esp32utils import *

DRAM0_DATA_START = None
DRAM0_DATA_END   = None

def printlog(*args, **kwargs):
  print(*args, **kwargs)

def if_addr_in_seg(image, addr, segname):
  for seg in image.ROM_LOADER.MEMORY_MAP:
    if seg[2]==segname and seg[0] <= addr < seg[1]:
        return True
  return False

def fix_image(chip, data, filename):
  global DRAM0_DATA_START, DRAM0_DATA_END
  
  try:
      image = esptool.LoadFirmwareImageFromBuffer(chip, data)
  except Exception as inst:
      printlog("Failed to parse : " + filename)
      printlog(inst)
      return False

  image_size = image.image_size()

  printlog("Image version: {}".format(image.version))
  printlog("real partition size: {}".format(image_size))

  for seg in image.segments:
    if if_addr_in_seg(image, seg.addr, "DROM"):
        seg_app_data = esp32.ESP_APP_DESC_STRUCT(seg.data)
        printlog("App data: {}".format(seg_app_data))

  fixed_image = None
  fixed_filename = filename + ".fixed"

  image.save(fixed_filename)
  with open(fixed_filename, "rb") as f:
    fixed_image = f.read() 

  output_image = fixed_image + data[len(fixed_image):len(data)]
  
  with open(fixed_filename, 'wb') as f:
    f.write(output_image)
  
  return True

def main():
    PARTITION_IMAGE = None

    try:
        parser = argparse.ArgumentParser(add_help=True, description='ESP32 fixer')

        parser.add_argument('--chip', '-c',
                            help='Target chip type',
                            choices=['esp32', 'esp32s2'],
                            default='esp32')

        subparsers = parser.add_subparsers(
            dest='operation',
            help='')

        parser_load_from_partition_file = subparsers.add_parser(
            'app_image',
            help='Fix all checksums in application partition image file')

        parser_load_from_partition_file.add_argument('filename', help='Application partition image')

        if len(sys.argv) == 1:
            printlog("Wrong arguments!!!")
            parser.print_help()
            exit(0)

        args = parser.parse_args()

        esp = None

        if args.operation=='app_image':
            chip_class = {
                'esp32'  : esptool.ESP32ROM,
                'esp32s2': esptool.ESP32S2ROM,
            }[args.chip]

            esp = chip_class(None) #dummy, to get constants only

            printlog("Reading partition image file from: {}".format(args.filename))
            with open(args.filename,"rb") as f:
                PARTITION_IMAGE = f.read() 

            fix_image(esp.CHIP_NAME, PARTITION_IMAGE, args.filename)
        else:
            printlog("Unknown operation: {}".format(args.operation))
            return

    except Exception as inst:
        printlog(type(inst))
        printlog(inst.args)
        printlog(inst)

def _main():
    try:
        main()
    except FatalError as e:
        printlog('\nA fatal error occurred: %s' % e)
        sys.exit(2)

if __name__ == '__main__':
    _main()