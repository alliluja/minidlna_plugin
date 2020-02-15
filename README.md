# The miniDLNA plugin

  minidlna daemon supports showing previews for movies, but it does not generate them.
  Therefore, the plugin gets an image from the movie name and places it in the folder
  with previews for movies. The plugin also adds information about this image to the
  minidlna daemon database

## dependencies

* python3
* pip3
* requests
* sqlite3
  may be more :), see sources


### First of all you must register in [tmdb](https://www.themoviedb.org/) and take api key, and put it in config.json to work with this service.

## Comments
  You also need to set read and write permissions for _ALL users_ for files and folders:
* the minidlna database file (`files.db`), by default `db_dir=/var/cache/minidlna`,
NOTE! Uncomment this line in `minidlna.conf`
* The folders where the image files will be placed, `/var/cache/minidlna/art_cache`.
* File `main.py` must be executable.
* Folder, for movies.
* To automate the process i write in transmission-daemon settings.json: `script-torrent-done-filename": "path_to/dlna_plugin/main.py"`,
* main.py will execute by user transmission-daemon

