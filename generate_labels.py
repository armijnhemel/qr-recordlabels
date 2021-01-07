#!/usr/bin/env python3

# a simple script that reads Discogs CSV collection dumps
# and generates labels with:
# * QR code for the Discogs URL
# * name of the artist
# * name of the title
#
# I only have A4 sheets with 8 rows of 3 labels each (24 per A4 sheet)
# so some settings are hardcoded
#
# Licensed under the terms of the General Public License version 3
#
# SPDX-License-Identifier: GPL-3.0
#
# Copyright 2017-2019 - Armijn Hemel

import sys
import os
import argparse
import configparser
import csv

# load a lot of reportlab stuff
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

    parser.add_argument("-c", "--config", action="store", dest="cfg",
                        help="path to configuration file", metavar="FILE")
    parser.add_argument("-f", "--file", action="store", dest="csvfile",
                        help="path to CSV file", metavar="FILE")
    parser.add_argument("-o", "--out", action="store", dest="outfile",
                        help="path to output PDF file", metavar="FILE")
    parser.add_argument("-p", "--profile", action="store", dest="profile",
                        help="name of label profile", metavar="PROFILE")
    args = parser.parse_args()

    # sanity checks for the configuration file
    if args.cfg is None:
        parser.error("Configuration file missing")

    if not os.path.exists(args.cfg):
        parser.error("Configuration file does not exist")

    # sanity checks for the CSV file
    if args.csvfile is None:
        parser.error("CSV file missing")

    if not os.path.exists(args.csvfile):
        parser.error("CSV file does not exist")

    # sanity checks for the output file
    if args.outfile is None:
        parser.error("name of output file missing")

    # sanity checks for the profile
    if args.profile is None:
        parser.error("name of profile missing")

    # read the configuration file
    config = configparser.ConfigParser()

    try:
        configfile = open(args.cfg, 'r')
    except:
        configfile.close()
        parser.error("Configuration file not readable")
    config.read_file(configfile)
    configfile.close()

    # check wheher or not the name of the profile provided
    # exists in the configuration file
    if args.profile not in config.sections():
        print("ERROR: profile name not found in configuration file, exiting",
              file=sys.stderr)
        sys.exit(1)

    # store profile
    profile = {}

    swap_columns = False

    # fields from CSV that need to be printed
    fields = []

    for section in config.sections():
        if section == "general":
            try:
                config.get(section, "type")
            except configparser.NoOptionError:
                break
            try:
                tmpval = config.get(section, "swap-columns")
                if tmpval == 'yes':
                    swap_columns = True
            except configparser.NoOptionError:
                pass
        elif section == args.profile:
            try:
                config.get(section, "type")
            except configparser.NoOptionError:
                break
            # first check if there is a page size
            try:
                pagesize = config.get(section, 'pagesize')
                if pagesize == 'A4':
                    profile['pagesize'] = A4
                    # also set the units for A4
                    profile['unit'] = mm
            except configparser.NoOptionError:
                pass

            if 'pagesize' not in profile:
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
                # default: 1 row
                profile['rows'] = 1
            try:
                profile['columns'] = int(config.get(section, 'columns'))
            except:
                # default: 1 column
                profile['columns'] = 1
            try:
                # default: points
                unit = config.get(section, 'unit')
                if unit == 'mm':
                    profile['unit'] = mm
            except configparser.NoOptionError:
                pass
            try:
                fields = config.get(section, 'fields').split(':')
                if fields == []:
                    fields = ['artist', 'title']
            except configparser.NoOptionError:
                # default is artist and title
                fields = ['artist', 'title']
    if profile == {}:
        print("ERROR: empty profile, exiting", file=sys.stderr)
        sys.exit(1)

    # a list to store the CSV values
    csvlines = []

    try:
        csvfile = open(args.csvfile, 'r')
    except:
        print("ERROR: can't open CSV file, exiting", file=sys.stderr)
        sys.exit(1)
    try:
        discogs_csv = csv.reader(csvfile, dialect='excel')
    except:
        csvfile.close()
        print("ERROR: file not CSV file, exiting", file=sys.stderr)
        sys.exit(1)

    # now read the CSV entries and only store the actual entries,
    # not the header
    firstline = True
    for r in discogs_csv:
        if firstline:
            # first line is not needed
            firstline = False
            continue
        csvlines.append(r)
    csvfile.close()

    # only process if there actually were lines in the CSV
    if len(csvlines) == 0:
        sys.exit(0)

    if 'pagesize' not in profile:
        if 'unit' in profile:
            profile['pagesize'] = (profile['width']*profile['unit'], profile['height']*profile['unit'])
        else:
            profile['pagesize'] = (profile['width'], profile['height'])
        dims = min(profile['width'], profile['height']) - 5
    else:
        dims = 35

    # create a document for reportlab
    # set the margins as close to the edge as possible.
    # I needed an ugly hack with the topMargin value
    qrdoc = SimpleDocTemplate(args.outfile, leftMargin=0, rightMargin=0,
                              topMargin=-4*profile['unit'], bottomMargin=0,
                              pagesize=profile['pagesize'], allow_splitting=0)

    # create a table for reportlab
    # each label basically consists of two columns:
    #
    # * text
    # * QR code image
    #
    # These are combined to form the final label.
    # The default ordering is: text left, image right, unless
    # the program has been configured to swap the columns.

    # container for the 'Flowable' objects
    elements = []

    data = []

    styleSheet = getSampleStyleSheet()
    qrTableStyle = styleSheet['BodyText']
    qrTableStyle.leading = 10

    # Discogs collection export looks like this:
    # ['Catalog#', 'Artist', 'Title', 'Label', 'Format', 'Rating',
    #  'Released', 'release_id', 'CollectionFolder', 'Date Added',
    #  'Collection Media Condition', 'Collection Sleeve Condition',
    #  'Collection Notes']
    # By default just 'Artist' and 'Title' are added.
    counter = 1
    tmpqueue = []
    for r in csvlines:
        (catalogue_number, artist, title, label, disc_format, rating, released, release_id, collectionfolder, date_added, media_condition, sleeve_condition, notes) = r

        # now generate a QR image with a valid discogs URL
        qrurl = QrCodeWidget('https://www.discogs.com/release/%s' % str(release_id))

        # set the dimensions for the Drawing, which is a square
        qrimage = Drawing(dims*profile['unit'], dims*profile['unit'])

        # add the QR code to the drawing
        qrimage.add(qrurl)

        # create the HTML with the text
        qrhtmltext = ""
        fieldcounter = 1
        for field in fields:
            if field == 'artist':
                qrhtmltext += "<b>Artist:</b> %s" % artist
            elif field == 'title':
                qrhtmltext += "<b>Title:</b> %s" % title
            elif field == 'sleeve':
                qrhtmltext += "<b>Sleeve Condition:</b> %s" % sleeve_condition
            elif field == 'media':
                qrhtmltext += "<b>Media Condition:</b> %s" % media_condition
            elif field == 'catalogue':
                qrhtmltext += "<b>Catalogue No.::</b> %s" % catalogue_number
            if fieldcounter < len(fields):
                qrhtmltext += "<br />"
            fieldcounter += 1
        qrhtml = Paragraph(qrhtmltext, styleSheet["BodyText"])

        # add the image and HTML to the data queue in the desired order
        if swap_columns:
            tmpqueue.append(qrimage)
            tmpqueue.append(qrhtml)
        else:
            tmpqueue.append(qrhtml)
            tmpqueue.append(qrimage)
        if counter % profile['columns'] == 0:
            data.append(tmpqueue)
            tmpqueue = []
        counter += 1

    # add any data that hasn't yet been added to the data queue
    if tmpqueue != []:
        data.append(tmpqueue)

    # pour the data queue into a table. For some reason I have to
    # add 2 to the row heights which is a TODO.
    qr_table = Table(data, colWidths=dims*profile['unit'],
                     rowHeights=(dims+2)*profile['unit'],
                     style=[('TOPMARGIN', (0, 0), (-1, -1), 0),
                            ('BOTTOMMARGIN', (0, 0), (-1, -1), 0),
                            ('LEFTMARGIN', (0, 0), (-1, -1), 0),
                            ('RIGHTMARGIN', (0, 0), (-1, -1), 0),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            # set INNERGRID for debugging
                            #('INNERGRID', (0, 0), (-1,-1), 0.25, colors.black)
                           ])
    elements.append(qr_table)

    # finally generate the document with all the QR codes
    qrdoc.build(elements)

if __name__ == "__main__":
    main(sys.argv)
