
## Python script that generates a .nbt structures generated from a world's region folder.

# Imports
import os
import anvil # pip install git+https://github.com/matcool/anvil-parser.git
from nbt import * # pip install nbt
import time
import math

def getAsPair(self):
	return (self >> 32, self & 0xFFFFFFFF)

# Function
def process_region(region_file):
	region_counter, file, total_regions = region_file

	# Constants
	CHUNK_DIM = 16
	REGION_DIM = 32
	STRUCT_DIM = 48
	TO_REMOVE = ("id", 'x', 'y', 'z')

	# Starting time
	start_time = time.time()

	# Read the region
	path = "./region/" + file
	r = anvil.Region.from_file(path)
	
	# Some variables
	data_version = 0
	structures = []
	
	# For each chunk in the region,
	for i in range(REGION_DIM):
		for j in range(REGION_DIM):
			c = r.chunk_data(i, j)
			if not c:
				continue
			c_x, c_z = c["xPos"].value * CHUNK_DIM, c["zPos"].value * CHUNK_DIM

			# Copy data version
			dv = c["DataVersion"].value
			if data_version < dv:
				data_version = dv
			
			# Get all the blocks of the chunk
			blocks = []
			for block in c["block_entities"]:
				t_x, t_y, t_z = [block[k].value for k in 'xyz']
				blocks.append((t_x, t_y, t_z, block))
			
			for section in c["sections"]:
				if "block_states" not in section:
					continue
				states = section["block_states"]
				if "palette" not in states or "data" not in states:
					continue
				yOffset = section["Y"].value * CHUNK_DIM
				palette = states["palette"]
				blockStates = states["data"]
				states_data = []
				for bs in blockStates:
					tempDataView = bytearray(8)
					pair = getAsPair(bs)
					tempDataView[:4] = int(pair[0]).to_bytes(4, byteorder='big')
					tempDataView[4:] = int(pair[1]).to_bytes(4, byteorder='big')
					states_data.append(int.from_bytes(tempDataView, byteorder='big'))
				bits = max(4, math.ceil(math.log2(len(palette))))
				bit_mask = (1 << bits) - 1
				state = 0
				data = states_data[state]
				data_length = 64

				for k in range(4096):
					if data_length < bits:
						state += 1
						data = states_data[state]
						data_length = 64
					palette_id = data & bit_mask
					block_state = palette[palette_id]
					if block_state["Name"].value != "minecraft:air":
						x = k & 0xF
						y = (k >> 8)
						z = (k >> 4) & 0xF
						real_x = c_x + x
						real_y = yOffset + y
						real_z = c_z + z
						blocks.append((real_x, real_y, real_z, block_state))
					data >>= bits
					data_length -= bits

			# If no block, continue
			if not blocks:
				continue

			# Get min and max y
			min_y = min([block[1] for block in blocks])
			max_y = max([block[1] for block in blocks])
			
			# Make structures from the blocks
			current_y = min_y
			while current_y <= max_y:
				structure = []
				for block in blocks:
					if block[1] >= current_y and block[1] < current_y + STRUCT_DIM:
						structure.append(block)
				if structure:
					structures.append(structure)
				
				# Increment height
				current_y += STRUCT_DIM
	print(f"Region {region_counter + 1}/{total_regions}: {len(structures)} structures found in {time.time() - start_time:.2f} seconds")

	# For each structure, make the file
	for i, structure in enumerate(structures):

		# Get coordinates
		min_x = min([block[0] for block in structure])
		min_y = min([block[1] for block in structure])
		min_z = min([block[2] for block in structure])
		max_x = max([block[0] for block in structure])
		max_y = max([block[1] for block in structure])
		max_z = max([block[2] for block in structure])
		size_x = max_x - min_x + 1
		size_y = max_y - min_y + 1
		size_z = max_z - min_z + 1

		# Start making the nbt file
		path = f"./structures/{min_x}_{min_y}_{min_z}.nbt"
		nbt_file = nbt.NBTFile()
		nbt_file['size'] = nbt.TAG_List(type = nbt.TAG_Int)
		for i in (size_x, size_y, size_z):
			nbt_file['size'].append(nbt.TAG_Int(i))
		nbt_file['DataVersion'] = nbt.TAG_Int(data_version)
		nbt_file['entities'] = nbt.TAG_List(type = nbt.TAG_Compound)
		nbt_file['palette'] = nbt.TAG_List(type = nbt.TAG_Compound)
		nbt_file['blocks'] = nbt.TAG_List(type = nbt.TAG_Compound)

		# Make the palette
		palette = []
		for x, y, z, block in structure:
			if "Name" not in block:
				block['Name'] = nbt.TAG_String(value = block['id'].value)
			for i in list(block):
				if i in TO_REMOVE or "Paper" in i:
					del block[i]
			if block not in palette:
				palette.append(block)
				nbt_file['palette'].append(block)

		# Make the blocks
		for x, y, z, block in structure:
			
			# Get state (index of the block in the palette)
			new_block = nbt.TAG_Compound()
			new_block['state'] = nbt.TAG_Int(palette.index(block))
			new_block['pos'] = nbt.TAG_List(type = nbt.TAG_Int)
			for i in (x - min_x, y - min_y, z - min_z):
				new_block['pos'].append(nbt.TAG_Int(i))
			nbt_file['blocks'].append(new_block)

		# Write the file
		nbt_file.write_file(path)
	print(f"Region {region_counter + 1}/{total_regions}: {len(structures)} structures saved in {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":

	# Make structures folder
	if not os.path.exists("./structures"):
		os.mkdir("./structures")
	else:
		for file in os.listdir("./structures"):
			os.remove("./structures/" + file)

	# Get all the regions
	regions = [file for file in os.listdir("./region") if file.endswith(".mca")]
	regions = [(i, file, len(regions)) for i, file in enumerate(regions)]

	# Process the files
	from multiprocessing import Pool
	THREADS = 12
	start = time.time()
	with Pool(processes = THREADS) as pool:
		pool.map(process_region, regions)
	print(f"\nTotal time: {time.time() - start:.2f} seconds")

