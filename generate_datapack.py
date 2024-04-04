
## Python script that generates a datapack for placing every structures in the structures folder

# Imports
import os
import time
import zipfile

# Constants
STRUCTURES_FOLDER = "./structures"
NAMESPACE = "regions_to_structures"
NAME = "Regions To Structures"
PACK_FORMAT = 26
TICKS_BETWEEN_FORCELOAD_AND_PLACE = 20
CHUNKS_PER_TICK = 20

# Get all the structures
start = time.time()
structures = [file for file in os.listdir(STRUCTURES_FOLDER) if file.endswith(".nbt") and len(file.split("_")) == 3]
structures = [(i, file, len(structures)) for i, file in enumerate(structures)]

# Make the datapack
with zipfile.ZipFile("structures.zip", "w", zipfile.ZIP_DEFLATED) as zf:

	# Write pack.mcmeta
	zf.writestr(f"pack.mcmeta", f"""{{
	"pack": {{
		"pack_format": {PACK_FORMAT},
		"description": "{NAME}"
	}}
}}
""")

	# Copy structures
	for structure_counter, structure, total_structures in structures:
		zf.write(f"{STRUCTURES_FOLDER}/{structure}", f"data/{NAMESPACE}/structures/{structure}")
		if structure_counter % 100 == 99 or structure_counter == total_structures - 1:
			print(f"Structures {structure_counter + 1}/{total_structures} copied in {time.time() - start:.2f} seconds")
	
	# Write the functions that will place the structures using "/place template namespace:name x y z" and remove the forceload of the chunk
	functions_dict = {}
	for structure_counter, structure, total_structures in structures:
		struct_name = structure.replace(".nbt", "")
		x, y, z = map(int, struct_name.split("_"))
		function_name = f"{x}_{z}"
		if function_name not in functions_dict:
			functions_dict[function_name] = []
		functions_dict[function_name].append(f"place template {NAMESPACE}:{struct_name} {x} {y} {z}")
		if structure_counter % 100 == 99 or structure_counter == total_structures - 1:
			print(f"Structures {structure_counter + 1}/{total_structures} added to functions in {time.time() - start:.2f} seconds")
	for function_name, commands in functions_dict.items():
		x, z = map(int, function_name.split("_"))
		zf.writestr(f"data/{NAMESPACE}/functions/chunks/{function_name}.mcfunction", "\n".join(commands) + f"\nforceload remove {x} {z}")
	
	# As we can't place all the structures at once, we need to make a chain of functions that will place the structures
	functions = list(functions_dict.keys())
	for i in range(0, len(functions), CHUNKS_PER_TICK):
		commands = []
		tick = i // CHUNKS_PER_TICK

		# Get the functions to place the structures
		functions_chunk = functions[i:i + CHUNKS_PER_TICK]
		
		# Append forceload add commands
		for function_name in functions_chunk:
			x, z = map(int, function_name.split("_"))
			commands.append(f"forceload add {x} {z}")
		
		# Append the schedule functions
		for function_name in functions_chunk:
			commands.append(f"schedule function {NAMESPACE}:chunks/{function_name} {TICKS_BETWEEN_FORCELOAD_AND_PLACE}t")
		
		# Get the content in a string
		content = "\n".join(commands)

		# Write a schedule calling the next function in a tick if able
		if i + CHUNKS_PER_TICK < len(functions):
			content += f"\nschedule function {NAMESPACE}:place/{tick + 1} 1t"
		progression = str(tick) + "/" + str(len(functions) // CHUNKS_PER_TICK)
		content += '\ntellraw @a [{"text":"[Regions To Structures] ","color":"gold"},{"text":"Progression: ' + progression + '","color":"white"}]'

		# Write file
		zf.writestr(f"data/{NAMESPACE}/functions/place/{tick}.mcfunction", content)
		if i % 100 == 0:
			print(f"Functions {i}/{len(functions)} written in {time.time() - start:.2f} seconds")
	
	# Write the main function
	zf.writestr(f"data/{NAMESPACE}/functions/_place_everything.mcfunction", f"function {NAMESPACE}:place/0")
pass

# End of the script
print(f"Datapack generated in {time.time() - start:.2f} seconds")

