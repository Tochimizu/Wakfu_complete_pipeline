import os


# Function to map the new names to the original files
def map_and_rename_files(new_names, directory_path):
    print(directory_path)
    # Get the list of files in the directory
    files_in_directory = os.listdir(directory_path)

    # Create a mapping for the new names based on the tag (e.g., "0003")
    new_names_mapping = {name[:4]: name for name in new_names}

    # Iterate over the files in the directory
    for old_file_name in files_in_directory:
        # Extract the tag from the old file name (assuming tag is the first 4 characters)
        old_file_tag = old_file_name[:4]

        # If the old file's tag exists in the new names mapping, check if renaming is necessary
        if old_file_tag in new_names_mapping:
            new_file_name = new_names_mapping[old_file_tag]
            old_file_path = os.path.join(directory_path, old_file_name)
            new_file_path = os.path.join(directory_path, new_file_name)

            # Rename the file only if the old and new names are different
            if old_file_name != new_file_name:
                os.rename(old_file_path, new_file_path)
                print(f'Renamed: {old_file_name} -> {new_file_name}')
            else:
                print(f'Skipped renaming {old_file_name}, names are the same.')


# This is the list of new names from the text file
with open("action.txt", "r") as file:
    new_names = [name.strip() for name in file.readlines()]  # Remove trailing newlines

# Path to the directory containing the original files (adjust this path)
directory_path = './img'

# Call the function to map and rename files
map_and_rename_files(new_names, directory_path)
