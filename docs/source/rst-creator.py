module_members = [
    # ".. automodule:: variety.__init__\n    :members:",
    ".. automodule:: variety.AboutVarietyDialog\n    :members:",
    ".. automodule:: variety.AbstractAddByQueryDialog\n    :members:\n    :undoc-members:",
    ".. automodule:: variety.AddFlickrDialog\n    :members:",
    ".. automodule:: variety.AddMediaRssDialog\n    :members:",
    ".. automodule:: variety.AddRedditDialog\n    :members:",
    ".. automodule:: variety.AddWallhavenDialog\n    :members:",
    ".. automodule:: variety.AttrDict\n    :members:",
    ".. automodule:: variety.CalibrateDominantColors\n    :members:",
    ".. automodule:: variety.DominantColors\n    :members:",
    ".. automodule:: variety.EditFavoriteOperationsDialog\n    :members:",
    ".. automodule:: variety.FlickrDownloader\n    :members:",
    ".. automodule:: variety.FolderChooser\n    :members:",
    ".. automodule:: variety.ImageFetcher\n    :members:",
    ".. automodule:: variety.indicator\n    :members:",
    ".. automodule:: variety.MediaRssDownloader\n    :members:",
    ".. automodule:: variety.Options\n    :members:",
    ".. automodule:: variety.PreferencesVarietyDialog\n    :members:",
    ".. automodule:: variety.QuotesEngine\n    :members:",
    ".. automodule:: variety.QuoteWriter\n    :members:",
    ".. automodule:: variety.RedditDownloader\n    :members:",
    ".. automodule:: variety.Texts\n    :members:",
    ".. automodule:: variety.ThumbsManager\n    :members:",
    ".. automodule:: variety.ThumbsWindow\n    :members:",
    ".. automodule:: variety.Util\n    :members:",
    ".. automodule:: variety.VarietyOptionParser\n    :members:",
    ".. automodule:: variety.VarietyWindow\n    :members:",
    ".. automodule:: variety.WallhavenDownloader\n    :members:",
    ".. automodule:: variety.WelcomeDialog\n    :members:",
]

file_contents = """.. {0}

{1}
{2}

.. automodule:: {3}
   :members:
   :undoc-members:


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`"""

def fill_file(content_string):
    # print(file_contents.format(1,2,3,4))
    # print(content_string)
    
    # ".. automodule:: variety.WelcomeDialog\n    :members:",
    title = content_string.split('variety.')[1].split("\n")[0]

    equals = "="*len(title)

    module_name = content_string.split('.. automodule:: ')[1].split("\n")[0]

    file_name = "-".join([module_name.split('.')[0], module_name.split('.')[1]])

    file_content_filled = file_contents.format(module_name, title, equals, module_name)
    new_file = open(file_name+".rst", "w+")
    new_file.write(file_content_filled)
    new_file.close()


    
f = open("file_names.temp", "w+")
for module_member in module_members:
    module_name = module_member.split('.. automodule:: ')[1].split("\n")[0]
    file_name = "-".join([module_name.split('.')[0], module_name.split('.')[1]])
    f.write("   " + file_name+".rst\n")
    # fill_file(module_member)

f.close()