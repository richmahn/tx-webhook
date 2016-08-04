# -*- coding: utf-8 -*-
#

import abstractRenderer
import codecs
import datetime
import books
import urllib2
import re
import json

# template regex - uses Blade/Twig syntax
#
HEADING_REGEX = re.compile(r"(\{{2}\s*HEADING\s*\}{2})", re.DOTALL)
CONTENTS_REGEX = re.compile(r"(\{{2}\s*CONTENTS\s*\}{2})", re.DOTALL)
SIDEBAR_REGEX = re.compile(r"(\{{2}\s*SIDEBAR\s*\}{2})", re.DOTALL)

#
#   Simplest renderer. Ignores everything except ascii text.
#

class SingleHTMLRenderer(abstractRenderer.AbstractRenderer):

    def __init__(self, inputDir, outputFilename, templateFile, heading):
        # Unset
        self.content = ''  # the content string
        self.currentBookNumber = 0
        self.currentBook = {}
        self.heading = heading
        # IO
        self.outputFilename = outputFilename
        self.inputDir = inputDir
        # Position
        self.cb = u''    # Current Book
        self.cc = u'001'    # Current Chapter
        self.cv = u'001'    # Currrent Verse
        self.indentFlag = False
        self.bookName = u''
        self.chapterLabel = 'Chapter'
        self.lineIndent = 0
        self.template = templateFile

    def getTemplateCode(self):
        response = urllib2.urlopen(self.template)
        return response.read()

    def render(self):
        self.loadUSFM(self.inputDir)
        template = self.getTemplateCode()
        self.run()
        html = HEADING_REGEX.sub(self.heading, template)
        html = CONTENTS_REGEX.sub(self.content, html)
        html = SIDEBAR_REGEX.sub('', html)
        f = codecs.open(self.outputFilename, 'w', 'utf_8_sig')
        f.write(html)
        f.close()

    def startLI(self):
        self.lineIndent += 1
        return ur'<ul> '

    def stopLI(self):
        if self.lineIndent < 1:
            return u''
        else:
            self.lineIndent -= 1
            return ur'</ul>'

    def escape(self, s):
        return s.replace(u'~',u'&nbsp;')

    def write(self, unicodeString):
        self.content += unicodeString.replace(u'~', u' ')

    def writeIndent(self, level):
        self.write(u'\n\n')
        if level == 0:
            self.indentFlag = False
            self.write(u'<p class="indent-0">')
            return
        if not self.indentFlag:
            self.indentFlag = True
            self.write(u'<p>')
        self.write(u'<p class="indent-' + str(level) + u'">')

    def renderID(self, token):
        self.cb = books.bookKeyForIdValue(token.value)
        self.indentFlag = False
        self.write(u'\n\n<h1 id="' + self.cb + u'"></h1>\n')
    def renderH(self, token):       self.bookname = token.value
    def renderTOC2(self, token):
        self.currentBookNumber += 1
        cssId = 'book-' + str(self.currentBookNumber)
        self.write(u'\n\n<h1 id="' + cssId + u'" data-sidebar-value="' + cssId + u'" data-sidebar-label="' + token.value + u'">' + token.value + u'</h1>')
    def renderMT(self, token):
        return; #self.write(u'\n\n<h1>' + token.value + u'</h1>') # removed to use TOC2
    def renderMT2(self, token):     self.write(u'\n\n<h2>' + token.value + u'</h2>')
    def renderMT3(self, token):     self.write(u'\n\n<h2>' + token.value + u'</h2>')
    def renderMS1(self, token):     self.write(u'\n\n<h3>' + token.value + u'</h3>')
    def renderMS2(self, token):     self.write(u'\n\n<h4>' + token.value + u'</h4>')
    def renderP(self, token):
        self.indentFlag = False
        self.write(self.stopLI() + u'\n\n<p>')
    def renderPI(self, token):
        self.indentFlag = False
        self.write(self.stopLI() + u'\n\n<p class"indent-2">')
    def renderM(self, token):
        self.indentFlag = False
        self.write(u'\n\n<p>')
    def renderS1(self, token):
        self.indentFlag = False
        self.write(u'\n\n<h5>' + token.getValue() + u'</h5>')
    def renderS2(self, token):
        self.indentFlag = False
        self.write(u'\n\n<p align="center">----</p>')
    def renderC(self, token):
        self.cc = token.value.zfill(3)
        parentCssId = u'book-' + str(self.currentBookNumber)
        cssId = parentCssId + u'-chapter-' + token.value
        title = self.chapterLabel + ' ' + token.value
        titleHtml = u'\n\n<h2 id="' + cssId + u'" data-sidebar-value="' + cssId + u'" data-sidebar-parent-value="' + parentCssId + u'" data-sidebar-label="' + title + u'" class="c-num">'+ title + u'</h2>'
        self.write(self.stopLI() + titleHtml)
    def renderV(self, token):
        self.cv = token.value.zfill(3)
        self.write(u' <span class="v-num"><sup><b>' + token.value + u'</b></sup></span>')
    def renderWJS(self, token):     self.write(u'<span class="woc">')
    def renderWJE(self, token):     self.write(u'</span>')
    def renderTEXT(self, token):    self.write(u" " + self.escape(token.value) + u" ")
    def renderQ(self, token):       self.writeIndent(1)
    def renderQ1(self, token):      self.writeIndent(1)
    def renderQ2(self, token):      self.writeIndent(2)
    def renderQ3(self, token):      self.writeIndent(3)
    def renderNB(self, token):      self.writeIndent(0)
    def renderB(self, token):       self.write(self.stopLI() + u'\n\n<p class="indent-0">&nbsp;</p>')
    def renderIS(self, token):      self.write(u'<i>')
    def renderIE(self, token):      self.write(u'</i>')
    def renderNDS(self, token):     self.write(u'<span class="tetragrammaton">')
    def renderNDE(self, token):     self.write(u'</span>')
    def renderPBR(self, token):     self.write(u'<br />')
    def renderSCS(self, token):     self.write(u'<b>')
    def renderSCE(self, token):     self.write(u'</b>')
    def renderFS(self, token):      self.write(u'[Note: ')
    def renderFT(self, token):      self.write(token.value)
    def renderFE(self, token):      self.write(u'')
    def renderQSS(self, token):     self.write(u'<i>')
    def renderQSE(self, token):     self.write(u'</i>')
    def renderEMS(self, token):     self.write(u'<i>')
    def renderEME(self, token):     self.write(u'</i>')
    def renderE(self, token):
        self.indentFlag = False
        self.write(u'\n\n<p>' + token.value + '</p>')

    def renderPB(self, token):     pass
    def renderPERIPH(self, token):  pass

    def renderLI(self, token):       self.write( self.startLI() )
    def renderLI1(self, token):      self.write( self.startLI() )
    def renderLI2(self, token):      self.write( self.startLI() )
    def renderLI3(self, token):      self.write( self.startLI() )

    def renderS5(self, token):       self.write(u'')
    def renderCL(self, token):       self.chapterLabel = token.value
    def renderQR(self, token):       self.write(u'')
    def renderFQA(self, token):      self.write(u'] ' + token.value)
