import os
import sys

from .DominantColors import DominantColors

dir = sys.argv[1]
m = {}

for f in sorted(os.listdir(dir)):
    if f.lower().endswith(".jpg") or f.lower().endswith(".jpg"):
        try:
            d = DominantColors(os.path.join(dir, f))
            calc = d.get_dominant_colors()
            print(f, "light:", calc[2])
            continue

            for fuzzy in range(20):
                if DominantColors.contains_color(calc, (255, 217, 100), fuzzy):
                    m[f] = fuzzy
                    print(f, fuzzy)
                    break
            else:
                m[f] = -1
                print(f, "no match")

        except Exception:
            print("oops for " + f)
            raise
            # pass

# print "\n----results----"
# for fuzzy in xrange(10):
#    print fuzzy
#    for k, v in m.items():
#        if v == fuzzy:
#            print k
#
# print "no match:"
# for k, v in m.items():
#    if v == -1:
#        print k
