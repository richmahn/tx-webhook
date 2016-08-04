#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Richard Mahn <richard_mahn@wycliffeassociates.org>
#
#  Converts a tA repo into a HTML
#
#  Usage: md_to_pdf.py -i <directory of all ta repos> -o <directory where html flies will be placed>
#

import os
import re
import sys
import json
import codecs
import urllib2
import argparse
import datetime
import yaml
import markdown
import markdown2

body_json = ''
refs = {}

reload(sys)
sys.setdefaultencoding('utf8')

page_dict = {}
source_dir = ''
destination_dir = ''
current_dir = os.path.dirname(os.path.realpath(__file__))
main_template_file = 'http://master.door43.org/templates/main.html'

# template regex - uses Blade/Twig syntax
#
HEADING_REGEX = re.compile(r"(\{{2}\s*HEADING\s*\}{2})", re.DOTALL)
CONTENTS_REGEX = re.compile(r"(\{{2}\s*CONTENTS\s*\}{2})", re.DOTALL)

def generate_page(current_manual, data, header, pageBreak):
    slug = meta = html = ''
    page = '<div class="row">'

    if 'slug' in data:
        slug = data['slug']
        if 'meta' in page_dict[slug]:
            meta = page_dict[slug]['meta']
        if 'html' in page_dict[slug]:
            html = page_dict[slug]['html']

    if 'title' in data:
        title = data['title']
    elif meta:
        title = meta['title']

    page += '<div'
    if pageBreak:
        page += ' class="break"'
    if slug:
        page += ' id="'+slug+'"'
    page += '>'

    page += '<div class="col-md-9">'
    if title:
        page += '<h'+str(header)+'>'+data['title']+'</h'+str(header)+'>'

    if html:
        html = re.sub(u'https://git.door43.org/Door43/'+current_manual+'/src/master/content/(.*)\.md', '#\\1', html, flags=re.MULTILINE)
        page += html+"\n"

    if meta and 'recommended' in meta and meta['recommended'] and meta['recommended'][0]:
        recommended = json.loads(meta['recommended'])
        if recommended:
            bottom_box = '<div class="box">'
            bottom_box += 'Next we recommend you learn about:<ul>'
            for rec in recommended:
                if rec in page_dict:
                    manual = page_dict[rec]['manual']
                    recTitle = page_dict[rec]['title']
                    if current_manual == manual:
                        bottom_box += u'<li><em><a href="#'+rec+'">'+recTitle+u'</a></em></li>'
                    else:
                        manualTitle = manualDict[manual]['meta']['manual_title']
                        bottom_box += u'<li><em><a href="https://git.door43.org/Door43/'+manual+u'/src/master/content/'+rec+'.md">'+recTitle+u'</a></em> in <em><a href="https://git.door43.org/Door43/'+manual+u'/src/master/content/">'+manualTitle+'</a></em></li>'
                else:
                    bottom_box += u'<li><em>'+rec+u'</em></li>'
            bottom_box += u'</ul></div>'
            page += bottom_box
    page += "</div>\n"
    if meta and ('question' in meta or ('dependencies' in meta and meta['dependencies'] and meta['dependencies'][0])):
        top_box = '<div class="col-md-3"><div class="well">'
        if 'question' in meta:
            top_box += u'This page answers the question:<p><em>'+meta['question']+u'</em></p>'
        if 'dependencies' in meta and meta['dependencies'] and meta['dependencies']:
            dependencies = json.loads(meta['dependencies'])
            has_dependency_content = False
            dep_content = ''
            if dependencies:
                for dep in dependencies:
                    if dep in page_dict:
                        has_dependency_content = True
                        manual = page_dict[dep]['manual']
                        depTitle = page_dict[dep]['title']
                        if current_manual == manual:
                            dep_content += u'<li><em><a href="#'+dep+'">'+depTitle+u'</a></em></li>'
                        else:
                            manualTitle = manualDict[manual]['meta']['manual_title']
                            dep_content += u'<li><em><a href="https://git.door43.org/Door43/'+manual+u'/src/master/content/'+dep+'.md">'+depTitle+u'</a></em> in <em><a href="https://git.door43.org/Door43/'+manual+u'/src/master/content/">'+manualTitle+'</a></em></li>'
                if has_dependency_content:
                    top_box += u'In order to understand this topic, it would be good to read:<ul>' + dep_content + '</ul>'
        top_box += "</div></div>\n"
        page += top_box
    if 'subitems' in data:
        for idx, subitem in enumerate(data['subitems']):
            page += generate_page(current_manual, subitem, header+1, (idx != 0 or header != 1))
    page += "</div>\n"
    page += "</div>\n"
    return page

# Populate the page dictionary with the appropriate page information
#
def populate_page_dict(current_manual, data):
    slug = title = ''

    if 'title' in data:
        title = data['title']
    if 'slug' in data:
        slug = data['slug']
        filepath = os.path.join(source_dir, 'content', slug+'.md')
        html = markdown2.markdown_path(filepath, extras=["tables", "metadata"])
        page_dict[slug] = {
            'title': title,
            'html': html,
            'manual': current_manual,
            'meta': html.metadata
        }
    if 'subitems' in data:
       for subitem in data['subitems']:
           populate_page_dict(current_manual, subitem)

# Read the file
#
def read_file(infile):
    contents = codecs.open(infile, 'r', encoding='utf-8').read()
    return contents

# Get YAML file contents
#
def get_yaml_contents(yaml_file):
    f = open(yaml_file, 'r')
    yml = yaml.load(f)
    f.close()
    return yml

# Get the template code
#
def get_template_code():
    response = urllib2.urlopen(main_template_file)
    return response.read()

# Make the given directory
#
def make_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir, 0755)

# Write the file
#
def write_file(outfile, content):
    make_dir(outfile.rpartition('/')[0])
    f = codecs.open(outfile, 'w', encoding='utf-8')
    f.write(content)
    f.close()

# Do we have a valid tA manual
#
def valid_manual():
    return os.path.isdir(os.path.join(source_dir, 'content')) and os.path.exists(os.path.join(source_dir, 'toc.yaml')) and os.path.exists(os.path.join(source_dir, 'meta.yaml'))

def main():
    if not valid_manual():
        sys.exit('Your manual is not valid.')

    meta = get_yaml_contents(os.path.join(source_dir, 'meta.yaml'))
    toc = get_yaml_contents(os.path.join(source_dir, 'toc.yaml'))
    template = get_template_code()
    heading = meta['manual_title']
    contents = []

    for data in toc:
        populate_page_dict(meta['manual'], data)
        contents.append(generate_page(meta['manual'], data, 2, True))

    html = HEADING_REGEX.sub(heading, template)
    html = CONTENTS_REGEX.sub('\n'.join(contents), html)
    write_file(os.path.join(destination_dir, 'index.html'), html)

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
    main()
