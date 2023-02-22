# Scraping Utils
A suite of utility functions that are used in my scraping scripts.

## Functions
#### `clean_exts(exts)`
```
Clean a list of extensions to not include a leading dot.
@param exts - Original list of extensions.
@return a list of cleaned extensions.
```

#### `compute_file_hashes(dir, exts=None, algo=hashlib.md5, hashes={}, recurse=False)`
```
Compute the hashes of files with specified extensions using a specified algorithm function.
@param dir - String of directory to process.
@param exts - List of extensions. If None, then all extensions are queried.
@param algo - Function for the hashing algorithm from hashlib.
@param hashes - Dictionary of seen hashes. Index is hash, value is original media name.
@param recurse - If true, subdirectories are traversed. If false, subdirectories are skipped.
@return a dictionary indexed by hash value storing the file name.
```

#### `download_urls(dir, urls, algo=hashlib.md5, hashes={})`
```
Download media from a list of URLs if the hash has not been seen before.
@param dir - Destination directory for the download.
@param urls - List of URLs to query.
@param algo - Algorithm from hashlib used by the dictionary of hashes.
@param hashes - Dictionary of seen hashes. Index is hash, value is original media name.
@return the new dictionary of hashes.
```

## How to Include in Project
1. To include scrape_utils in your code, copy all contents from this repository into a folder of any name, e.g. `foobar`.
2. Move the folder to same directory as the Python file that will use the utility functions, e.g. `/my/python/project/foobar`.
3. Import `scraping_utils` to the Python file, e.g. `from foobar.scraping_utils import *`.


## Disclaimer
This repository is for personal use. There is no guarantee that the function signatures used in the current version will be compatible with future versions. Use at your own risk.
