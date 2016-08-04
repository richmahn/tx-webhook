#!/usr/bin/env python2
# A script for converting the Open Bible Stories Text based repo's into HTML for the
# new Door43 Site
#
import os
import sys
import re
import codecs
import getopt
import json
import urllib2

# Globals
#
current_dir = os.path.dirname(os.path.realpath(__file__))
source_dir = ''
destination_dir = ''
image_api_url = 'https://api.unfoldingword.org/obs/jpg/1/'
main_template_file = 'http://master.door43.org/templates/reveal.html'
resolutions = ['360px', '2160px']
ignoreDirectories = ['.git', '00']
framesIgnoreFiles = ['.DS_Store', 'reference.txt', 'title.txt']

# HTML templates
#
frame_template = u'<section data-background="{0}"><p>{1}</p></section>'
next_link_template = u'<section><a href="../{0}/index.html"><p>{1}</p></a></section>'
# to include literal braces in a format string, double them
#
menu_link_template = u'<li><a href="../{0}/{{{{ PATH_INDEX }}}}">{1}</a></li>'
title_template = u'''<section><h1>{0}</h1><h3>{1}</h3></section>'''

# template regex - uses Blade/Twig syntax
#
LANG_CODE_REGEX = re.compile(r"(\{{2}\s*LANG_CODE\s*\}{2})", re.DOTALL)
HEADING_REGEX = re.compile(r"(\{{2}\s*HEADING\s*\}{2})", re.DOTALL)
HOME_REGEX = re.compile(r"(\{{2}\s*HOME\s*\}{2})", re.DOTALL)
HOME_LINK_REGEX = re.compile(r"(\{{2}\s*HOME_LINK\s*\}{2})", re.DOTALL)
MENY_REGEX = re.compile(r"(\{{2}\s*MENY\s*\}{2})", re.DOTALL)
REVEAL_SLIDES_REGEX = re.compile(r"(\{{2}\s*REVEAL_SLIDES\s*\}{2})", re.DOTALL)
`1234`
# paths for local and web files
PATH_INDEX_REGEX = re.compile(r"(\{{2}\s*PATH_INDEX\s*\}{2})", re.DOTALL)

# list layout [RegularExpression, LocalPath, WebPath]
res_paths = [[PATH_INDEX_REGEX, u'index.html', u'']]

# Describe how to use this script
#
def usage():
    print ''
    print 'Usage:'
    print '     convert_to_html.py [options]'
    print 'Options:'
    print '     -s --source [DIR] Source directory'
    print '     -d --destination [DIR] Destination directory'
    print '     -h --help Show this message'
    print ''

# Get the provide arguments to this script
#
def get_arguments(argv):
    global source_dir, destination_dir
    try:
        opts, args = getopt.getopt(argv, 'hs:d:', ['help', 'source=', 'destination='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    if opts:
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                usage()
                sys.exit()
            elif opt in ('-s', '--source'):
                source_dir = arg
            elif opt in ('-d', '--destination'):
                destination_dir = arg
    else:
        usage()
        sys.exit()

# Get a list of all available chapters
#
def get_chapters():
    chapters = []
    for chapter in os.listdir(source_dir):
        if os.path.isdir(os.path.join(source_dir, chapter)) and not chapter in ignoreDirectories:
            chapters.append({
                'number': chapter,
                'title': get_chapter_title(chapter),
                'reference': get_chapter_reference(chapter),
                'frames': get_chapter_frames(chapter)
            })
    return chapters

# Get a chapte title, if the title file does not exist, it will hand back the number with a period only.
#
def get_chapter_title(chapter):
    title_file = os.path.join(source_dir, chapter, 'title.txt')
    title = chapter.lstrip('0') + '. '
    if os.path.exists(title_file):
        contents = read_file(title_file)
        title = contents.strip()
    return title

# Get the chapters reference text
#
def get_chapter_reference(chapter):
    reference_file = os.path.join(source_dir, chapter, 'reference.txt')
    reference = ''
    if os.path.exists(reference_file):
        contents = read_file(reference_file)
        reference = contents.strip()
    return reference

# Get the frames for each chapter
#
def get_chapter_frames(chapter):
    frames = []
    chapter_dir = os.path.join(source_dir, chapter)
    for frame in os.listdir(chapter_dir):
        if not frame in framesIgnoreFiles:
            text = read_file(os.path.join(chapter_dir, frame))
            frames.append({
                'id': chapter + '-' + frame.strip('.txt'),
                'text': text
            })
    return frames

# Get the frame image for the given resolution
#
def get_frame_img_url(resolution, frame_id):
    return '{0}en/{1}/obs-en-{2}.jpg'.format(image_api_url, resolution, frame_id)

# Get the language for the file
# defaults to en
#
def get_language():
    language = 'en'
    manifest = os.path.join(source_dir, 'manifest.json')
    if os.path.exists(manifest):
        data = json.load(open(manifest))
        if data:
            target_language = data.get('target_language', {}).get('id')
            if target_language is not None:
                language = target_language
    return language

# Returns an HTML list formated string of the chapters with links.
#
def get_menu(chapters):
    menu = []
    i = 1
    for chapter in chapters:
        menu.append(menu_link_template.format(str(chapter.get('number')).zfill(2), chapter.get('title')))
        i += 1
    return u'\n'.join(menu)

# Get the template code
#
def get_template_code():
    response = urllib2.urlopen(main_template_file)
    return response.read()

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

# Write the final file
#
def write_slideshow(output_file, page):
    for itm in res_paths:
        page = itm[0].sub(itm[1], page)

    write_file(output_file, page)

# Make the given directory
#
def make_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir, 0755)

# Convert the OBS repo to HTML
#
def convert():
    language = get_language()
    chapters = get_chapters()
    meny = get_menu(chapters)
    template = get_template_code()

    for resolution in resolutions:
        if chapters:
            last_chapter = chapters[-1]
            for i in range(0, len(chapters)):
                page = []
                chapter = chapters[i]
                frames = chapter.get('frames')
                page.append(title_template.format(chapter.get('title'), chapter.get('reference')))

                if frames:
                    # a slides for each frame
                    for frame in frames:
                        img_url = get_frame_img_url(resolution, frame.get('id'))
                        page.append(frame_template.format(img_url, frame.get('text')))

                if chapter.get('number') != last_chapter.get('number'):
                    # a slide that links to the next story
                    next_chapter = chapters[i + 1]
                    page.append(next_link_template.format(str(next_chapter.get('number')).zfill(2), next_chapter.get('title')))

                # put it together
                html = MENY_REGEX.sub(meny, template)
                html = REVEAL_SLIDES_REGEX.sub('\n'.join(page), html)
                html = LANG_CODE_REGEX.sub(language, html)
                html = HEADING_REGEX.sub('Open Bible Stories: ' +chapter.get('title'), html)
                html = HOME_REGEX.sub('Open Bible Stories Home', html)
                html = HOME_LINK_REGEX.sub('https://unfoldingword.org/stories/', html)

                # save the html
                output_file = os.path.join(destination_dir, resolution, chapter.get('number'), 'index.html')
                write_slideshow(output_file, html)

if __name__ == '__main__':
    get_arguments(sys.argv[1:])
    print 'Using source directory: {0}'.format(source_dir)
    print 'Using destination directory: {0}'.format(destination_dir)
    convert()
