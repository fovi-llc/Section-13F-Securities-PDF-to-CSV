import PyPDF2

# import textract
import glob
import os
import sys
import re
import pandas as pd
from io import StringIO

topdir = sys.argv[1]

for filename in glob.iglob(os.path.join(topdir, "*.pdf")):
    print(filename)
    path = "data/pdf13flist/13flist2019q3.pdf"
    filename = os.path.basename(path)
    # extract year and quarter from filename.
    # year follows "13flist" and is 4 characters long
    # quarter follows "q" and is 1 character long
    year = filename[filename.index("13flist") + len("13flist"):filename.index("q")]
    quarter = filename[filename.index("q") + 1]
    print(f"{year=}, {quarter=}")

    # open allows you to read the file
    pdfFileObj = open(filename, "rb")
    # The pdfReader variable is a readable object that will be parsed
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    # discerning the number of pages will allow us to parse through all #the pages
    num_pages = pdfReader.numPages
    count = 0
    text = ""
    # The while loop will read each page
    while count < num_pages:
        pageObj = pdfReader.getPage(count)
        count += 1
        text += pageObj.extractText()

    # get rid of empty lines
    text = "".join([s for s in text.splitlines(True) if s.strip("\r\n")])

    # CUT OUT REPEATING HEADERS
    # WHEN CONSTRUCTING DIFFICULT REGEX TEST HERE: https://pythex.org/
    # EXAMPLE:
    # CUSIP NOISSUER NAMEISSUER DESCRIPTIONSTATUS
    # 7:26IVM001
    # Run Date:
    # 1/10/2019** List of Section 13F Securities **
    # Page 1 Year:
    # Run Time:
    # 2018Qtr:
    # 4
    cleanup_pattern = re.compile(r"^CUSIP.*?\d{4}Qtr:.\d", re.DOTALL | re.MULTILINE)
    text = re.sub(cleanup_pattern, "", text)

    # tricky part of extracting only data fields
    # ASSUMPTION:
    # Look for lines that begin with either digit or cap letter in first position
    # followed by either capital or digit repeating 'n' times
    pattern = r"^[A-Z0-9][A-Z0-9]{8}"
    data_str = "cusip,has_options,name,description,status,year,quarter\n"
    data_line_count = 0
    for line in text.splitlines():
        if re.search(pattern, line):
            # DATA CLEANUP
            cleanup_pattern = re.compile(r"^([A-Z0-9]{9})([\* ])")
            line = re.sub(cleanup_pattern, r"\1,\2,", line)
            # ASSUMPTION: FIRST CODE MUST BE "9" CHARS LONG
            # (1.) '*' char gets lumped with adjacent positions
            # cleanup_pattern = r'^[0-9]?([A-Z,0-9]{9})([\* ]+)([A-Z])'
            # cleanup_pattern = r'^[0-9]*([A-Z,0-9]{9})([\* ]?)([A-Z]+)'
            # l = re.sub(cleanup_pattern, r'\1,\2,\3', l)

            # (2.) FIRST AND SECOND DATA FIELD ARE GETTING LUMPED TOGETHER, ie: 000868109ACNB
            # AND AT SAME TIME EXTRA CHAR GETS ADDED IN FIRST POSITION OF FIRST DATA FIELD
            # KILL EXTRA CHAR AND INJECT SPACE
            cleanup_pattern = re.compile(r"^([A-Z0-9]{9})([A-Z0-9])")
            line = re.sub(cleanup_pattern, r"\1,,\2", line)

            cleanup_pattern = re.compile(
                r"^(.*)(SHS|CALL|DEBT|NAMEN|EVENTSHS|SPONSORED ADR|COM PAR|COM CL A|NOTE|COM|PUT|UNIT|\*W|CL|USD|ORD|NOTE)(.*)$"
            )
            line = re.sub(cleanup_pattern, r"\1,\2,\3", line)

            data_str += line + f",{year},{quarter}" "\n"
            data_line_count += 1

    df = pd.read_csv(StringIO(data_str), sep=",")
    df.to_excel("output.xlsx", index=False, header=True)

    with open(filename + ".txt", "w", encoding="utf-8") as out_filename:
        out_filename.write(str(data_str))
        # out_filename.write(str(text))

    print(data_line_count)
