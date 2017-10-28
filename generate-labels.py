#!/usr/bin/python

## a simple script that reads Discogs CSV collection dumps
## and generates labels with:
## * QR code for the Discogs URL
## * name of the artist
## * name of the title
##
## I only have A4 sheets with 8 rows of 3 labels each (24 per A4 sheet)
## so some settings are hardcoded
##
## Licensed under the terms of the General Public License version 3
##
## SPDX-License-Identifier: GPL-3.0
##
## Copyright 2017 - Armijn Hemel
##

import csv, sys, os, argparse, ConfigParser

## load a lot of reportlab stuff
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import Image, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode.qr import QrCodeWidget

def main(argv):
	parser = argparse.ArgumentParser()

	parser.add_argument("-c", "--config", action="store", dest="cfg", help="path to configuration file", metavar="FILE")
	parser.add_argument("-f", "--file", action="store", dest="csvfile", help="path to CSV file", metavar="FILE")
	parser.add_argument("-o", "--out", action="store", dest="outfile", help="path to output PDF file", metavar="FILE")
	parser.add_argument("-p", "--profile", action="store", dest="profile", help="name of label profile", metavar="PROFILE")
	args = parser.parse_args()

	## sanity checks for the configuration file
	if args.cfg == None:
		parser.error("Configuration file missing")

	if not os.path.exists(args.cfg):
		parser.error("Configuration file does not exist")

	## sanity checks for the CSV file
	if args.csvfile == None:
		parser.error("CSV file missing")

	if not os.path.exists(args.csvfile):
		parser.error("CSV file does not exist")

	## sanity checks for the output file
	if args.outfile == None:
		parser.error("name of output file missing")

	## sanity checks for the profile
	if args.profile == None:
		parser.error("name of profile missing")

	## read the configuration file
	config = ConfigParser.ConfigParser()

	try:
		configfile = open(args.cfg, 'r')
	except:
		configfile.close()
		parser.error("Configuration file not readable")
	config.readfp(configfile)
	configfile.close()

	## check wheher or not the name of the profile provided
	## exists in the configuration file
	if not args.profile in config.sections():
		print >>sys.stderr, "ERROR: profile name not found in configuration file, exiting"
		sys.exit(1)

	## store profile
	profile = {}

	reverse_columns = False

	for section in config.sections():
		if section == "general":
			try:
				config.get(section, "type")
			except:
				break
			try:
				tmpval = config.get(section, "reverse-columns")
				if tmpval == 'yes':
					reverse_columns = True
			except:
				pass
		elif section == args.profile:
			try:
				config.get(section, "type")
			except:
				break
			## first check if there is a page size
			try:
				pagesize = config.get(section, 'pagesize')
				if pagesize == 'A4':
					profile['pagesize'] = A4
			except:
				pass

			if not 'pagesize' in profile:
				try:
					profile['height'] = int(config.get(section, 'height'))
				except:
					break
				try:
					profile['width'] = int(config.get(section, 'width'))
				except:
					break
			try:
				profile['rows'] = int(config.get(section, 'rows'))
			except:
				## default: 1 row
				profile['rows'] = 1
			try:
				profile['columns'] = int(config.get(section, 'columns'))
			except:
				## default: 1 column
				profile['columns'] = 1
			try:
				## default: points
				unit = config.get(section, 'unit')
				if unit == 'mm':
					profile['unit'] = mm
			except:
				pass
	if profile == {}:
		print >>sys.stderr, "ERROR: empty profile, exiting"
		sys.exit(1)

	## a list to store the CSV values
	csvlines = []

	try:
		csvfile = open(args.csvfile, 'rb')
	except:
		print >>sys.stderr, "ERROR: can't open CSV file, exiting"
		sys.exit(1)
	try:
		discogs_csv = csv.reader(csvfile, dialect='excel')
	except:
		csvfile.close()
		print >>sys.stderr, "ERROR: file not CSV file, exiting"
		sys.exit(1)

	## now read the CSV entries and only store the actual entries,
	## not the header
	firstline = True
	for r in discogs_csv:
		if firstline:
			## first line is not needed
			firstline = False
			continue
		csvlines.append(r)
	csvfile.close()

	## only process if there actually were lines in the CSV
	if len(csvlines) == 0:
		sys.exit(0)

	if not 'pagesize' in profile:
		if 'unit' in profile:
			profile['pagesize'] = (profile['width']*profile['unit'],profile['height']*profile['unit'])
		else:
			profile['pagesize'] = (profile['width'], profile['height'])

	## create a document for reportlab
	## set the margins as close to the edge as possible. I needed an ugly hack with the topMargin value
	qrdoc = SimpleDocTemplate(args.outfile, leftMargin=0, rightMargin=0, topMargin=-4*mm, bottomMargin=0, pagesize=profile['pagesize'], allow_splitting=0)

	## create a table for reportlab
	## each label basically consists of two parts:
	## * text
	## * QR code
	## These are them combined.
	## The default ordering is: text left, image right, unless the columns are reversed

	# container for the 'Flowable' objects
	elements = []
 
	data = []

	styleSheet = getSampleStyleSheet()
	qrTableStyle = styleSheet['BodyText']
	qrTableStyle.leading = 10

	cleanup = True

	## Discogs collection export looks like this:
	## ['Catalog#', 'Artist', 'Title', 'Label', 'Format', 'Rating', 'Released', 'release_id', 'CollectionFolder', 'Date Added', 'Collection Media Condition', 'Collection Sleeve Condition', 'Collection Notes']
	counter = 1
	tmpqueue = []
	for r in csvlines:
		(catalogue_number, artist, title, label, disc_format, rating, released, release_id, collectionfolder, date_added, media_condition, sleeve_condition, notes) = r

		## now generate a QR image with a valid discogs URL
		qrurl = QrCodeWidget('https://www.discogs.com/release/%s' % str(release_id))
		qrurl = QrCodeWidget('https://www.discogs.com/release/%s' % str(release_id))

		## set the dimensions for the Drawing
		qrimage = Drawing(35*mm,35*mm)

		## add the QR code to the drawing
		qrimage.add(qrurl)
    
		#qrhtml = Paragraph("<b>Artist:</b> %s<br /><b>Title:</b> %s<br /><b>Catalogue No.:</b> %s" % (artist, title, catalogue_number), styleSheet["BodyText"])
		#qrhtml = Paragraph("<b>Artist:</b> %s<br /><b>Title:</b> %s<br /><b>Price:</b> &euro; 50" % (artist, title), styleSheet["BodyText"])
		qrhtml = Paragraph("<b>Artist:</b> %s<br /><b>Title:</b> %s" % (artist, title), styleSheet["BodyText"])
		if reverse_columns:
			tmpqueue.append(qrimage)
			tmpqueue.append(qrhtml)
		else:
			tmpqueue.append(qrhtml)
			tmpqueue.append(qrimage)
		if counter%profile['columns'] == 0:
			data.append(tmpqueue)
			tmpqueue = []
		counter += 1

	## add any data that hasn't been added yet
	if tmpqueue != []:
		data.append(tmpqueue)
        
	t=Table(data, colWidths=35*mm, rowHeights=37*mm, style=[
                    ('TOPMARGIN',(0,0), (-1, -1), 0),
                    ('BOTTOMMARGIN',(0,0), (-1, -1), 0),
                    ('LEFTMARGIN',(0,0), (-1, -1), 0),
                    ('RIGHTMARGIN',(0,0), (-1, -1), 0),
                    ('VALIGN',(0,0), (-1, -1), 'MIDDLE'),
                    ('ALIGN',(0,0), (-1, -1), 'CENTER'),
                    ## set INNERGRID for debugging
                    #('INNERGRID', (0,0), (-1,-1), 0.25, colors.black)
                    ])
	elements.append(t)

	## finally generate the document with all the QR codes
	qrdoc.build(elements)

if __name__ == "__main__":
	main(sys.argv)
