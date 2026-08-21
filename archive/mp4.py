import subprocess
import glob
import os
import time
import random

def report(t):
    sec = round(time.time()-t, 0)
    min = round(sec/60, 0)
    hr = round(min/60, 0)
    return {'sec':sec, 'min':min, 'hr':hr}


def go(type = 'jpg'):
    filenames = glob.glob('*.{}'.format(type))
    if not filenames:
        print('No files of type {}'.format(type))
        return

    path = os.path.abspath("").replace("\\", "/")
    print('Making mp4 in {}\n'.format(path))
    duration = 0.05
    duration = 1
    name = os.path.basename( os.getcwd() )

    mp4start = time.time()

    # create a file list of image format
    with open("input.txt", "wb") as outfile:
        for filename in filenames:
            outfile.write(f"file '{path}/{filename}'\n".encode())
            outfile.write(f"duration {duration}\n".encode())

    command_line = 'ffmpeg -stream_loop 1 -y -r 30 -analyzeduration 2000M -probesize 120000M -f concat -safe 0 -i input.txt -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" {}\\{}.mp4'.format(path, name)
    print(command_line)
    pipe = subprocess.Popen(command_line, shell=True, stdout=subprocess.PIPE).stdout
    output = pipe.read().decode()
    pipe.close()

    mt = report(mp4start)
    print('Created mp4 using ffmpeg from {} {} files in {} seconds / {} minutes / {} hours.'.format(len(filenames), type, mt['sec'], mt['min'], mt['hr']))

def randomfiles():
    # Get the list of files in the current folder
    files = os.listdir()

    # Shuffle the list of files randomly
    random.shuffle(files)

    # Iterate over the files and rename them with sequential numbers
    for i, file_name in enumerate(files):
        # Get the file extension
        _, extension = os.path.splitext(file_name)

        # Generate the new file name with a sequential number and the original extension
        new_file_name = f"{i+1:04d}{extension}"

        # Rename the file
        os.rename(file_name, new_file_name)


if __name__=='__main__':
    print('Build mp4')
    #go(type='jpg')
    randomfiles()
