import os
import random
import decimal

def process_filename(filename):
    # Split the filename by underscores and remove the ".png" extension
    parts = filename[:-4].split('_')
    
    if len(parts) < 5:
        return filename  # Skip any files that don't match the expected pattern
    
    # Extract the delay part and convert it to a float
    try:
        delay = float(parts[-1])
    except ValueError:
        return filename  # Skip if the delay part is not a valid float
    
    # Check if the delay is less than 0.9 and adjust if necessary
    min_delay = 0.9 + random.randrange(0, 10)/100
    if delay < min_delay:
        delay = min_delay

    # Reconstruct the filename with the modified delay
    parts[-1] = f"{delay:.2f}"  # Format the delay to 2 decimal places
    new_filename = '_'.join(parts) + ".png"
    
    return new_filename

def print_dir_tree(startpath, output_filename, exclude_dirs=None):

    with open(output_filename, "w") as output_file:
        for root, dirs, files in os.walk(startpath, topdown=True):
            # Skip directories that are in the exclude list
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                new_filename = process_filename(f)
                print(f"{new_filename}")
                output_file.write(f"{new_filename}\n")

# Example usage:
exclude_list = ['.git', '.import', '__pycache__', 'ArduinoJson', 'Pour_Moi', 'Codepo_22_23', 'CodePourChristian']
print_dir_tree('./img', "action.txt", exclude_list)
