
## Python script that generates a .nbt structures generated from a world's region folder.

# Imports
from nbt import *

# Get build battle structure 
file = "build_battle.nbt"
nbtfile = nbt.NBTFile(file, 'rb')
del nbtfile['palette']
print(nbtfile.pretty_tree()[:1024])



