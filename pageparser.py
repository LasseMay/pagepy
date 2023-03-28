from jinja2 import Environment, FileSystemLoader
from markdown.extensions.wikilinks import WikiLinkExtension
import glob
import markdown
import frontmatter
import shutil
import os

def write_html(template,context,path):
    content = template.render(context)
    with open(path, mode="w", encoding="utf-8") as outfile:
        outfile.write(content)

# paths
src_path = "src"
build_path = "out"

# TODO: make these parameters that can be set in a config
# design it in a way, that templates do not have to be registered here explicitly, except for index
environment = Environment(loader=FileSystemLoader("templates/"))
index_template = environment.get_template("index.html")
#blog_template = environment.get_template("blog.html")

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


# parse Landing page. parse markdown and handle special markers (replace them later with file list)
index_file = os.path.join(src_path, "index.md")
index_text = frontmatter.load(index_file)

# list of all md files except index.md 
files = [ f for f in glob.glob(f"{src_path}/*.md") if not f == index_file]

# store metadata of each document in this array, grouped by template,
# so that one can easily create overview pages. different templates for photos/blog/post/project/pages/cv/tutorials
# pages{ blog:["writing":<str>, "meta":<dict>] }
pages = {} 
kwrd2template = {} # store template objects and make the accesible via keyword

# loop over files once just to get a list of all of the templates being used and for storing metadata
for file in files:
    
    # metadata associated to each md file in src
    meta = {}
    
    # get filename
    in_file_stump = os.path.split(file)[1].split(".")[0] 
    meta["filename"] = in_file_stump+".html"
    
    # parse content, and separate metadata
    text = frontmatter.load(file)
    meta.update(index_text.metadata) # general 
    meta.update(text.metadata)       # page specific (can override general settings) 
   
    # extract actual text
    html = markdown.markdown(text.content, extensions=[WikiLinkExtension(end_url=".html")])

    # set context for rendering metadata and content
    context = {"writing":html, "meta":meta }
   
    # if the requested template is new, get it and add to dict for later
    templ_str = meta["template"]
    if not templ_str in pages.keys():
        kwrd2template[templ_str] = environment.get_template(f"{templ_str}.html")
        pages[templ_str] = []
      
    # add the context to the pages dict
    pages[templ_str].append(context)

# then render every page
for template in pages.keys():    # loop over differnet kinds of templates
    for page_context in pages[template]: # render every page of a given category
        templ = kwrd2template[page_context["meta"]["template"]]
        write_html(templ, page_context, os.path.join(build_path, page_context["meta"]["filename"]))

# save index html
# TODO: 
# in index md, define 
# top nav bar links (list) 
# and ways to create overview/list pages for each content template

index_context = {"posts":[f["meta"] for f in pages["blog"]],"title":"test_title"}
index_context["meta"] = index_text.metadata
write_html(index_template, index_context, os.path.join(build_path, "index.html"))
