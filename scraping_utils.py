#!/usr/bin/env python3

from os import listdir, system, name
from os.path import join, isfile, isdir, commonpath
from sys import stdout
from threading import Thread, enumerate
import hashlib
import requests
import time


NOT_FOUND = 404
TOO_MANY_REQUESTS = 429
CONNECTION_RESET = 104

MAX_THREADS = 8
THROTTLE_TIME = MAX_THREADS * 4

IMG_EXTS = [ 'jpg', 'jpeg', 'png', 'gif', 'webp' ]
VID_EXTS = [ 'mp4', 'm4v', 'mkv', 'mov', 'wmv', 'webm', 'avi', 'flv', 'mp3' ]


"""
A class to download a URL to a directory on a separate thread.
"""
class DownloadThread(Thread):
    # Constants to describe the status of the thread
    ERROR = -99
    TIMEOUT = -1

    STANDBY = 0
    CONNECTING = 1
    HASHING = 2
    DOWNLOADING = 3
    WRITING = 4
    FINISHED = 5
    
    # Initialize this DownloadThread
    def __init__(self, file_name, url, dst, algo=hashlib.md5, hashes={}):
        Thread.__init__(self)
        self.name = file_name
        self.url = url
        self.dst = dst
        self.hashes = hashes
        self.algo = algo
        self.status = self.STANDBY
        self.total_size = 1
        self.downloaded = 0
        
    # Perform downloading until successful or deemed impossible
    def run(self):
        media = None
        
        try:
            while(self.status == self.STANDBY):
                self.status = self.DOWNLOADING
                res = requests.get(self.url)
                self.total_size = int(res.headers.get("content-length", 0))
                self.downloaded = len(res.content)
                if(res.status_code == TOO_MANY_REQUESTS):
                    self.status = self.STANDBY
                    time.sleep(THROTTLE_TIME)
                elif(res.status_code != NOT_FOUND):
                    media = res.content
                    
        except requests.exceptions.Timeout:
            self.status = self.TIMEOUT
            time.sleep(THROTTLE_TIME * 10)
            
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
        self.hashes[hash] = self.name
        with open(join(self.dst, self.name), 'wb') as file_out:
            file_out.write(media)
        self.status = self.FINISHED

    # Print the information for this DownloadThread
    def print_status(self):
        if(self.status == self.STANDBY): status_char = ' S '
        elif(self.status == self.TIMEOUT): status_char = ' T '
        elif(self.status == self.CONNECTING): status_char = '1/4'
        elif(self.status == self.HASHING): status_char = '2/4'
        elif(self.status == self.DOWNLOADING): status_char = '3/4'
        elif(self.status == self.WRITING): status_char = '4/4'
        elif(self.status == self.FINISHED): status_char = ' ✓ '
        elif(self.status == self.ERROR): status_char = ' E '
        else: status_char = ' ? '
        stdout.write(f'[{status_char} - {self.downloaded / self.total_size:6.1%}] {self.url}\n')


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
@param algo - Function for the hashing algorithm from hashlib (default=md5).
@param hashes - Dictionary of seen hashes. Index is hash, value is original media name.
@param short - If true, only the first 64 kilobytes of the file will be hashed.
@param recurse - If true, subdirectories are traversed. If false, subdirectories are skipped.
@return a dictionary indexed by hash value storing the file name.
"""
def compute_file_hashes(dir, exts=None, algo=hashlib.md5, hashes={}, short=False, recurse=False):
    exts_clean = clean_exts(exts)
    for name in listdir(dir):
        full_name = join(dir, name)
        ext = name.split('.')[-1]

        if(isfile(full_name) and (exts_clean is None or ext in exts_clean)):
            stdout.write(f'[compute_file_hashes] INFO: Hashing ({full_name})... ')
            stdout.flush()
            with open(full_name, 'rb') as file_in:
                file_hash = algo()
                if short:
                    chunk = file_in.read(1024 * 64)
                    file_hash.update(chunk)
                else:
                    while True:
                        chunk = file_in.read(1024 * 1024 * 128)
                        if not chunk:
                            break
                        file_hash.update(chunk)
                file_hash = file_hash.hexdigest()

            if(file_hash not in hashes):
                hashes[file_hash] = full_name
                stdout.write(f'unique hash ({len(hashes)}).\n')
            else:
                stdout.write(f'duplicate of ({hashes[file_hash]}).\n')

        elif(isdir(full_name) and recurse):
            hashes = compute_file_hashes(full_name, exts=exts, algo=algo, hashes=hashes, recurse=True)

    return hashes


"""
Download media from a list of URLs if the hash has not been seen before.
@param dir - Destination directory for the download.
@param urls - List of URLs to query.
@param algo - Function for the hashing algorithm from hashlib (default=md5).
@param hashes - Dictionary of seen hashes. Index is hash, value is original media name.
@return the new dictionary of hashes.
"""
def download_urls(dir, urls, algo=hashlib.md5, hashes={}):
    for url in urls:
        stdout.write(f'[download_urls] INFO: Media from {url} :\t\t')
        stdout.flush()
        ext = url.split('.')[-1]
        name = url.split('/')[-1].split('.')[0]
        try:
            media = None
            while(True):
                res = requests.get(url)
                if(res.status_code == TOO_MANY_REQUESTS):
                    stdout.write(f'Too many requests, delaying {THROTTLE_TIME} seconds.\n')
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
            stdout.write(f'Downloading as {hash}.{ext}\n')
            stdout.flush()
            with open(join(dir, f'{hash}.{ext}'), 'wb') as file_out:
                file_out.write(media)
        else:
            stdout.write(f'Duplicate media of {hashes[hash]}\n')
    return hashes


"""
Orchestrate multi-threaded downloads.
@param urls - Dictionary of named URLs to download.
@param pics_dst - Destination for pictures.
@param vids_dst - Destination for videos.
@param algo - Function for the hashing algorithm from hashlib (default=md5).
@param hashes - Dictionary of hashes for existing downloaded media.
@return the updated hash table.
"""
def multithread_download_urls(urls, pics_dst, vids_dst, algo=hashlib.md5, hashes={}):
    multithread_download_urls_special(DownloadThread, urls, pics_dst, vids_dst, algo=algo, hashes=hashes)


"""
Orchestrate multi-threaded downloads.
@param Dtsc - DownloadThread subclass to handle downloading.
@param urls - Dictionary of named URLs to download.
@param pics_dst - Destination for pictures.
@param vids_dst - Destination for videos.
@param algo - Function for the hashing algorithm from hashlib (default=md5).
@param hashes - Dictionary of hashes for existing downloaded media.
@return the updated hash table.
"""
def multithread_download_urls_special(Dtsc, urls, pics_dst, vids_dst, algo=hashlib.md5, hashes={}):
    # Confirm that Dtsc is a subclass of DownloadThread (or the same class)
    if(not issubclass(Dtsc, DownloadThread)):
        return hashes
        
    # Print the initial status box
    dst = commonpath([pics_dst, vids_dst])
    msg = f'Successfully downloaded media from 0/{len(urls)} URLs to {dst}'
    print(f'.{"="*(len(msg)+2)}.')
    print(f'| {msg} |')
    print(f'\'{"="*(len(msg)+2)}\'')

    # Sort the name of URLs to downloaded newest-to-oldest
    names = sorted(list(urls.keys()), reverse=True)
    
    # Loop until completing processing of all urls
    pos = 0
    prevThreadCnt = 0
    download_threads = []
    while(pos < len(urls)):
        # Get the number of threads
        download_threads = list(filter(lambda t: isinstance(t, Dtsc), enumerate()))

        # Start new threads up to the maximum number of threads
        while(len(download_threads) < MAX_THREADS):
            thread_url = urls[names[pos]]
            thread_ext = thread_url.split('.')[-1]
            thread_dst = pics_dst if thread_ext in IMG_EXTS else vids_dst
            thread = Dtsc(names[pos], thread_url, thread_dst, algo=algo, hashes=hashes);
            thread.start()
            
            pos = pos + 1
            download_threads.append(thread)
            if(pos >= len(urls)):
                break
            
        # Clear the previous status box and status of each thread
        for _ in range(0, prevThreadCnt+3): stdout.write('\033[F')
        
        # Print the status box
        howManyCompleted = max(0, pos-MAX_THREADS)
        msg = f'Successfully downloaded media from {howManyCompleted}/{len(urls)} URLs to {dst}'
        print(f'.{"="*(len(msg)+2)}.')
        print(f'| {msg} |')
        print(f'\'{"="*(len(msg)+2)}\'')
        
        # Print the status of each thread
        for thread in download_threads:
            try: thread.print_status()
            except: pass
            
        # Update the number of status messages that were printed and sleep
        prevThreadCnt = len(download_threads)
        time.sleep(1)
        
    # Wait for the final threads to complete
    remaining = list(filter(lambda t: isinstance(t, Dtsc), enumerate()))
    while(len(remaining) > 0):
        # Clear the previous status box and status of each thread
        for _ in range(0, prevThreadCnt+3): stdout.write('\033[F')
        
        # Print the status box
        msg = f'Successfully downloaded media from {pos-len(remaining)}/{len(urls)} URLs to {dst}'
        print(f'.{"="*(len(msg)+2)}.')
        print(f'| {msg} |')
        print(f'\'{"="*(len(msg)+2)}\'')
        
        # Print the status of each thread
        for thread in download_threads:
            try: thread.print_status()
            except: pass
            
        # Update the number of status messages that were printed and sleep
        time.sleep(1)
        remaining = list(filter(lambda t: isinstance(t, Dtsc), enumerate()))
    
    # Clear the previous status box and status of each thread
    for _ in range(0, len(download_threads)+3): stdout.write('\033[F')
    
    # Print the final status box
    msg = f'Successfully downloaded media from {pos-len(remaining)}/{len(urls)} URLs to {dst}'
    print(f'.{"="*(len(msg)+2)}.')
    print(f'| {msg} |')
    print(f'\'{"="*(len(msg)+2)}\'')
    
    # Print the final thread status
    for thread in download_threads:
        thread.status = Dtsc.FINISHED
        try: thread.print_status()
        except: pass
    
    return hashes
