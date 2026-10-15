import glob, os

current_dir = 'data/obj'

file_train = open('data/train.txt', 'w')
file_test = open('data/test.txt', 'w')

images = glob.glob("data/obj/*.png") + glob.glob("data/obj/*.jpg")

percentage_test = 10
index_test = round(100 / percentage_test)

counter = 0

for path in images:
    title = os.path.splitext(os.path.basename(path))[0]

    if counter % index_test == 0:
        file_test.write("data/obj/" + title + ".png\n")
    else:
        file_train.write("data/obj/" + title + ".png\n")

    counter += 1