from os import listdir, system, name
from os.path import join, isfile, isdir
from sys import stdout
from threading import Thread, enumerate
import hashlib
import requests
import time


NOT_FOUND = 404
TOO_MANY_REQUESTS = 429

MAX_THREADS = 8
THROTTLE_TIME = MAX_THREADS * 2
THREAD_CLASS_NAME = 'DownloadThread'

IMG_EXTS = [ 'jpg', 'jpeg', 'png', 'gif' ]
VID_EXTS = [ 'mp4', 'm4v', 'mkv', 'mov', 'wmv', 'webm', 'avi', 'flv']


"""
A class to download a URL to a directory on a separate thread.
"""
class DownloadThread(Thread):
    # Constants to describe the status of the thread
    ERROR = -1
    STANDBY = 0
    DOWNLOADING = 1
    HASHING = 2
    WRITING = 3
    FINISHED = 4
    
    # Initialize this DownloadThread
    def __init__(self, url, dst, algo=hashlib.md5, hashes={}):
        Thread.__init__(self)
        self.url = url
        self.dst = dst
        self.hashes = hashes
        self.algo = algo
        self.status = self.STANDBY
    
    # Perform downloading until successful or deemed impossible
    def run(self):
        ext = self.url.split('.')[-1]
        name = self.url.split('/')[-1].split('.')[0]
        media = None
        try:
            while(self.status == self.STANDBY):
                self.status = self.DOWNLOADING
                res = requests.get(self.url)
                if(res.status_code == TOO_MANY_REQUESTS):
                    self.status = self.STANDBY
                    time.sleep(THROTTLE_TIME)
                elif(res.status_code != NOT_FOUND):
                    media = res.content
        except:
            self.status = self.ERROR
            return
        
        if(media is None):
            self.status = self.ERROR
            return
        
        self.status = self.HASHING
        hash = self.algo(media).hexdigest()
        if(hash in self.hashes):
            self.status = self.FINISHED
            return

        self.status = self.WRITING
        self.hashes[hash] = name
        with open(join(self.dst, hash + '.' + ext), 'wb') as file_out:
            file_out.write(media)
        self.status = self.FINISHED

    # Print the information for this DownloadThread
    def print_status(self):
        status_char = ''
        if(self.status == self.STANDBY): status_char = ' S '
        elif(self.status == self.DOWNLOADING): status_char = '1/3'
        elif(self.status == self.HASHING): status_char = '2/3'
        elif(self.status == self.WRITING): status_char = '3/3'
        elif(self.status == self.FINISHED): status_char = ' ✓ '
        elif(self.status == self.ERROR): status_char = ' E '
        else: status_char = '?'
        stdout.write('[%s] %s\n' % (status_char, self.url))


"""
Clean a list of extensions to not include a leading dot.
@param exts - Original list of extensions.
@return a list of cleaned extensions.
"""
def clean_exts(exts):
    if(exts is None):
        return exts
    exts_clean = []
    for ext in exts:
        exts_clean.append(ext.replace('.', ''))
    return exts_clean


"""
Compute the hashes of files with specified extensions using a specified algorithm function.
@param dir - String of directory to process.
@param exts - List of extensions. If None, then all extensions are queried.
@param algo - Function for the hashing algorithm from hashlib.
@param hashes - Dictionary of seen hashes. Index is hash, value is original media name.
@param recurse - If true, subdirectories are traversed. If false, subdirectories are skipped.
@return a dictionary indexed by hash value storing the file name.
"""
def compute_file_hashes(dir, exts=None, algo=hashlib.md5, hashes={}, recurse=False):
    exts_clean = clean_exts(exts)
    for name in listdir(dir):
        full_name = join(dir, name)
        ext = name.split('.')[-1]
        if(isfile(full_name) and (exts_clean is None or ext in exts_clean)):
            stdout.write('[compute_file_hashes] INFO: Hashing (%s)... ' % (full_name))
            with open(full_name, 'rb') as file_in:
                file_bytes = file_in.read()
                file_hash = algo(file_bytes).hexdigest()
            if(file_hash not in hashes):
                hashes[file_hash] = full_name
                stdout.write('unique hash (%d).\n' % len(hashes))
            else:
                stdout.write('duplicate of (%s).\n' % (hashes[file_hash]))
        elif(recurse and isdir(full_name)):
            hashes = compute_file_hashes(full_name, exts=exts, algo=algo, hashes=hashes, recurse=True)
    return hashes


"""
Download media from a list of URLs if the hash has not been seen before.
@param dir - Destination directory for the download.
@param urls - List of URLs to query.
@param algo - Algorithm from hashlib used by the dictionary of hashes.
@param hashes - Dictionary of seen hashes. Index is hash, value is original media name.
@return the new dictionary of hashes.
"""
def download_urls(dir, urls, algo=hashlib.md5, hashes={}):
    for url in urls:
        stdout.write('[download_urls] INFO: Media from %s :\t\t' % (url))
        stdout.flush()
        ext = url.split('.')[-1]
        name = url.split('/')[-1].split('.')[0]
        try:
            media = None
            while(True):
                res = requests.get(url)
                if(res.status_code == TOO_MANY_REQUESTS):
                    stdout.write('Too many requests, delaying %d seconds. This is normal; have patience.\n' % (THROTTLE_TIME))
                    res.close()
                    time.sleep(THROTTLE_TIME)
                else:
                    if(res.status_code == NOT_FOUND):
                        stdout.write('Page does not exist, skipping\n')
                    else:
                        media = res.content
                    res.close()
                    break
        except:
            stdout.write('Unknown failure during retrieval, skipping.\n')
            continue
        if(media is None):
            continue
        hash = algo(media).hexdigest()
        if(hash not in hashes):
            hashes[hash] = name
            stdout.write('Downloading as %s\n' % (hash + '.' + ext))
            stdout.flush()
            with open(join(dir, hash + '.' + ext), 'wb') as file_out:
                file_out.write(media)
        else:
            stdout.write('Duplicate media of %s\n' % hashes[hash])
    return hashes


"""
Orchestrate multi-threaded downloads.
@param urls - List of URLs to download.
@param pics_dst - Destination for pictures.
@param vids_dst - Destination for videos.
@param hashes - Dictionary of hashes for existing downloaded media.
@return the updated hash table.
"""
def multithread_download_urls(urls, pics_dst, vids_dst, algo=hashlib.md5, hashes={}):
    pos = 0
    while(pos < len(urls)):
    
        download_threads = enumerate()
        
        while(len(download_threads) - 1 < MAX_THREADS):
            thread_url = urls[pos]
            thread_ext = thread_url.split('.')[-1]
            thread_dst = pics_dst if thread_ext in IMG_EXTS else vids_dst
            thread = DownloadThread(thread_url, thread_dst, algo=algo, hashes=hashes);
            thread.start()
            
            pos = pos + 1
            download_threads.append(thread)
            if(pos >= len(urls)):
                break
            
        system('cls') if name == 'nt' else system('clear')
        for thread in download_threads:
            if(thread.__class__.__name__ == THREAD_CLASS_NAME):
                thread.print_status()
        time.sleep(1)

    remaining = enumerate()
    while(len(remaining) > 1):
        system('cls') if name == 'nt' else system('clear')
        for thread in download_threads:
            if(thread.__class__.__name__ == THREAD_CLASS_NAME):
                thread.print_status()
        time.sleep(1)
        remaining = enumerate()
    
    system('cls') if name == 'nt' else system('clear')
    for thread in download_threads:
        if(thread.__class__.__name__ == THREAD_CLASS_NAME):
            thread.print_status()
    
    return hashes
