from os import listdir
from os.path import join, isfile, isdir
from sys import stdout
import hashlib
import requests
import time


NOT_FOUND = 404
TOO_MANY_REQUESTS = 429
THROTTLE_TIME = 30


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
            stdout.write('[compute_file_hashes] INFO Hashing (%s)... ' % (full_name))
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
                    stdout.write('Too many requests, delaying %d seconds. This usually happens while downloading multiple LARGE files, so have patience.\n' % (THROTTLE_TIME))
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
