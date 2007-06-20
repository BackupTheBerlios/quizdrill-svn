#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, Adam Schmalhofer <schmalhof@users.berlios.de>
# Developed at http://quizdrill.berlios.de/
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from builder import Abstract_Quiz_Writer, Abstract_Drill_Handler

from xml import sax
from xml.sax.handler import ContentHandler
import re
import sys
# i18n #
import gettext
_ = gettext.gettext


class Abstract_MediaWiki_Dump_Handler(ContentHandler):
    """
    Processes a MediaWiki pages-articles.xml Database Backup dump[1] and 
    passes the article and title to separate_article implemented by a child.

    [1]: http://meta.wikimedia.org/wiki/Data_dumps
    """
    def __init__(self, encoding='utf-8'):
        # Sax #
        self.encoding = encoding
        self.DATA_FIELD = "text"
        self.TITLE_FIELD = "title"
        self.in_data_field = False
        self.in_title_field = False
        self.content = ""
        self.title = ""

    def parse(self, file):
        try:
            self.read_data_source(file)
        except:
            self.endDocument()
            self.append_file.write('# Warning: Building of this Quiz got '
                    'interrupted.\n')
            self.write_quiz_data()
            raise
        else:
            self.write_quiz_data()   # finally-clause isn't py2.4 compatible

    def read_data_source(self, file):
        sax.parse(file, self)

    # Sax XML-methods #

    def startElement(self, name, attr):
        """
        Remember if we are in an xml-element of interest (title_field or
        data_field).
        """
        if name == self.DATA_FIELD:
           self.in_data_field = True
           self.content = ""
        if name == self.TITLE_FIELD:
            self.in_title_field = True
            self.title = ""

    def endElement(self, name):
        """
        Tracks whether we leave our xml-element of interest (title_field or 
        data_field) and processes the article if we leave data_field.
        """
        if name == self.DATA_FIELD:
            self.in_data_field = False
            if self.content:
                self.num_processed_articles += 1
                if self.separate_article(self.content):
                    self.num_found_infoboxes += 1
                print _('Found this infobox-type in %(num_boxes)s of '
                        '%(num_articles)s articles.') % \
                        {'num_boxes': self.num_found_infoboxes, 
                        'num_articles': self.num_processed_articles} + '\r',
        if name == self.TITLE_FIELD:
            self.in_title_field = False

    def characters(self, content):
        """
        Records the content if we are in an xml-element of interest
        (title_field or data_field).
        """
        if self.in_data_field:
            self.content += unicode.encode(content, self.encoding)
        if self.in_title_field:
            self.title += unicode.encode(content, self.encoding)

    def startDocument(self):
        self.num_processed_articles = 0
        self.num_found_infoboxes = 0

    def endDocument(self):
        print ""       # To keep the final 'progress bar'.

    # Processing Article #
    def separate_article(self, content):
        """
        Needs to be implemented by the child. Processes the actual article and
        returns True if new data is found.
        """
        raise AttributionError('Method "separate_article" should overwritten '
                'by a child of AbstractWikipediaHandler.')
        return False


class Abstract_MediaWiki_Handler(Abstract_MediaWiki_Dump_Handler, 
        Abstract_Drill_Handler):
    """
    Processes a MediaWiki pages-articles.xml Database Backup dump[1] and 
    passes the article and title to separate_article implemented by a child.

    [1]: http://meta.wikimedia.org/wiki/Data_dumps
    """

    def __init__(self, file_out, collected_head_tags, collected_build_tags,
            tag_dict={}):
        self.one_of_categories = [ ]
        self.wiki_cat_namespace = [ "category" ]
        tag_dict.update( {'wiki_cat_namespace': self.on_tag_wiki_cat_namespace,
            'one_of_categories': self.on_tag_one_of_categories} )
        Abstract_Drill_Handler.__init__(self, file_out, collected_head_tags,
                collected_build_tags, tag_dict)
        Abstract_MediaWiki_Dump_Handler.__init__(self, self.encoding)

    def on_tag_one_of_categories(self, word_pair_list):
        for word_pair in word_pair_list:
            self.one_of_categories.append(word_pair)

    def on_tag_wiki_cat_namespace(self, word_pair_list):
        assert len(word_pair_list) == 1, \
                _('Warning: Only one tag $wiki_cat_namespace allowed.')
        word_pair = word_pair_list[0]
        self.wiki_cat_namespace = word_pair


class Wikipedia_Article_Handler(Abstract_MediaWiki_Handler, 
        Abstract_Quiz_Writer):
    """
    Processes a MediaWiki database_dump (see class Abstract_MediaWiki_Handler),
    extracts data from the categories and named-templates (e.g. infoboxes
    and personendaten) and generates a .drill-file from it.
    """
    def __init__(self, file_out, collected_head_tags, collected_build_tags, 
            tag_dict={}):
        tag_dict.update( {'builder': self.on_tag_builder} )
        Abstract_MediaWiki_Handler.__init__(self, file_out, 
                collected_head_tags, collected_build_tags, tag_dict)
        Abstract_Quiz_Writer.__init__(self, 
                self.category_filter, self.question_filter, self.answer_filter)
        # Regular Expressions #
        self.re_flags = re.DOTALL | re.IGNORECASE
        ## Regular Expressions ##
        ### separate_article() ###
        # "\[\[" + cat + ":" + "("+ "[^|\]]*" +")" + "\|?" + ".*?" + "\]\]"
        self._cat_re_list = [ re.compile("\[\[" + cat + ":([^|\]]*)\|?.*?\]\]", 
            self.re_flags) for cat in self.wiki_cat_namespace ]
        self._comments_re = re.compile(r"<!--.*?-->", self.re_flags)
        #### infobox ####
        template_start = r"\{\{\S*:?" + self.template_tag
        template_body = r"[^{]*"
        template_end = r"\}\}"
        nested_template_body = r"[^}]*"
        self._unnested_template_re = re.compile(template_start + 
                template_body + template_end, self.re_flags)
        self._nested_template_re = re.compile(template_start + 
                nested_template_body + template_start, self.re_flags)
        ### remove_links() ###
        self._ref_section_re = re.compile(r"<ref>[^|<>]*?</ref>", self.re_flags)
        self._include_section_re = re.compile(r"<include>[^|<>]*?</include>", 
                self.re_flags)
        self._xml_code_re = re.compile(r"<[^|]*?>", self.re_flags)
        # "\[\[" + "(" + t + "\|)" + "{2,}" + t "\]\]"       with t = "[^|\]]*"
        self._images_re = re.compile(r"\[\[([^|\]]*\|){2,}[^|\]]*\]\]", 
                self.re_flags)
        # "\[\[" + t"*?" + "\|?" + "(" + t"*" + ")" + "\]\]"  with t="[^|\]]"
        self._wiki_links_re = re.compile(r"\[\[[^|\]]*?\|?([^|\]]*)\]\]", 
                self.re_flags)
        self._web_links_re = re.compile(r"\[[^ |\]]+ ?([^|\]]*?)\]")
        self._kursive_bold_re = re.compile(r"'''?(.*?)'?''")
        ### separate_infobox() ###
        self._infobox_end_re = re.compile(r"\|*[\s_]*\}\}")
        self._wiki_white_spaces_re = re.compile(r"([\s_\n]|&nbsp;)+")

    def on_tag_builder(self, word_pair_list):
        assert len(word_pair_list) == 1, \
                _('Warning: Only one tag $builder allowed.')
        word_pair = word_pair_list[0]
        self.template_tag = re.compile(r" ").sub(r"[\s_]", word_pair[1])

    def separate_article(self, text):
        """
        Extract data out of a given article. Currently templates and categories
        are supported.
        """
        dict = { "_article" : self.title.strip(), "_cat" : [] }
        found_data = False
        for cat_re in self._cat_re_list:
            dict["_cat"].extend([ cat for cat in cat_re.findall(text)])
        self.select_one_of_categories(dict)
        text = self._comments_re.sub("", text)
        if self._nested_template_re.search(text):
            print _('Warning: Skipping nested templates in "%s".') % \
                    self.title
        for infobox in self._unnested_template_re.findall(text):
            found_data = True
            infobox_dict = self.separate_infobox(infobox)
            infobox_dict.update(dict)
            self.append_template_to_quiz_data(infobox_dict)
        return found_data

    def select_one_of_categories(self, article_dict):
        """
        Generate the 'select_one_categories' values from the dictionary of
        the current wikipedia-page beeing processed.
        """
        categories = article_dict["_cat"]
        for cat_list in self.one_of_categories:
            for cat in cat_list[1:]:
                if cat in categories:
                    article_dict[cat_list[0]] = cat
                    break
            else:
                article_dict[cat_list[0]] = "_None_of" + cat_list[0]

    def separate_infobox(self, infobox):
        """
        Extract data out of a template (e.g. a infobox or personendaten).
        """
        text = self.remove_links(infobox)
        text = self._infobox_end_re.sub("", text)
        text = text.replace('\n', '')
        tag_list = text.split("|")
        dict = { "_head" : tag_list[0].strip()[3:] }
        for tag in tag_list[1:]:
            L = tag.split("=", 1)
            if len(L) == 2:
                dict[L[0].strip()] = self._wiki_white_spaces_re.sub(' ', 
                        (L[1]).strip())
            elif len(L) == 1 and not L[0].strip():
                pass
            else:
                print _('Warning: No parameter name in Infobox row '
                        '"%(para)s" in article "%(article)s".') % \
                                { 'para': L, 'article': self.title }
        return dict

    def remove_links(self, text):
        """
        Removes wikistructures, which often cause problems beacause they 
        contain "|" or "=": Weblinks (URLs sometimes have a "="), Images,
        Wikilinks, Sources (ref-sections) and XML tags (assigning attributes 
        have "=") as well as '' '' (kursiv) and ''' ''' (bold).
        """
        # remove sections #
        text = self._ref_section_re.sub("", text)
        text = self._include_section_re.sub("", text)
        text = self._xml_code_re.sub("", text)
        # remove Images etc (any "Link" with more then one "|" #
        text = self._images_re.sub("", text)
        # replace Links with Linktext #
        text = self._wiki_links_re.sub(r"\1", text)
        # replace web-links with label #
        text = self._web_links_re.sub(r"\1", text)
        # remove '' '' (kursiv) and ''' ''' (bold) #
        text = self._kursive_bold_re.sub(r"\1", text)
        return text

    # Writing Quiz Data #
    
    def append_template_to_quiz_data(self, dict):
        """
        Generate the quiz_data from a mediawiki-template (as a dictionary) and 
        append it to self.quiz_dict.
        """
        if self.category_tag in dict:
            cat = dict[self.category_tag]
        else:
            cat = ""
            if self.category_tag != "":
                print _('Warning: Parameter "%(para)s" missing in a template in ' 
                        'article "%(article)s", using "" instead.') % \
                            { 'para': self.category_tag, 
                                    'article': dict['_article'] }
        if self.question_tag in dict:
            question = dict[self.question_tag]
        else:
            print _('Warning: Parameter "%(para)s" missing in a template in ' 
                    'article "%(article)s", skipping.') % \
                            { 'para': self.question_tag, 
                                    'article': dict["_article"] }
            return
        if self.answer_tag in dict:
            answer = dict[self.answer_tag]
        else:
            print _('Warning: Parameter "%(para)s" missing in a template in '
                    'article "%(article)s", skipping.') % \
                            { 'para': self.answer_tag, 
                                    'article': dict["_article"] }
            return
        # actual adding to dictionary #
        if not cat in self.quiz_dict:
            self.quiz_dict[cat] = [[question, answer]]
        else:
            self.quiz_dict[cat].append([question, answer])


