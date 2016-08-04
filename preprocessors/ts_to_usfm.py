#!/usr/bin/env python2
# A script for converting text chunks into USFM for conversion
#
import os
import sys
import codecs
import argparse
import fnmatch
import collections
import json
source_dir = ''
destination_dir = ''

# Make the given directory
#
def make_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir, 0755)

# Read the file
#
def read_file(infile):
    contents = codecs.open(infile, 'r', encoding='utf-8').read()
    return contents

# Write the file
#
def write_file(outfile, content):
    make_dir(outfile.rpartition('/')[0])
    f = codecs.open(outfile, 'w', encoding='utf-8')
    f.write(content)
    f.close()
# Check that a manifest file exists
#
def has_manifest():
    return os.path.isfile(os.path.join(source_dir, 'manifest.json'))

def get_manifest():
    with open(os.path.join(source_dir, 'manifest.json')) as data_file:
        data = json.load(data_file)
    return data

# Get the title of the project
#
def get_title():
    title = ''
    for root, dirnames, filenames in os.walk(source_dir):
        for filename in fnmatch.filter(filenames, 'title.txt'):
            title = read_file(os.path.join(root, filename))
    return title

# Get the heading for the USFM file
#
def get_usfm_heading(book_id, title):
    return (
        u'\id ' + book_id + u'\n'
        u'\ide UTF-8\n'
        u'\h ' + title + u'\n'
        u'\\toc1 ' + title + u'\n'
        u'\\toc2 ' + title + u'\n'
        u'\mt ' + title + u'\n\n'
    )

# Get the chapter's content
#
def get_chapter(chapter):
    chapter_content = ''
    for chapter in sorted(chapter):
        chapter_content += read_file(chapter)
    return chapter_content

# HOLD FOR NOW
def get_chapters():
    chapters = {}
    for root, dirnames, filenames in os.walk(source_dir):
        for filename in fnmatch.filter(filenames, '[0-9]*.txt'):
            chapter_key = os.path.basename(os.path.normpath(root))
            if not chapter_key in chapters:
                chapters[chapter_key] = []
            chapters[chapter_key].append(os.path.join(root, filename))
    return chapters

# Process the files
#
def process_files(book_id):
    title = get_title()
    usfm_content = get_usfm_heading(book_id, title)
    chapters = get_chapters()
    for key in sorted(chapters):
        usfm_content += get_chapter(chapters[key])
    write_file(os.path.join(destination_dir,  book_id + '.usfm'), usfm_content)

# The main function
#
def main():
    if has_manifest:
        manifest = get_manifest()
        book_id = manifest['project']['id'].upper()
        make_dir(destination_dir)
        process_files(book_id)
    else:
        print 'You are missing a manifest file'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', '--source', dest="inpath",
        help="Directory of the repo to be processed", required=True)
    parser.add_argument('-d', '--destination', dest="outpath",
        required=True, help="Output path of USFM files")

    args = parser.parse_args(sys.argv[1:])

    source_dir = args.inpath
    destination_dir = args.outpath

    print 'Using source directory: {0}'.format(source_dir)
    print 'Using destination directory: {0}'.format(destination_dir)
    main()
