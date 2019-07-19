import os

from collections import defaultdict
from typing import List, Tuple, Set, Dict
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileWriter, PdfFileReader


from dataline import *


def write_lines_to_pdf(data: List[DataLine], file_path: str):
    input_file = PdfFileReader(open(os.path.join(os.path.dirname(os.path.curdir), f'{file_path}:orig.pdf'), "rb"))

    output_file = PdfFileWriter()

    cur_page = 0
    input_page = input_file.getPage(cur_page)

    c = canvas.Canvas('watermark.pdf')

    for line in data:
        if line.page_number - 1 == cur_page:
            # new page == old page
            c.setStrokeColorRGB(*color_dict[line.label])
            c.rect(line.h_left, line.v, line.h_right - line.h_left, 8, stroke=1, fill=0)

            # input_page.mergePage(watermark.getPage(0))
        else:
            c.save()
            watermark = PdfFileReader(open("watermark.pdf", "rb"))
            input_page.mergePage(watermark.getPage(0))
            output_file.addPage(input_page)

            cur_page = line.page_number - 1
            input_page = input_file.getPage(cur_page)

            c = canvas.Canvas('watermark.pdf')
            c.setStrokeColorRGB(*color_dict[line.label])
            c.rect(line.h_left, line.v, line.h_right - line.h_left, 8, stroke=1, fill=0)

    c.save()
    watermark = PdfFileReader(open("watermark.pdf", "rb"))
    input_page.mergePage(watermark.getPage(0))
    output_file.addPage(input_page)

    with open(os.path.join(os.curdir, f'{file_path}:l.pdf'), "wb") as o:
        output_file.write(o)



