import hashlib
import requests
from os import listdir
from os.path import join, isfile, isdir
from sys import stdout


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
@param exts - List of extensions.
@param algo - Function for the hashing algorithm.
@param hashes - Map of seen hashes. Index is hash, value is original media name.
@return a map indexed by hash value storing the file name.
"""
def compute_file_hashes(dir, exts=None, algo=hashlib.md5, hashes={}, recurse=False):
    exts_clean = clean_exts(exts)
    for name in listdir(dir):
        full_name = join(dir, name)
        ext = name.split('.')[-1]
        if(isfile(full_name) and (clean_exts is None or ext in exts_clean)):
            with open(full_name, 'rb') as file_in:
                file_bytes = file_in.read()
                file_hash = algo(file_bytes).hexdigest()
            if(file_hash not in hashes):
                hashes[file_hash] = name
        elif(recurse and isdir(full_name)):
            hashes = compute_file_hashes(full_name, exts=exts, algo=algo, hashes=hashes, recurse=True)
    return hashes


"""
Download media from a list of URLs if the hash has not been seen before.
@param dir - Destination directory for the download.
@param urls - List of URLs to query.
@param algo - Algorithm used by the map of hashes.
@param hashes - Map of seen hashes. Index is hash, value is original media name.
@return the new map of hashes.
"""
def download_urls(dir, urls, algo=hashlib.md5, hashes={}):
    for url in urls:
        stdout.write('[download_urls] INFO: Media from %s:\t\t' % (url))
        ext = url.split('.')[-1]
        name = url.split('/')[-1]
        img = requests.get(url).content
        hash = algo(img).hexdigest()
        if(hash not in hashes):
            hashes[hash] = name
            stdout.write('Downloading as %s\n' % (hash + '.' + ext))
            with open(join(dir, hash + '.' + ext), 'wb') as file_out:
                file_out.write(img)
        else:
            stdout.write('Duplicate image of %s\n' % hashes[hash])
    return hashes
