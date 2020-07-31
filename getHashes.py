#!/usr/bin/python
import os
import sys
import libs
import libs.fingerprint as fingerprint
import json
from termcolor import colored
from libs.reader_file import FileReader
from libs.db_sqlite import SqliteDatabase
from libs.config import get_config

if __name__ == '__main__':
  config = get_config()

  db = SqliteDatabase()
  

  # fingerprint all files in a directory

  for filename in sys.argv:
    if filename.endswith(".mp3"):
      reader = FileReader(filename)
      audio = reader.parse_audio()

      print colored('   new song, going to analyze..', 'green')

      hashes = set()
      channel_amount = len(audio['channels'])

      for channeln, channel in enumerate(audio['channels']):
        msg = '   fingerprinting channel %d/%d'
        print colored(msg, attrs=['dark']) % (channeln+1, channel_amount)

        channel_hashes = fingerprint.fingerprint(channel, Fs=audio['Fs'], plots=config['fingerprint.show_plots'])
        channel_hashes = set(channel_hashes)

        msg = '   finished channel %d/%d, got %d hashes'
        print colored(msg, attrs=['dark']) % (
          channeln+1, channel_amount, len(channel_hashes)
        )

        hashes |= channel_hashes

      msg = '   finished fingerprinting, got %d unique hashes'

      values = []
      for hash, offset in hashes:
        values.append({'hash':hash,'offset':offset})
      with open('your_file.json', 'w') as f:
        json.dump(values, f)
          
  print('end')
