import argparse
import datetime
import os
import re
import subprocess

from glob import glob

KEY_VALUE_RE = re.compile('(\w+)\s+:\s+(.+)')
CHAPTER_RE = re.compile('Chapter #0:(\d+):\s+start\s+(\d+\.\d+),\s+end\s+(\d+\.\d+)')
BITRATE_RE = re.compile('bitrate:\s+(\d+)')

SANITIZE_FILENAME_RE = re.compile('\'|:|\\\\|/')


def Sanitize(path):
    return SANITIZE_FILENAME_RE.sub('', path)

def ProcessFile(filename, root_dir, authcode):
    bitrate = 0

    duration = 0
    tags = {}
    chapters = []

    cmd = ['ffmpeg.exe', '-i', filename]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
    for line in process.stdout:
        match = KEY_VALUE_RE.search(line)
        if match:
            if match.group(1) not in tags:
                tags[match.group(1)] = match.group(2)
            continue

        match = CHAPTER_RE.search(line)
        if match:
            chapter = int(match.group(1)) + 1
            start = match.group(2)
            end = match.group(3)
            chapters.append((chapter, start, end))
            duration = float(end)
            continue

        match = BITRATE_RE.search(line)
        if match:
            bitrate = match.group(1)

    title = Sanitize(tags['title']).replace(' (Unabridged)', '')
    output_dir = os.path.join(root_dir, tags['genre'], Sanitize(tags['artist']), title)
    
    if not os.path.isdir(output_dir):
        print 'Creating %s' % output_dir
        os.makedirs(output_dir)
    
    output_name = '%s - %s.mp3' % (Sanitize(tags['artist']), title)
    output_path = os.path.join(output_dir, output_name)

    print 'Duration: %s' % str(datetime.timedelta(seconds=duration))
    print 'Processing %s' % output_path 

    cmd = ['ffmpeg', '-v', 'error', '-stats', '-activation_bytes', authcode, '-i', filename, '-id3v2_version', '3', '-vn', '-c:a', 'libmp3lame', '-ab', bitrate, output_path]
    subprocess.call(cmd)

    for chapter in chapters:
        track = 'track="%s"' % chapter[0]
        chapter_output_path = os.path.join(output_dir, '%s - Chapter %s.mp3' % (output_name, chapter[0]))
        cmd = ['ffmpeg', '-v', 'error', '-stats', '-i', output_path, '-id3v2_version', '3', '-metadata', track, '-ss', chapter[1], '-to', chapter[2], '-acodec', 'copy', chapter_output_path]
        subprocess.call(cmd)    

    cover_path = os.path.join(output_dir, 'cover.jpg')
    cmd = ['ffmpeg', '-v', 'error', '-stats', '-activation_bytes', authcode, '-i', filename, '-an', '-vcodec', 'copy', cover_path]
    subprocess.call(cmd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authcode", help="Authentication code")
    parser.add_argument("--output_dir", help="Output directory")
    parser.add_argument('file', nargs='+')
    args = parser.parse_args()

    for filemask in args.file:
        for filename in glob(filemask):
            ProcessFile(filename, args.output_dir, args.authcode)



if __name__ == "__main__":
    main()