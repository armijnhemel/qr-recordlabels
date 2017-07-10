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

    ## TODO: use a configuration file for more configurability
    #parser.add_argument("-c", "--config", action="store", dest="cfg", help="path to configuration file", metavar="FILE")
    parser.add_argument("-f", "--file", action="store", dest="csvfile", help="path to CSV file", metavar="FILE")
    parser.add_argument("-o", "--out", action="store", dest="outfile", help="path to output PDF file", metavar="FILE")
    args = parser.parse_args()

    ## sanity checks for the configuration file
    #if args.cfg == None:
    #    parser.error("Configuration file missing")

    #if not os.path.exists(args.cfg):
    #    parser.error("Configuration file does not exist")

    ## sanity checks for the CSV file
    if args.csvfile == None:
        parser.error("CSV file missing")

    if not os.path.exists(args.csvfile):
        parser.error("CSV file does not exist")

    ## sanity checks for the output file
    if args.outfile == None:
        parser.error("name of output file missing")

    #config = ConfigParser.ConfigParser()

    #try:
    #    configfile = open(args.cfg, 'r')
    #except:
    #    parser.error("Configuration file not readable")
    #config.readfp(configfile)
    #configfile.close()

    ## a list to store the CSV values
    csvlines = []

    try:
        csvfile = open(args.csvfile, 'rb')
        discogs_csv = csv.reader(csvfile, dialect='excel')
    except:
        print >>sys.stderr, "file not CSV file"
        sys.exit(1)

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

    ## create a document for reportlab
    ## set the margins as close to the edge as possible. I needed an ugly hack with the topMargin value
    qrdoc = SimpleDocTemplate(args.outfile, leftMargin=0, rightMargin=0, topMargin=-4*mm, bottomMargin=0, pagesize=A4, allow_splitting=0)

    ## create a table for reportlab
    ## labels are basically six columns:
    ## 1, 3, 5 :: text
    ## 2, 4, 6 :: QR code
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

        ## set the dimensions for the drawing
        qrimage = Drawing(35*mm,35*mm) 
        qrimage.add(qrurl)
    
        #qrhtml = Paragraph("<b>Artist:</b> %s<br /><b>Title:</b> %s<br /><b>Catalogue No.:</b> %s" % (artist, title, catalogue_number), styleSheet["BodyText"])
        #qrhtml = Paragraph("<b>Artist:</b> %s<br /><b>Title:</b> %s<br /><b>Price:</b> &euro; 50" % (artist, title), styleSheet["BodyText"])
        qrhtml = Paragraph("<b>Artist:</b> %s<br /><b>Title:</b> %s" % (artist, title), styleSheet["BodyText"])
        tmpqueue.append(qrhtml)
        tmpqueue.append(qrimage)
        if counter%3 == 0:
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