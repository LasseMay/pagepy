import importlib.machinery
import importlib.util
import pkgutil
from jinja2 import Environment, FileSystemLoader
from markdown.extensions.wikilinks import WikiLinkExtension
import glob
import markdown
import frontmatter
import shutil
import os
import re
import copy
import pprint
import json

def load_plugins(plugin_dir):
    for file in os.listdir(plugin_dir):
        if file.endswith(".py"):
            # TODO: fix names
            file = (os.path.join(plugin_dir, file))
            loader = importlib.machinery.SourceFileLoader(file, file)
            spec = importlib.util.spec_from_loader(loader.name, loader)
            mod = importlib.util.module_from_spec(spec)
            loader.exec_module(mod)
            mod.print_hello()

def reg1(context, pages):
    return "reg1"

def reg2(context, pages):
    return "reg2"

# TODO: generalize this for every type of template
def blog(context, pages):
    out_str = "<ul>"
    for page in pages["blog"]:
        # TODO: make this a link to the actual page
        out_str += "<li>"
        out_str += page["meta"]["title"]
        out_str += "</li>"
    out_str += "</ul>"

    return out_str

filter_functions = {"reg1":reg1, "reg2":reg2, "blog":blog}

# TODO: make nicer by having a dict that matches key to a function that takes a (user implemented) copy of the context and returns a new contex
# TODO: also make the marker user defined
def handle_regex(context, pages):

    regexl = r"<p>\+\+\+"
    regexr = r"\+\+\+<\/p>"
    marker = regexl+"(.*)"+regexr

    # make sure, we do not mutate the original context and pages
    writing = copy.deepcopy(context["writing"])
    pages = copy.deepcopy(pages)

    keys = re.findall(marker,writing)
    for key in keys:
        func_call = key.split("|")
        func_name = func_call[0]
        print(func_name)
        if len(func_call) > 1:
            func_args = json.loads(func_call[1:][0])
            print(func_args)
        if key in filter_functions.keys(): 
            to_be_replaced = regexl+key+regexr
            writing = (re.sub(to_be_replaced,filter_functions[key](context,pages),writing))
    
    return writing

def write_html(template,context,path):
    content = template.render(context)
    with open(path, mode="w", encoding="utf-8") as outfile:
        outfile.write(content)

#####################
# Setup and Prepare #
#####################

# paths
src_path = "src/md"
plugin_path = "src/plugins"
build_path = "out"

load_plugins(plugin_path)

# TODO: make these parameters that can be set in a config
# design it in a way, that templates do not have to be registered here explicitly, except for index
environment = Environment(loader=FileSystemLoader("templates/"))
index_template = environment.get_template("index.html")
subfolders = [ f.path for f in os.scandir(src_path) if f.is_dir() ]

# copy subfolders that contain e.g. media over to out dir
for folder in subfolders:
    resource_folder = os.path.split(folder)[1]
    shutil.copytree(folder, 
                    os.path.join("out", resource_folder), 
                    symlinks=False,
                    ignore=None,
                    ignore_dangling_symlinks=False,
                    dirs_exist_ok=True)


# parse Landing page. 
index_file = os.path.join(src_path, "index.md")
index_text = frontmatter.load(index_file)

# list of all md files except index.md 
files = [ f for f in glob.glob(f"{src_path}/*.md") if not f == index_file]

# store metadata of each document in this array, grouped by template,
# so that one can easily create overview pages. different templates for photos/blog/post/project/pages/cv/tutorials
# pages{ blog:["writing":<str>, "meta":<dict>] }
pages = {} 
kwrd2template = {} # store template objects and make the accesible via keyword


############################################################
# first parse all files and store metadata and content #####
############################################################

for file in files:
    
    # metadata associated to each md file in src
    meta = {}
    
    # get filename
    in_file_stump = os.path.split(file)[1].split(".")[0] 
    meta["filename"] = in_file_stump+".html"
    
    # parse content, and separate metadata
    text = frontmatter.load(file)
    meta.update(index_text.metadata) # every page has the metadata from index.md 
    meta.update(text.metadata)       # which can be overriden locally 
   
    # extract actual text
    html = markdown.markdown(text.content, extensions=[WikiLinkExtension(end_url=".html")])

    # set context for rendering metadata and content
    context = {"writing":html, "meta":meta }
   
    # if the requested template is new, get it and add to dict for later
    # TODO: if there is no template provided, use a default one to render
    if not "template" in meta.keys():
        #meta["template"] = "default" # for now use the blog template to render. in the future, this might change
        meta["template"] = "blog"
    
    # if the template is new, get it and add to dict for later
    templ_str = meta["template"] 
    if not templ_str in pages.keys():
        kwrd2template[templ_str] = environment.get_template(f"{templ_str}.html")
        pages[templ_str] = []
      
    # add the context to the pages dict so they are ordered by template
    pages[templ_str].append(context)


#######################################
# loop over all pages and render them #
#######################################

for template in pages.keys():                                   # loop over differnet kinds of templates
    for page_context in pages[template]:                        # render every page of a given category
        page_context["writing"] = handle_regex(page_context,pages)    # handle markers in text
        templ = kwrd2template[page_context["meta"]["template"]]
        write_html(templ, page_context, os.path.join(build_path, page_context["meta"]["filename"]))

###################
# save index html #
###################

# TODO: in index.md let the user procide a list of top bar links to pages
index_context = {"posts":[f["meta"] for f in pages["blog"]],
        "title":"test_title"}
index_context["meta"] = index_text.metadata
write_html(index_template, index_context, os.path.join(build_path, "index.html"))

