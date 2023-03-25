from jinja2 import Environment, FileSystemLoader
from markdown.extensions.wikilinks import WikiLinkExtension
import glob
import markdown
import frontmatter
import shutil
import os
from collections import defaultdict

def write_html(template,context,path):
    content = template.render(context)
    with open(path, mode="w", encoding="utf-8") as outfile:
        outfile.write(content)

# paths
src_path = "src"
build_path = "out"

# TODO: make these parameters that can be set in a config
environment = Environment(loader=FileSystemLoader("templates/"))
index_template = environment.get_template("index.html")
blog_template = environment.get_template("blog.html")

# get a matchingn template as defined in the metadata of the respective file
kwrd2template = {"blog":blog_template}

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

# convert all posts
files = [ f for f in glob.glob(f"{src_path}/*.md") if not f == f"{src_path}/index.md"]
posts = []

# store metadata of each document in this array, grouped by template,
# so that one can easily create overview pages.
# pages{blog:[]}
pages = {} 

for file in files:
    
    # metadata associated to each md file in src
    meta = {}
    
    # get filename
    in_file_stump = os.path.split(file)[1].split(".")[0] 
    meta["filename"] = in_file_stump+".html"
    
    # parse content, and separate metadata
    text = frontmatter.load(file)
    meta.update(text.metadata) 
    
    # extract actual text
    html = markdown.markdown(text.content, extensions=[WikiLinkExtension(end_url=".html")])

    # get context for rendering metadata and content
    context = {"writing":html, "meta":meta}
   
    # get the matching template 
    templ = kwrd2template[meta["template"]] # the template is defined in the md file itself
    write_html(templ, context, os.path.join(build_path, meta["filename"]))
   
    # add to pages dict so that we can generate overview pages
    if not meta["template"] in pages.keys():
        pages[meta["template"]] = []
        
    pages[meta["template"]].append(meta)


# TODO: add config file for overview page
print(pages["blog"][0]["filename"])

# parse index.md

index_context = {"posts":pages["blog"], "title":"test_title"}

write_html(index_template, index_context, os.path.join(build_path, "index.html"))
