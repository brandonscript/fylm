#!/usr/bin/env python
###################################################

from FilmRenamerConfig import *
import re
import sys
import os, os.path
import shutil
import urllib
from time import sleep
import logging
import time
import datetime
import inspect
import requests

logging.basicConfig(filename=logPath + 'FilmRenamer.log',level=logging.INFO)

if (os.name == "nt"):
	slash = "\\"
else:
	slash = "/"

divider = "---------------------------------------------------"
hash = "******************************************************"
line = " "

sourcePath = re.sub("(\\\\|/)$", "", sourcePath)
destPath = re.sub("(\\\\|/)$", "", destPath)
timestamp = time.ctime()
movieList = ''

#folder = "FernGully The Last Rainforest 1992 1080p BluRay x264 HD4U"
#file = "ferngully.the.last.rainforest.1992.1080-hd4u.mkv"

def output(text):
	print(text)
	logging.info(re.sub("\n", "\nINFO:root:", text))

def validate(file, folder):
    #check folder
	if (re.search(".+(108|72)0p?.+", folder) and re.search(".+(\s|\.)(19|20)[0-9][0-9](.*|(?!p))", folder)):
		#appears to have a valid quality and date, return folder
		return folder

	#check filename
	elif (re.search(".+(108|72)0p?.+", file) and re.search(".+(\s|\.)(19|20)[0-9][0-9](.*|(?!p))", file)):
		#appears to have a valid date and quality, return file
		return file

	else:
		#return None, which will fail the script
		return None


#title case corrections
def titleCase(s, exceptions):
	word_list = re.split(' ', s)	#re.split behaves as expected
	final = [word_list[0].capitalize()]
	for word in word_list[1:]:
		final.append(word.lower() in exceptions and word.lower() or word.upper() in roman and word.upper() or word.capitalize())
	return " ".join(final)

#rename and join each chunk of the file
def rename(file_string, file_name):
	elements = []
	spl = re.split("(\%\w+\%)", renamePattern)
	for s in spl:
		if s:
			elements.append(getValue(s, file_string, file_name))
	renamed = ''.join(elements)
	return renamed

#strip the applicable value out of the string chunk and return it
def getValue(s, file_string, file_name):
	f = re.sub("\.", " ", file_string)
	s = re.sub("\.", "", s)
	#print(s)
	if re.search("\%\w+\%", s):
		if re.search("titlethe", s):
			s = titleCase(f, articles)
			s = re.sub("\s(19|20)[0-9][0-9](.*|(?!p))$", "", s)
			s = re.sub("\s?(108|72)0p\s?", "", s, re.I)
			if re.search("^The\s", s):
				s = re.sub("^The\s", "", s) + ", The"
		elif re.search("thetitle", s):
			#do thetitle stuff
			s = titleCase(f, articles)
			s = re.sub("\s(19|20)[0-9][0-9](.*|(?!p))$", "", s)
			s = re.sub("\s?(108|720)p\s?", " ", s, re.I)
		elif re.search("quality", s):
			if re.search(".*1080p?.*", f, re.I):
				s = "1080p"
			elif re.search(".*720p?.*", f, re.I):
				s = "720p"
		elif re.search("year", s):
			p = re.compile(".+\s(?P<year>(19|20)[0-9][0-9])(.*|(?!p))")
			if p is not None:
				m = p.match(f)
				s = m.group('year')
		elif re.search("ext", s):
			s = getExt(file_name)
	return re.sub("[ ]{2,}", " ", s)

def sizeInStr(path):
	if os.path.exists(path):
		b = os.path.getsize(path)
		kb = round(b / 1024, 10)
		mb = round(kb / 1024, 10)
		gb = round(mb / 1024, 10)

		if gb >= 1:
			return str(round(gb, 2)) + " GiB"
		elif mb >= 1:
			return str(round(mb, 2)) + " MiB"
		elif kb >= 1:
			return str(round(kb, 2)) + " KiB"
		else:
			return str(b) + " B"
	else:
		return "X GiB"

def sizeInGiB(path):
	return round(os.path.getsize(path) / 1024 / 1024 / 1024, 2)

def getExt(string):
	fileName, fileExtension = os.path.splitext(string)
	return fileExtension

def moveFile(src, dst, srcFolder):
	srcSize = os.path.getsize(src)
	if (safeCopy):
		with file(src, 'rb') as fsrc:
			with file(dst, 'w+b') as fdst:
				shutil.copyfileobj(fsrc, fdst, 10485760)
				shutil.copystat(src, dst)
	else:
		shutil.move(src, dst)
	try:
		with open(dst): pass
		if os.path.exists(dst):
			if srcSize == os.path.getsize(dst):
				if os.path.dirname(src) == sourcePath:
					return "\t==> Not removing folder as it matches sourcePath variable!"
				else:
					shutil.rmtree(parentfolderpath)
					return "\tFile moved successfully\n\tRemoved " + sourcePath + "/" + srcFolder
			else:
				return "\t==> Destination file size does not match the original file size\n==> An error may have occurred in the file move operation"
		else:
			return "\tFile move operation failed"
	except IOError:
		return "\tFile move operation failed"

def notifyProwl(moviename, apikey):
	#Clean up the title so it's URL encoded
	moviecleaned = urllib.quote_plus(moviename)
	# Send our Prowl Notification
	url = 'https://api.prowlapp.com/publicapi/add?' + 'apikey=' + apikey + '&application=SABnzbd/Plex&event=Film%20Processed&description=' + moviecleaned + "%20has%20been%20renamed%20and%20moved."
	u = urllib.urlopen(url)
	#u is a file-like object
	data = u.read()

def notifyPushover(moviename, apikey):
	moviecleaned = urllib.quote_plus(moviename)
	url = 'https://api.pushover.net/1/messages.json?token=aXGBsCSKjLpwFHLcT62Qhtfc2oE6z2&user=' + apikey + '&title=Download Finished&message=' + moviecleaned
	r = requests.post(url)
	data = r.json()

def refreshPlex():
	# Refresh our Plex Library: http://kodiak:32400/web/index.html#!/servers/03162ca01e22e3b0f73ed86e07e1bb71ac6364ab/sections/3
	#url = plexServer + ':' + plexServerPort + '/web/index.html#!/servers/' + plexKey + '/sections/' + movieCat + '/refresh'
	#u = urllib.urlopen(url)
	#data = u.read()

	#This is for windows only
	os.popen("C:\Program Files (x86)\Plex\Plex Media Server\Plex Media Server.exe --scan --refresh --section " + movieCat)

### Stuff happens here

output("")
output(hash)
output(inspect.getfile(inspect.currentframe()) + " initialized on " + timestamp)
output(hash)

print(sourcePath)

if not os.path.exists(sourcePath):
	output("\nError: 'sourcePath' does not exist; check folder path in FilmRenamerConfig.py\n")
elif not os.path.exists(destPath):
	output("\nError: 'destPath' does not exist; check folder path in FilmRenamerConfig.py\n")	
else:
	output("Scanning subfolders and files in " + sourcePath)
	output("Selected destination folder " + destPath)
	print("Please wait...")
	output('')

	directories = [sourcePath]

	while len(directories)>0:
		directory = directories.pop()

		try:
			for name in os.listdir(directory):
				fullpath = os.path.join(directory,name)
				fileonly = os.path.basename(fullpath)

				if os.path.isfile(fullpath):   # That's a file. Do something with it.
					if (getExt(fullpath) == ".mkv"):
						output("Checking " + fullpath)
					parentfolderpath = os.path.abspath(os.path.join(fullpath, os.path.pardir))
					parentfolder = re.sub(".*(\/|\\\\)", "", parentfolderpath)
					
					# Check if the file ends in .mkv. If it doesn't, we don't care.
					if (getExt(fullpath) == ".mkv"):
						if (re.search("_UNPACK_", fullpath)):
							output(divider)
							output("\tIgnoring " + fileonly + ": file is currently unpacking")
							output(line)
						elif (re.search("_FAILED_", fullpath)):
							output(divider)
							output("\tIgnoring " + fileonly + ": archive extraction appears to have failed")
							output(line)
						elif (re.search("sample", fullpath, re.I)):
							output(divider)
							output("\tIgnoring " + fileonly + ": file appears to be sample")
							output(line)
						elif (re.search(r"s\d{1,2}e\d{1,2}", fullpath, re.I)):
							output(divider)
							output("\tIgnoring " + fileonly + ": file appears to be a TV show")
							output(line)
						# Check and validate the file according to our detection parameters
						elif (sizeInGiB(fullpath) < minSizeInGiB):
							output(divider)
							output("\tIgnoring " + fileonly + ": file size (" + sizeInStr(fullpath) + ") is less than minimum size specified (" + str(minSizeInGiB) + ".0 GiB)")
							output(line)
						elif validate(fileonly, parentfolder) is not None:
							newfilename = rename(validate(fileonly, parentfolder), fileonly)
							size = sizeInStr(fullpath)
							newpath = destPath + slash + newfilename
							output(divider)
							output("\tRenaming " + fileonly + " (" + size + ") => " + newfilename)
							output("\tAttempting to move file...")
							try:
								if os.path.isfile(newpath):
									output("\t==> A file with the same name exists; aborting")
								else:
									if (testMode):
										output("\tTest mode - not actually renaming or moving file")
									else:
										output(moveFile(fullpath, newpath, parentfolder))
										#move was successful, notify
										if os.path.exists(newpath):

											output("\tFile moved successfully")
											#refreshPlex() #ignoring plex for now since it's not installed
											if enablePushover:
											# notifyProwl(newfilename + " (" + size + ")", prowlKey)
												notifyPushover(newfilename + " (" + size + ")", pushoverKey)
											if enablePlex:
												refreshPlex()

							except Exception, e:
								output("\t*** An error occurred when attempting to move " + newfilename)
								print(e)
								output("\t*** Details: " + str(e))
							output(line)						
						else:
							output(divider)
							output("\tIgnoring " + fileonly + ": could not interpret file/folder name (file or folder must have valid date and quality)")
							output(line)

				elif os.path.isdir(fullpath):
					directories.append(fullpath)
		except Exception:
			pass

	print("FilmRenamer script completed successfully.") #not using output here as this doesn't need to be in log
	sleep(10) #sleeps for 10 seconds to review console output
