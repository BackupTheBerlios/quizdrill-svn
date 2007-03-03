#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007, Adam Schmalhofer
# Developed by Adam Schmalhofer <schmalhof@users.berlios.de>
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


from xml import sax
from xml.sax.handler import ContentHandler
import re
import sys
# i18n
import locale
import gettext
_ = gettext.gettext
APP = "quizdrill"
DIR = "locale"
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)


class AbstractMediaWikiHandler(ContentHandler):
    """
    Processes a MediaWiki pages-articles.xml Database Backup dump[1] and 
    generates a Quizdrill quiz.

    [1]: http://meta.wikimedia.org/wiki/Data_dumps

    TODO: Spin-off class WikipediaArticleHandler.
    """
    def __init__(self, encoding="utf-8"):
        # Sax #
        self.encoding = "utf-8"
        self.DATA_FIELD = "text"
        self.TITLE_FIELD = "title"
        self.in_data_field = False
        self.in_title_field = False
        self.content = ""
        self.title = ""
        # Output #
        self.log_file = "log"
        #self.log("=== " + time.ctime() + " ===")

    def parse(self, file):
        sax.parse(file, self)
        self.write_quiz_data()

    # Sax XML-methods #

    def startElement(self, name, attr):
        if name == self.DATA_FIELD:
           self.in_data_field = True
           self.content = ""
        if name == self.TITLE_FIELD:
            self.in_title_field = True
            self.title = ""

    def endElement(self, name):
        if name == self.DATA_FIELD:
            self.in_data_field = False
            if self.content:
                self.separate_article(self.content)
        if name == self.TITLE_FIELD:
            self.in_title_field = False

    def characters(self, content):
        if self.in_data_field:
            self.content += unicode.encode(content, self.encoding)
        if self.in_title_field:
            self.title += unicode.encode(content, self.encoding)

    def separate_article(self, content):
        """
        Needs to be implemented by the child. Processes the actual article.
        """
        pass

class WikipediaArticleHandler(AbstractMediaWikiHandler):
    def __init__(self, append_file, template_tag, 
            category_tag, question_tag, answer_tag,
            category_filter, question_filter, answer_filter,
            one_of_categories=[], encoding="utf-8",
            wiki_cat_namespace=["category"]):
        AbstractMediaWikiHandler.__init__(self, encoding)
        self.append_file = open(append_file, "a")
        # Regular Expressions #
        self.re_flags = re.DOTALL | re.IGNORECASE
        self.template_tag = re.compile(r" ").sub(r"[\s_]", template_tag)
        # Quiz Generating #
        filter_dict = { "brackets" : self.filter_brackets }
        self.wiki_cat_namespace = wiki_cat_namespace
        self.category_tag = category_tag
        self.question_tag = question_tag
        self.answer_tag = answer_tag
        self.category_filter = filter_dict[category_filter]
        self.question_filter = filter_dict[question_filter]
        self.answer_filter = filter_dict[answer_filter]
        self.one_of_categories = one_of_categories
        self.quiz_dict = {}

    def separate_article(self, text):
        """
        Extract data out of a given article. Currently templates and categories
        are supported.
        """
        # infobox #
        template_start = r"\{\{\S*:?" + self.template_tag
        template_body = r"[^{]*"
        template_end = r"\}\}"
        nested_template_body = r"[^}]*"
        # Regular Expressions: Category #
        dict = { "_article" : self.title.strip(), "_cat" : [] }
        for cat in self.wiki_cat_namespace:
            # "\[\[" + cat + ":" + "("+ "[^|\]]*" +")" + "\|?" + ".*?" + "\]\]"
            cat_re = re.compile("\[\[" + cat + ":([^|\]]*)\|?.*?\]\]",
                    self.re_flags)
            dict["_cat"].extend([ cat for cat in cat_re.findall(text)])
        self.select_one_of_categories(dict)
        # Regular Expressions: Infobox #
        unnested_template_re = re.compile(template_start + 
                template_body + template_end, self.re_flags)
        nested_template_re = re.compile(template_start + 
                nested_template_body + template_start, self.re_flags)
        comments_re = re.compile(r"<!--.*?-->", self.re_flags)
        #
        text = comments_re.sub("", text)
        if nested_template_re.search(text):
            self.log("Warning skipping nested templates in %s." % self.title)
        for infobox in unnested_template_re.findall(text):
            infobox_dict = self.separate_infobox(infobox)
            infobox_dict.update(dict)
            self.append_quiz_data(infobox_dict)
        #print dict["_article"]

    def select_one_of_categories(self, dict):
        """
        """
        categories = dict["_cat"]
        for cat_list in self.one_of_categories:
            for cat in cat_list[1:]:
                if cat in categories:
                    dict[cat_list[0]] = cat
                    break
            else:
                dict[cat_list[0]] = "_None_of" + cat_list[0]

    def separate_infobox(self, infobox):
        """
        Extract data out of a template (e.g. a infobox or personendaten).
        """
        text = self.remove_links(infobox)
        text = re.compile(r"\|*[\s_]*\}\}").sub("", text)
        tag_list = text.split("|")
        dict = { "_head" : tag_list[0].strip()[3:] }
        for tag in tag_list[1:]:
            L = tag.split("=")
            if len(L) == 2:
                dict[L[0].strip()] = self.simple_white_spaces(L[1]).strip()
            elif len(L) == 1 and not L[0].strip():
                pass
            else:
                warn = "Warning: Tag %s isn't a Pair in '%s'." %(L, self.title)
                self.log(warn, infobox)
        return dict

    def remove_links(self, text):
        """
        Removes wikistructures, which often cause problems beacause they 
        contain "|" or "=": Weblinks (URLs sometimes have a "="), Images,
        Wikilinks, Sources (ref-sections) and XML tags (assigning attributes 
        have "=") as well as '' '' (kursiv) and ''' ''' (bold).
        """
        # remove ref-sections #
        text = re.compile(r"<ref>[^|<>]*?</ref>", self.re_flags).sub("", text)
        # remove include-sections #
        text = re.compile(r"<include>[^|<>]*?</include>", 
                self.re_flags).sub("", text)
        # remove xml-code #
        text = re.compile(r"<[^|]*?>", self.re_flags).sub("", text)
        # remove Images etc (any "Link" with more then one "|" #
        # "\[\[" + "(" + t + "\|)" + "{2,}" + t "\]\]"       with t = "[^|\]]*"
        text = re.compile(r"\[\[([^|\]]*\|){2,}[^|\]]*\]\]", 
                self.re_flags).sub("", text)
        # replace Links with Linktext #
        # "\[\[" + t"*?" + "\|?" + "(" + t"*" + ")" + "\]\]"  with t="[^|\]]"
        text = re.compile(r"\[\[[^|\]]*?\|?([^|\]]*)\]\]", 
                self.re_flags).sub(r"\1", text)
        # remove web-links #
        text = re.compile(r"\[[^ |\]]+ ?([^|\]]*?)\]").sub(r"\1", text)
        # remove '' '' (kursiv) and ''' ''' (bold) #
        text = re.compile(r"'''(.*?)'''").sub(r"\1", text)
        text = re.compile(r"''(.*?)''").sub(r"\1", text)
        return text

    def simple_white_spaces(self, text):
        """
        Convert wiki-white-spaces into " ".
        """
        return re.compile(r"([\s_\n]|&nbsp;)+").sub(" ", text)

    def filter_brackets(self, text):
        """
        Remove brackets as they often contain extra information, that isn't
        provided on all articles (so the user can't know when to type it and
        when not) and often not what the user wants to be tested on (e.g. 
        city name in a different language, which might not be (easily) typable.
        """
        text = re.compile(r"\(.*?\)").sub("", text)
        text = re.compile(r"\{.*?\}").sub("", text)
        text = re.compile(r"\[.*?\]").sub("", text)
        return text

    # Writing Quiz Data #
    
    def append_quiz_data(self, dict):
        """
        Generate the quiz_data of a template (as a dictionary) and append it 
        to self.quiz_dict.
        """
        if self.category_tag in dict:
            cat = self.category_filter(dict[self.category_tag])
        else:
            cat = ""
            if self.category_tag != "":
                print 'Warning "%s" missing in a template in article "%s", \
                        using "" instead' %\
                        ( self.category_tag, dict["_article"] )
        if self.question_tag in dict:
            question = self.question_filter(dict[self.question_tag])
        else:
            print 'Warning "%s" missing in a template in article "%s", \
                    skipping.' % ( self.question_tag, dict["_article"] )
            return
        if self.answer_tag in dict:
            answer = self.answer_filter(dict[self.answer_tag])
        else:
            print 'Warning "%s" missing in a template in article "%s", \
                    skipping.' % ( self.answer_tag, dict["_article"] )
            return
        # actual adding to dictionary #
        if not cat in self.quiz_dict:
            self.quiz_dict[cat] = [[question, answer]]
        else:
            self.quiz_dict[cat].append([question, answer])

    def write_quiz_data(self):
        """
        Append the quiz-data to the .drill-file.
        """
        str = ""
        for cat in self.quiz_dict.keys():
            str += "\n\n\n[" + cat + "]\n"
            for question in self.quiz_dict[cat]:
                str += "\n" + question[0] + " = " + question[1]
        self.append_file.write(str)

    # Misc #

    def log(self, short_msg, additional_msg=""):
        """
        Simple quick and dirty log method. Should be replaced be something 
        more standard in the future (see module logging).
        """
        print short_msg
        if self.log_file != None:
            long_msg = short_msg + "\n" + additional_msg + "\n=========="
            file = open(self.log_file, "a")
            #print "file.write: " + long_msg
            file.write(long_msg)
            file.close()


class DrillBuilder:
    def __init__(self):
        self.encoding = "utf-8"
        self.one_of_categories = []

    def convert_drill_file(self, file, database):
        file_out = file.replace(".builder", "") + ".original"
        fin = open(file)
        fout = open(file_out, "w")
        tag_dict = { "build_to" : self.on_tag_build_to, 
                "builder" : self.on_tag_builder, "filter" : self.on_tag_filter,
                "one_of_categories" : self.on_tag_one_of_categories, 
                "wiki_cat_namespace" : self.on_tag_wiki_cat_namespace }
        found_tags = { "build_to" : False, "builder" : False }
        for i, line in enumerate(fin.readlines()):
            line = line.strip()
            if len(line) == 0:
                pass
            elif line[0] == "$":
                colon = line.index(":")
                tag = line[1:colon]
                word_pair = [ w.strip() for w in line[colon+1:].split("=")]
                if tag in tag_dict:
                    tag_dict[tag](word_pair)
                    found_tags[tag] = True
                else:
                    print _('Warning: unknown tag "%s".') % tag
            else:
                fout.write(line + "\n")
        for tag in found_tags.keys():
            if not found_tags[tag]:
                print _('Error: missing mandatory tag "%s".') % tag
                sys.exit(1)
        fin.close()
        fout.close()
        builder = self.builder_class(file_out, self.template_tag, 
                self.category_tag, self.question_tag, self.answer_tag,
                self.category_filter, self.question_filter, self.answer_filter,
                self.one_of_categories, self.encoding, self.wiki_cat_namespace)
        builder.parse(database)

    def on_tag_builder(self, word_pair):
        builder_dict = {"WikipediaArticle" : WikipediaArticleHandler }
        assert len(word_pair) == 2, _('Error: tag $builder does not have \
                exactly one "=".')
        assert word_pair[0] in builder_dict, _('Error: unknown builder "%s".')\
                % tag
        self.builder_class = builder_dict[word_pair[0]]
        self.template_tag = word_pair[1]

    def on_tag_build_to(self, word_pair):
        assert len(word_pair) == 3, _('Error: tag $build_to does not have \
                exactly two "=".')
        self.category_tag = word_pair[0]
        self.question_tag = word_pair[1]
        self.answer_tag = word_pair[2]

    def on_tag_filter(self, word_pair):
        while len(word_pair) > 3:
            word_pair.append(None)
        self.category_filter = word_pair[0]
        self.question_filter = word_pair[1]
        self.answer_filter = word_pair[2]

    def on_tag_wiki_cat_namespace(self, word_pair):
        self.wiki_cat_namespace = word_pair

    def on_tag_one_of_categories(self, word_pair):
        self.one_of_categories = word_pair

if __name__ == "__main__":
    builder = DrillBuilder()
    if len(sys.argv) == 3:
        builder.convert_drill_file(sys.argv[1], sys.argv[2])
    else: 
        print _('Usage: %s [.drill.builder-file] [wikipedia.xml-file]') \
                % sys.argv[0]

