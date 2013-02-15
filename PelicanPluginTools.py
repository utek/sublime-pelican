# -*- coding: utf-8 -*-

import sublime
import datetime
import re
import os

import sys
if sys.getdefaultencoding() != 'utf-8':
    reload(sys)
    sys.setdefaultencoding('utf-8')

pelican_slug_template = {
    "md": "slug: %s\n",
    "rst": ":slug: %s\n",
}

default_filter = '.*\\.(md|markdown|mkd|rst)$'

global_settings = sublime.load_settings("Pelican.sublime-settings")

pelican_article_views = []

def addPelicanArticle(view):
    view_id = view.id()
    if not view_id in pelican_article_views:
        pelican_article_views.append(view_id)

def removePelicanArticle(view):
    view_id = view.id()
    if view_id in pelican_article_views:
        pelican_article_views.remove(view_id)

def isPelicanArticle(view):
    if view.id() in pelican_article_views:
        return True

    if view.file_name():
        filepath_filter = load_setting(view, "filepath_filter", default_filter)

        use_input_folder_in_makefile = load_setting(view, "use_input_folder_in_makefile", True)
        if use_input_folder_in_makefile:
            makefile_params = parse_makefile(view.window())
            if makefile_params and "INPUTDIR" in makefile_params:
                filepath_filter = makefile_params['INPUTDIR'] + "/" + default_filter

        if re.search(filepath_filter, view.file_name()):
            return True

    return False

def strDateNow():
    now = datetime.datetime.now()
    return datetime.datetime.strftime(now, "%Y-%m-%d %H:%M:%S")

def load_setting(view, setting_name, default_value):
    if len(setting_name) < 1:
        if default_value:
            return default_value
        return None

    return view.settings().get(setting_name, global_settings.get(setting_name, default_value))

def normalize_line_endings(view, string):
    string = string.replace('\r\n', '\n').replace('\r', '\n')
    line_endings = load_setting(view, 'default_line_ending', 'unix')
    if line_endings == 'windows':
        string = string.replace('\n', '\r\n')
    elif line_endings == 'mac':
        string = string.replace('\n', '\r')
    return string

def load_article_metadata_template_lines(view, meta_type = None):
    if meta_type is None:
        meta_type = detect_article_type(view)

    article_metadata_template = load_setting(view, "article_metadata_template", {})
    if not article_metadata_template or len(article_metadata_template) < 1:
        return

    return article_metadata_template[meta_type]

def load_article_metadata_template_str(view, meta_type = None):
    if meta_type is None:
        meta_type = detect_article_type(view)

    article_metadata_template = load_article_metadata_template_lines(view, meta_type)
    return normalize_line_endings(view, "\n".join(article_metadata_template))

def detect_article_type(view):
    if isPelicanArticle(view) and view.file_name():
        if re.search("rst", view.file_name()):
            return "rst"
        return "md"

    if view.find("^:\w+:", 0):
        return "rst"
    return "md"

def parse_makefile(window):
    makefile_path = None
    current_filename = window.active_view().file_name()
    current_folder = os.path.dirname(current_filename)
    current_folders = window.folders()
    for folder in current_folders:
        if folder in current_folder:
            break
    makefile_dir = folder
    makefile_path = os.path.join(makefile_dir, "Makefile")
    if not os.path.exists(makefile_path):
        return None

    # parse parameters in Makefile
    regex = re.compile("(\S+)=(.*)")
    makefile_content = ""
    with open(makefile_path, 'r') as f:
        makefile_content = f.read()

    if len(makefile_content) > 0:
        origin_makefile_params = []
        origin_makefile_params = regex.findall(makefile_content)

        if len(origin_makefile_params) > 0:

            makefile_params = {"CURDIR": makefile_dir}

            for (key, value) in origin_makefile_params:
                if not key in makefile_params:
                    # replace "$(var)" to "%(var)s"
                    value = re.sub(r"\$\((\S+)\)", r"%(\1)s", value)

                    makefile_params[key] = value % makefile_params

            return makefile_params
    return None

def get_categories_tags(window, mode = "tag"):
    # load INPUTDIR
    inputdir = None
    makefile_params = parse_makefile(window)
    if makefile_params and "INPUTDIR" in makefile_params:
        inputdir = makefile_params['INPUTDIR']
    else:
        return

    # get paths of all articles in INPUTDIR
    articles_paths = []
    inputdir_structure = os.walk(inputdir)
    if inputdir_structure:
        for (dirpath, dirnames, filenames) in inputdir_structure:
            for filename in filenames:
                article_path = os.path.join(dirpath, filename)
                if re.search(default_filter, article_path):
                    articles_paths.append(article_path)
    else:
        return

    # retrieve categories or tags
    results = []
    for article_path in articles_paths:
        if mode == "category":
            regex = re.compile("category:(.*)", re.IGNORECASE)
        else:
            regex = re.compile("tags:(.*)", re.IGNORECASE)

        with open(article_path) as f:
            content_str = f.read()

        regex_results = regex.findall(content_str)
        if len(regex_results) > 0:
            for result in regex_results:
                results.extend( [x.strip() for x in result.split(",")] )

    if len(results) == 0:
        return None

    list_results = sorted(list(set(results)))
    if '' in list_results:
        list_results.remove('')

    return list_results
