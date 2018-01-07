### begin config

#
# testMode: Logs out as if moving/renaming/removing files but does not actually make changes
testMode = False

#
# debugMode: Writes search and result details (and retry attempts) out to the console
debugMode = False

#
# strictMode: Uses intelligent string comparison to ensure titles are a good match
# Good if your titles are accurate, may miss some matches if they are not
# If you disable this, you may find some innaccurate matches
strictMode = True 

#
# minTitleSimilarity: Min % similarity (0.0 - 1.0) that a matched title should be to the original
# The lower this value, the more likely you are to find incorredt matches
minTitleSimilarity = 0.5

#
# maxYearDifference: Number of years apart to still consider a valid match
maxYearDifference = 1 

#
# minPopularity: Min popularity ranking on TMDb to consider a valid match
# Popular titles generally rank above 10
minPopularity = 2

#
# safeCopy: Copies files to the destination, verifies, and deletes originals
# This is the default behavior when source and destination are on different partitions (or network)
safeCopy = False 

#
# limit: Limits number of files copied; useful for large rename jobs where error chance is high
limit = 0

#
# sourceDirs: An array of folders to search for films to rename.
# For Windows paths, make sure you escape the path with a \, for example: r"D:\\Downloads"
# For *nix, use standard path, for example: r"/path/to/folder"
# Use the 'u' prefix to ensure unicode chars are read properly
sourceDirs = [u"/Volumes/Films/_Rename"]

#
# destDir: Destination folder, e.g. r"/Volumes/Films/_New"
# Works best if source and destination are on the same partition, otherwise things are... slow
destDir = u'/Volumes/Films/HD'

#
# renamePattern: Permitted rename pattern objects: {title}, {title-the}, {year}, {quality}, {edition}, {media}
# for using other characters with pattern objects, place them inside {} e.g. { - edition}
# for escaping templating characters, use \{ \}, e.g. {|{edition\}}
renamePattern = r"{title} {[edition]} {(year)} {media-}{quality}" 

#
# Array of words to always lowercase (if not at start of name) or always uppercase
alwaysLowercase = ['a', 'an', 'of', 'the', 'is', 'on', 'at', 'in', 'and', 'to'] # whole words to remain lowercase if not start of string
alwaysUppercase = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'TRON'] # whole words to remain uppercase

#
# minSizeInMiB: Ignore files/folders smaller than this
# Change to 0 for testing with empty .txt files ^_^
minSizeInMiB = 200

# useFolders: sorts files into identically named subfolders
useFolders = True

# checkForDuplicates: Do not check for duplicate files at the destination
# If enabled, duplicates are considered based on matching titles and years, irrespective of naming convention
checkForDuplicates = True

#
# specialEditionStrings: Strings that are likely to match a special edition, and a cleaned mapping for each
# The first complete match will be used, so order them appropriately, e.g. place "extended.edition" before "extended"
# Always separate with '.' because these will be compiled into regular expressions
specialEditionStrings = [
    ["extended.directors.cut", "Extended Director's Cut"],
    ["extended.remastered", "Extended Remastered"],
    ["extended.edition", "Extended Edition"],
    ["directors.cut.remastered", "Director's Cut Remastered"],
    ["25th.anniversary.edition", "25th Anniversary Edition"],
    ["25th.anniversary.ed", "25th Anniversary Edition"],
    ["25th.anniversary", "25th Anniversary"],
    ["dc.remastered", "Director's Cut Remastered"],
    ["se.remastered", "Special Edition Remastered"],
    ["unrated.directors.cut", "Unrated Director's Cut"],
    ["directors.cut", "Director's Cut"],
    ["ultimate.expanded.edition", "Ultimate Expanded Edition"],
    ["ultimate.edition", "Ultimate Edition"],
    ["expanded.edition", "Expanded Edition"],
    ["unrated.remastered", "Unrated Remastered"],
    ["theatrical.remastered", "Theatrical Remastered"],
    ["alternate.ending", "Alternate Ending"],
    ["special.edition", "Special Edition"],
    ["remastered", "Remastered"],
    ["extended", "Extended"],
    ["uncut", "Uncut"],
    ["unrated", "Unrated"],
    ["limited", "Limited"],
    ["theatrical", "Theatrical"],
    ["noir", "Noir"]
]

#
# stripPrefixes: Sometimes films are prefixed with tags; remove these when looking up
stripPrefixes = ['ams-', 'flame-', 'blow-', 'geckos-', 'rep-', 'pfa-', 'snow-', 'refined-', 'japhson-', 'sector7-']

#
# restrictedChars: Strip all instances of these strings from files before writing to filesystem (case insensitive)
restrictedChars = [':/\\']

#
# ignoreStrings: Ignore files with any of these strings (case insensitive)
ignoreStrings = ['sample']

#
# videoFileExts: Array of valid video file extensions
videoFileExts = ['.mkv', '.m4v', '.mp4', '.avi']

#
# extraExts: Array of additional file types to move and rename with films, e.g. srt, nfo
extraExts = ['.srt']

#
# cleanUnwantedFiles: Remove unwanted files from folders
# (Includes videoFileExts, extraExts, and ignoreStrings)
cleanUnwantedFiles = True

#
# cleanUpSource: Removes all files/folders left behind after the move is complete
cleanUpSource = True


#
# TMDb config; use TMDb API validate and correct film titles
# You will need an API key to The Movie Database to access the API. To obtain a key, follow these steps:
#  1. Register for and verify an account.
#  2. Select the API section on left side of your account page.
#  3. Click on the link to generate a new API key and copy it here.
TMDb = {
    "enabled": True,
    "key": ""
}

#
# Plex config
plex = {
    "enabled": True,
    "baseurl": "http://localhost:32400", # Plex url including : port
    "token": "", # See https://support.plex.tv/hc/en-us/articles/204059436-Finding-an-authentication-token-X-Plex-Token
    "sections": ["Films"] # List of Plex sections to update
}

#
# Pushover config; receive notifications when moves are complete
pushover = {
    "enabled": False,
    "key": ""
}

#
# Path to write log; make sure to include trailing slash (\\ on windows or / on *nix)
logPath = "./"

### endconfig