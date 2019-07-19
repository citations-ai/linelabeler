import os

from collections import defaultdict
from typing import List, Tuple, Set, Dict
from reportlab.pdfgen import canvas
from PyPDF2 import PdfFileWriter, PdfFileReader

from dataline import *


def get_file_path(journal_handler):
    return f'experiment1/{journal_handler}/{journal_handler}'


def calc_page_numbers_interval(data: List[DataLine], page_start: int = 0, page_finish: int = -1) -> Tuple[int, int]:
    page_first = data[0].page_number + page_start if page_start >= 0 else data[-1].page_number + page_start + 1
    page_last = data[0].page_number + page_finish if page_finish >= 0 else data[-1].page_number + page_finish + 1
    return page_first, page_last


def filter_data(data: List[DataLine], page_first: int, page_last: int) -> Tuple[List[DataLine], List[int]]:
    for line in data:
        if not (page_first <= line.page_number <= page_last):
            line.label = Label.SKIP

        if not len(line.text.strip()):
            line.label = Label.SKIP

    for i, line in enumerate(data):
        if line.text.strip().lower() == 'references':
            for j in range(i, len(data)):
                data[j].label = Label.SKIP
            break

    filtered_inds = [i for i in range(len(data)) if data[i].label != Label.SKIP]

    return data, filtered_inds


def find_regular_font(data: List[DataLine], filtered_inds: List[int]) -> Tuple[str, int]:
    regular_font_name = None
    regular_font_size = None
    max_font_count = -1

    font_counts = defaultdict(int)

    for i in filtered_inds:
        x = data[i]
        font_counts[(x.font0_name, x.font0_size)] += 1
        font_counts[(x.font1_name, x.font1_size)] += 1

        if font_counts[(x.font0_name, x.font0_size)] > max_font_count:
            max_font_count = font_counts[(x.font0_name, x.font0_size)]
            regular_font_name, regular_font_size = x.font0_name, x.font0_size
        if font_counts[(x.font1_name, x.font1_size)] > max_font_count:
            max_font_count = font_counts[(x.font1_name, x.font1_size)]
            regular_font_name, regular_font_size = x.font1_name, x.font1_size

    return regular_font_name, regular_font_size


def find_regular_vert_int(data: List[DataLine], filtered_inds: List[int]) -> int:

    regular_vert_int = None

    vert_int_counts = defaultdict(int)

    for i in filtered_inds:
        x = data[i]
        if x.int_from_prev == 0:
            continue
        vert_int_counts[x.int_from_prev] += 1
        if (regular_vert_int is None) or vert_int_counts[x.int_from_prev] > vert_int_counts[regular_vert_int]:
            regular_vert_int = x.int_from_prev

    return regular_vert_int


def find_base_magrins(data: List[DataLine], filtered_inds: List[int], n_columns: int = 1, left: bool = True, eps_indent: int = 2) -> List[int]:
    margins = [data[i].h_left if left else data[i].h_right for i in filtered_inds]
    margins = np.array(margins)
    margins_values, margins_indices = np.unique(margins, return_inverse=True)
    margins_counts = np.bincount(margins_indices)
    margins_counts_sorted_indices = list(reversed(np.argsort(margins_counts)))

    margin_keys = list()
    indents = defaultdict(int)
    for margin_value, margin_count in zip(margins_values[margins_counts_sorted_indices],
                                          margins_counts[margins_counts_sorted_indices]):
        index = None
        for margin_value_ in range(margin_value - eps_indent, margin_value + eps_indent + 1):
            if margin_value_ in indents:
                index = margin_value_
        if index is not None:
            indents[index] += margin_count
        else:
            indents[margin_value] += margin_count
            margin_keys.append(margin_value)

    base_margins = list(np.sort(margin_keys[:n_columns]))
    return base_margins


def find_paragraph_indents(data: List[DataLine], filtered_inds: List[int], eps_indent: int = 2) -> Dict:

    paragraph_indents = defaultdict(int)

    for i in filtered_inds:
        line = data[i]
        if line.label == Label.NOT_SURE:
        #if line.label == Label.PAR_STARTS:
            index = line.h_left
            for l in range(line.h_left - eps_indent, line.h_left + eps_indent + 1):
                if l in paragraph_indents:
                    index = l
            paragraph_indents[index] += 1

    return paragraph_indents


def find_par_magrins(indents: Dict, base_left_margins: List[int], base_right_margins: List[int], eps_indent: int = 2) -> List[int]:
    margin_keys_sorted = sorted(indents.keys())
    par_magrins = []

    for lm, rm in zip(base_left_margins, base_right_margins):
        cur_par_indent = None
        for key in margin_keys_sorted:
            if not (lm + eps_indent < key <= rm + eps_indent):
                continue
            if (cur_par_indent is None) or indents[cur_par_indent] < indents[key]:
                cur_par_indent = key
        par_magrins.append(cur_par_indent)

    return par_magrins


def read_lines_from_txt(file_path: str) -> List[DataLine]:
    data = []

    with open(os.path.join(os.path.dirname(os.path.curdir), f'{file_path}:orig.txt'), 'r', encoding='utf8') \
            as read_file:
        for string_line in read_file:
            try:
                data.append(read_line(string_line))
            except:
                pass

    return data


def write_lines_to_txt(data: List[DataLine], file_path: str):
    with open(os.path.join(os.path.dirname(os.path.curdir), f'{file_path}:l.txt'), 'w', encoding='utf8') \
            as write_file:
        for line in data:
            write_file.write(f'{line.to_export_txt}\n')


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
