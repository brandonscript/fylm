### begin config

# Logs out as if moving/renamed files but does not actually affect them
testMode = False
safeCopy = False # uses shutil.copy regardless of whether src and dst are on the same partition

# For Windows paths, make sure you escape the path, for example: "D:\\Downloads"
# For *nix, enter standard path, for example: "/path/to/folder"

sourcePaths = [r"/Users/brandon/Usenet/complete", r"/Volumes/5 TB - 01/_Films/_Rename"]

# destPath = r"/Volumes/X/Films/_New"
destPath = r"/Volumes/5 TB - 01/_Films"

# renamePattern: permitted rename pattern objects: %titlethe%, %thetitle%, %year%, %quality%, %ext%
renamePattern = "%titlethe% %quality% (%year%).%ext%" 
articles = ['a', 'an', 'of', 'the', 'is', 'on', 'at', 'in', 'and', 'to'] # words to remain lowercase
roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII'] # words to remain uppercase

#
# minSizeInGiB: change this to 0 for testing with .txt files ^_^
minSizeInGiB = 2
#
# Define your INTERNAL address of your Plex Server:
#plexServer = "http://172.16.99.31"
plexServer = "http://127.0.0.1"
plexServerPort = "32400"
#
# movieCat: Define the 'Movie' category ID
# Lookup Category: http://192.168.1.100:32400/web, click category, save the API key from the URL, then the number after "/section"
enablePlex = False
plexKey = "03162ca01e22e3b0f73ed86e07e1bb71ac6364ab"
movieCat = "3"
#
# prowlKey: Prowl API Key
#prowlKey = "0c74cd01d764dd6c496b19d2dc94b05278e96cec" #Jeremy
#prowlKey = "d03e78c79928696abee52396282c540cb0b32487" #Brandon
enablePushover = False
pushoverKey = "uFX5ZFkRPoyG72DYcoV1dBoEwT7t7i"
#
#
# Log path - make sure to include trailing slash (\\ on windows or / on *NIX)
logPath = "/Users/brandon/Scripts/FilmRenamer/"
#
### endconfig