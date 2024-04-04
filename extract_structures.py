
## Python script that generates a .nbt structures generated from a world's region folder.

# Imports
import os
import anvil # pip install git+https://github.com/matcool/anvil-parser.git
from nbt import * # pip install nbt
import time
import math

def getAsPair(self):
	return (self >> 32, self & 0xFFFFFFFF)

def indexInPalette(palette: list[nbt.TAG_Compound], block: nbt.TAG_Compound) -> int:
	for i, b in enumerate(palette):
		if b["Name"].value == block["Name"].value:
			if "Properties" in block:
				if "Properties" in b and (b['Properties'].pretty_tree() == block['Properties'].pretty_tree()):
					return i
			else:
				return i
	return -1

# Constants
CHUNK_DIM = 16
REGION_DIM = 32
STRUCT_DIM = 48
TO_REMOVE = ("Properties", "Name", "id", 'x', 'y', 'z')

# Function
def process_region(region_file):
	region_counter, file, total_regions = region_file

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
			try:
				c = r.chunk_data(i, j)
				if not c:
					continue
				c_x, c_z = c["xPos"].value * CHUNK_DIM, c["zPos"].value * CHUNK_DIM

				# Copy data version
				dv = c["DataVersion"].value
				if data_version < dv:
					data_version = dv
				
				# Get all the block entities of the chunk
				blocks = [(block['x'].value, block['y'].value, block['z'].value, block) for block in c["block_entities"]]

				# Get all the normal blocks of the chunk for each section
				valid_sections = [section for section in c["sections"] if "block_states" in section and "palette" in section["block_states"] and "data" in section["block_states"]]
				for section in valid_sections:

					states = section["block_states"]
					yOffset = section["Y"].value * CHUNK_DIM
					section_palette = states["palette"]

					states_data = []
					tempDataView = bytearray(8)
					for bs in states["data"]:
						pair = getAsPair(bs)
						tempDataView[:4] = int(pair[0]).to_bytes(4, byteorder='big')
						tempDataView[4:] = int(pair[1]).to_bytes(4, byteorder='big')
						states_data.append(int.from_bytes(tempDataView, byteorder='big'))
					
					bits = max(4, math.ceil(math.log2(len(section_palette))))
					bit_mask = (1 << bits) - 1
					state = 0
					data = states_data[0]
					data_length = 64

					for k in range(4096):
						if data_length < bits:
							state += 1
							data = states_data[state]
							data_length = 64
						palette_id = data & bit_mask
						block_state = section_palette[palette_id]
						if block_state["Name"].value != "minecraft:air":
							# x = c_x + (k & 0xF)
							# y = yOffset + (k >> 8)
							# z = c_z + ((k >> 4) & 0xF)
							blocks.append((c_x + (k & 0xF), yOffset + (k >> 8), c_z + ((k >> 4) & 0xF), block_state))
						data >>= bits
						data_length -= bits

				# If no block, continue
				if not blocks:
					continue

				# Get min and max y
				current_y = min([block[1] for block in blocks])
				max_y = max([block[1] for block in blocks])
				
				# Make structures from the blocks
				while current_y <= max_y:
					structure = []
					for block in blocks:
						if block[1] >= current_y and block[1] < current_y + STRUCT_DIM:
							structure.append(block)
					if structure:
						structures.append(structure)
					
					# Increment height
					current_y += STRUCT_DIM
			except Exception as e:
				print(f"Error during Region {region_counter + 1}/{total_regions} ({file}): {e}")
				continue

	# For each structure, make the file
	for i, structure in enumerate(structures):

		# Get coordinates
		min_x, min_y, min_z, _ = structure[0]
		max_x, max_y, max_z, _ = structure[0]
		for x, y, z, block in structure:
			min_x = min(min_x, x)
			min_y = min(min_y, y)
			min_z = min(min_z, z)
			max_x = max(max_x, x)
			max_y = max(max_y, y)
			max_z = max(max_z, z)
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
		nbt_file["blocks"] = nbt.TAG_List(type = nbt.TAG_Compound)

		# Make the palette
		final_palette = []
		for x, y, z, block in structure:
			if "Name" not in block:
				block['Name'] = nbt.TAG_String(value = block['id'].value)
			
			block_in_palette = nbt.TAG_Compound()
			block_in_palette['Name'] = block['Name']
			if "Properties" in block:
				block_in_palette['Properties'] = block['Properties']

			if indexInPalette(final_palette, block_in_palette) == -1:
				final_palette.append(block_in_palette)
				nbt_file['palette'].append(block_in_palette)

		# Make the blocks
		taken_positions = []	# For optimisations
		for x, y, z, block in structure:
			if "Name" not in block:
				block['Name'] = nbt.TAG_String(value = block['id'].value)
			
			block_in_palette = nbt.TAG_Compound()
			block_in_palette['Name'] = block['Name']
			if "Properties" in block:
				block_in_palette['Properties'] = block['Properties']
			
			# Get state (index of the block in the palette)
			new_block = nbt.TAG_Compound()
			new_block['state'] = nbt.TAG_Int(indexInPalette(final_palette, block_in_palette))

			# Get position
			new_x, new_y, new_z = x - min_x, y - min_y, z - min_z
			new_block["pos"] = nbt.TAG_List(type = nbt.TAG_Int)
			new_block["pos"].append(nbt.TAG_Int(new_x))
			new_block["pos"].append(nbt.TAG_Int(new_y))
			new_block["pos"].append(nbt.TAG_Int(new_z))
			
			# Get nbt (if any)
			new_block["nbt"] = nbt.TAG_Compound()
			for i in list(block):
				if not(i in TO_REMOVE or "Paper" in i):
					new_block["nbt"][i] = block[i]

			# If no nbt, remove
			if not new_block["nbt"]:
				del new_block["nbt"]
			
			# Check if there is a block already at the position and merge it
			if (new_x, new_y, new_z) in taken_positions:

				# Search for the block
				for i, b in enumerate(nbt_file["blocks"]):
					b_pos = tuple([x.value for x in b["pos"]])
					if b_pos == (new_x, new_y, new_z):

						# Merge: Copy nbt and state
						if "nbt" in new_block:
							if "nbt" in b:
								for key in new_block["nbt"]:
									b["nbt"][key] = new_block["nbt"][key]
							else:
								b["nbt"] = new_block["nbt"]
						b["state"] = new_block["state"]
						break
			
			# Add block to the list and the taken positions
			else:
				nbt_file["blocks"].append(new_block)
				taken_positions.append((new_x, new_y, new_z))

		# Write the file
		nbt_file.write_file(path)
	print(f"Region {region_counter + 1}/{total_regions}: {len(structures)} structures saved in {time.time() - start_time:.2f} seconds")

def thread_regions(regions):
	for region in sorted(regions, key = lambda x: x[0]):
		try:
			process_region(region)
		except Exception as e:
			print(f"Error during Region {region[0] + 1}/{region[2]} ({region[1]}): {e}")

if __name__ == "__main__":
	THREADS = 10

	# Make structures folder
	if os.path.exists("./structures"):
		import shutil
		shutil.rmtree("./structures")
	os.mkdir("./structures")

	# Get all the regions
	regions = [file for file in os.listdir("./region") if file.endswith(".mca")]
	regions = [(i, file, len(regions)) for i, file in enumerate(regions)]
	
	# Sort regions so thread start with first regions
	regions_per_thread = []
	for i in range(THREADS):
		thread_list = []
		for j in range(i, len(regions), THREADS):
			thread_list.append(regions[j])
		regions_per_thread.append(thread_list)

	# Process the files
	from multiprocessing import Pool
	start = time.time()
	with Pool(processes = THREADS) as pool:
		pool.map(thread_regions, regions_per_thread)
	print(f"\nTotal time: {time.time() - start:.2f} seconds")

