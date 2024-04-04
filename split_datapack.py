
## Python script that generates a datapack for placing every structures in the structures folder

# Imports
import os
import time
import zipfile
import shutil

# Constants
SPLITTED_FOLDER = "./splitted_structures"
NB_SPLITS = 50
DATAPACK = "structures.zip"
NAMESPACE = "regions_to_structures"

# Create the splitted folder
if os.path.exists(SPLITTED_FOLDER):
	shutil.rmtree(SPLITTED_FOLDER)
os.makedirs(SPLITTED_FOLDER)

# Open the datapack
start_time = time.time()
with zipfile.ZipFile(DATAPACK, "r") as zf:

	# Get structures
	structures = [file for file in zf.namelist() if file.startswith(f"data/{NAMESPACE}/structures/") and file.endswith(".nbt")]

	# Get functions
	functions = [file for file in zf.namelist() if file.startswith(f"data/{NAMESPACE}/functions/chunks/") and file.endswith(".mcfunction")]
	
	# Split the structures
	for i in range(NB_SPLITS):
		with zipfile.ZipFile(f"{SPLITTED_FOLDER}/{DATAPACK[:-4]}_part{i+1}.zip", "w", zipfile.ZIP_DEFLATED, compresslevel = 9) as zf_split:

			# Write pack.mcmeta
			zf_split.writestr(f"pack.mcmeta", zf.read("pack.mcmeta"))
			
			# Copy a part of the structures
			start_index = i * len(structures) // NB_SPLITS
			end_index = (i + 1) * len(structures) // NB_SPLITS
			for structure in structures[start_index:end_index]:
				zf_split.writestr(structure, zf.read(structure))
			
			# Copy the functions
			start_index = i * len(functions) // NB_SPLITS
			end_index = (i + 1) * len(functions) // NB_SPLITS
			for function in functions[start_index:end_index]:
				zf_split.writestr(function, zf.read(function))
	
	# Make part 0 (copy everything that is not a structure)
	with zipfile.ZipFile(f"{SPLITTED_FOLDER}/{DATAPACK[:-4]}_part0.zip", "w", zipfile.ZIP_DEFLATED, compresslevel = 9) as zf_split:
		for file in zf.namelist():
			if not file.startswith(f"data/{NAMESPACE}/structures/") and not file.startswith(f"data/{NAMESPACE}/functions/chunks/"):
				zf_split.writestr(file, zf.read(file))

# Print the time
print(f"{len(structures)} structures splitted in {time.time() - start_time:.2f} seconds")

