from .Util import Util
import sys
import os

if len(sys.argv) < 2:
    print("Usage: python convert-metadata.py <folder_to_convert_recursively>")
    sys.exit(1)

dir = sys.argv[1]
for f in Util.list_files(files=(),
                         folders=(dir,),
                         filter_func=Util.is_image,
                         max_files=1000000,
                         randomize=False):
    try:
        if os.path.exists(f + ".txt"):
            info = Util.read_metadata(f)
            if info:
                print("Converting " + f)
                if Util.write_metadata(f, info):
                    print("OK. Deleting " + f + ".txt")
                    os.unlink(f + ".txt")
                else:
                    print("Writing metadata failed, leaving txt in peace")
    except Exception as e:
        print("Oops: " + str(e))
