#!/usr/bin/python
import os
import sys
import libs
import libs.fingerprint as fingerprint

from termcolor import colored
from libs.reader_file import FileReader
from libs.db_sqlite import SqliteDatabase
from libs.config import get_config
import argparse

from argparse import RawTextHelpFormatter
from itertools import izip_longest
from libs.reader_microphone import MicrophoneReader
from libs.visualiser_console import VisualiserConsole as visual_peak
from libs.visualiser_plot import VisualiserPlot as visual_plot
from libs.db_sqlite import SqliteDatabase
if __name__ == '__main__':
  config = get_config()

  db = SqliteDatabase()
  path = "mp3/"

  # fingerprint all files in a directory

  for filename in os.listdir(path):
    if filename.endswith(".mp3"):
      reader = FileReader(path + filename)
      audio = reader.parse_audio()

      song = db.get_song_by_filehash(audio['file_hash'])
      song_id = db.add_song(filename, audio['file_hash'])

      msg = ' * %s %s: %s' % (
        colored('id=%s', 'white', attrs=['dark']),       # id
        colored('channels=%d', 'white', attrs=['dark']), # channels
        colored('%s', 'white', attrs=['bold'])           # filename
      )
      print msg % (song_id, len(audio['channels']), filename)
      '''
      if song:
        hash_count = db.get_song_hashes_count(song_id)

        if hash_count > 0:
          msg = '   already exists (%d hashes), skip' % hash_count
          print colored(msg, 'red')

          continue
      '''
      print colored('   new song, going to analyze..', 'green')

      hashes = set()
      channel_amount = len(audio['channels'])

      def grouper(iterable, n, fillvalue=None):
            args = [iter(iterable)] * n
            return (filter(None, values) for values
                in izip_longest(fillvalue=fillvalue, *args))


      # reader.save_recorded('test.wav')


      Fs = fingerprint.DEFAULT_FS
      

      result = set()
      matches = []

      def find_matches(samples, Fs=fingerprint.DEFAULT_FS):
            hashes = fingerprint.fingerprint(samples, Fs=Fs)
            return return_matches(hashes)

      def return_matches(hashes):
            mapper = {}
            for hash, offset in hashes:
                mapper[hash.upper()] = offset
            values = mapper.keys()

            for split_values in grouper(values, 1000):
                # @todo move to db related files
                query = """
                    SELECT upper(hash), song_fk, offset
                    FROM fingerprints
                    WHERE upper(hash) IN (%s)
                """
                query = query % ', '.join('?' * len(split_values))

                x = db.executeAll(query, split_values)
                matches_found = len(x)

                if matches_found > 0:
                    msg = '   ** found %d hash matches (step %d/%d)'
                    print colored(msg, 'green') % (
                    matches_found,
                    len(split_values),
                    len(values)
                    )
                else:
                    msg = '   ** not matches found (step %d/%d)'
                    print colored(msg, 'red') % (
                    len(split_values),
                    len(values)
                    )

                for hash, sid, offset in x:
                    # (sid, db_offset - song_sampled_offset)
                    yield (sid, offset - mapper[hash])

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
        matches.extend(find_matches(channel))
      msg = '   finished fingerprinting, got %d unique hashes'

      def align_matches(matches):
            diff_counter = {}
            largest = 0
            largest_count = 0
            song_id = -1

            for tup in matches:
                sid, diff = tup

                if diff not in diff_counter:
                    diff_counter[diff] = {}

                if sid not in diff_counter[diff]:
                    diff_counter[diff][sid] = 0

                diff_counter[diff][sid] += 1

                if diff_counter[diff][sid] > largest_count:
                    largest = diff
                    largest_count = diff_counter[diff][sid]
                    song_id = sid

            songM = db.get_song_by_id(song_id)

            nseconds = round(float(largest) / fingerprint.DEFAULT_FS *
                                fingerprint.DEFAULT_WINDOW_SIZE *
                                fingerprint.DEFAULT_OVERLAP_RATIO, 5)

            return {
                    "SONG_ID" : song_id,
                    "SONG_NAME" : songM[1],
                    "CONFIDENCE" : largest_count,
                    "OFFSET" : int(largest),
                    "OFFSET_SECS" : nseconds
                }

      total_matches_found = len(matches)

      print ''

      if total_matches_found > 0:
            msg = ' ** totally found %d hash matches'
            print colored(msg, 'green') % total_matches_found

            song = align_matches(matches)

            msg = ' => song: %s (id=%d)\n'
            msg += '    offset: %d (%d secs)\n'
            msg += '    confidence: %d'

            print colored(msg, 'green') % (
            song['SONG_NAME'], song['SONG_ID'],
            song['OFFSET'], song['OFFSET_SECS'],
            song['CONFIDENCE']
            )
      else:
            msg = ' ** not matches found at all'
            print colored(msg, 'red')

        

  print('end')
