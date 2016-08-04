#!/usr/bin/env python2
# A script for converting the USFM file based repo's into HTML for the
# new Door43 Site
#
import os
import sys
import argparse
import fnmatch
from support import *

source_dir = ''
destination_dir = ''
main_template_file = 'http://master.door43.org/templates/bible.html'

# Make the given directory
#
def make_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir, 0755)

# Build all files in a single HTML page
#
def build_single_html():
    # Convert to HTML
    print('#### Building Single Page HTML...')
    c = singlehtmlRenderer.SingleHTMLRenderer(source_dir, os.path.join(destination_dir, 'index.html'), main_template_file, 'Bible')
    c.render()

def main():
    build_single_html()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', '--source', dest="inpath",
        help="Directory of the tA repos to be compiled into html", required=True)
    parser.add_argument('-d', '--destination', dest="outpath", default='.',
        required=False, help="Output path of html files")

    args = parser.parse_args(sys.argv[1:])

    source_dir = args.inpath
    destination_dir = args.outpath

    print 'Using source directory: {0}'.format(source_dir)
    print 'Using destination directory: {0}'.format(destination_dir)
    main()
