import re
from enum import Enum
from typing import List, Tuple, Set, Dict
import numpy as np


class State(Enum):
    NEUTRAL = 0
    PARAGRAPH = 1
    BUKVITSA = 2


class Sizes(Enum):
    NOT_EQUAL = 0
    SMALL = 1
    REGULAR = 2
    LARGE = 3


class Label(Enum):
    NOT_SURE = '?'
    PAR_STARTS = 'A'
    PAR_CONTINUES = 'B'
    TITLE = 'C'
    FOOTNOTE = 'D'
    OTHER = '*'
    SKIP = '!'


color_dict = {Label.PAR_STARTS: (1.0, 0.0, 0.0),
              Label.PAR_CONTINUES: (0.0, 1.0, 1.0),
              Label.TITLE: (0.0, 0.0, 1.0),
              Label.FOOTNOTE: (0.0, 1.0, 0.0),
              Label.OTHER: (0.5, 0.5, 0.5),
              Label.SKIP: (0.9, 0.9, 0.9),
              # Label["BUKVITSA"]: (1.0, 0.0, 1.0),
              # Label["LIST"]: (1.0, 1.0, 0.0),
              }


NUM_LINE_ATTRS = 13


def _is_valid_title(s: str) -> bool:
    """
    :param s: original string, e.g. "I. Introduction"
    :return: if s is a valid title
    """
    s = s.strip().split()
    if len(s) < 2:
        return False
    s = s[0]
    for regex in [
        '^(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})[.]?',
        '\d*[.\d*]+[.]?',
        '[A-Za-z][.\)]',
    ]:
        result = re.match(regex, s)
        if result is not None and result.span()[1] == len(s):
            return True
    return False


class DataLine:
    def __init__(self,
                 page_number: str = None,  #:Nстраницы
                 line_number: str = None,  #:Nстроки, сквозной
                 first_symbol: str = None,  #:Nсимвола, начального, сквозной
                 int_from_prev: str = None,  #:дельта-v-coord-up
                 int_from_next: str = None,  #:дельта-v-coord-down
                 h_left: str = None,  #:h-coord начала
                 h_right: str = None,  #:h-coord конца + 1
                 v: str = None,  #:v-coord
                 font0_size: str = None,  #:font-height0
                 font0_name: str = '',  #:font-name0
                 font1_size: str = None,  #:font-height1
                 font1_name: str = '',  #:font-name1
                 text: str = None,  #:TEXT
                 ):
        self.page_number = self.to_int(page_number)
        self.line_number = self.to_int(line_number)
        self.first_symbol = self.to_int(first_symbol)

        self.int_from_prev = self.to_int(int_from_prev)
        self.int_from_next = self.to_int(int_from_next)

        self.h_left = self.to_int(h_left)
        self.h_right = self.to_int(h_right)
        self.v = self.to_int(v)

        self.font0_size = self.to_int(font0_size)
        self.font0_name = font0_name
        self.font1_size = self.to_int(font1_size)
        self.font1_name = font1_name

        self.text = text

        self.label = Label.NOT_SURE

        self.ind_block = None
        self.is_aligned_left = None
        self.is_aligned_right = None
        self.is_aligned_par = None
        self.vert_int_category = None
        self.font_size_category = None
        self.is_font_regular = None
        self.is_after_empty_line = False


    @staticmethod
    def to_int(x):
        return int(x) if len(x) else 0

    @property
    def to_export_txt(self):
        line_export = [self.page_number,
                       self.line_number,
                       self.first_symbol,
                       self.int_from_prev,
                       self.int_from_next,
                       self.h_left,
                       self.h_right,
                       self.v,
                       self.font0_size,
                       self.font0_name,
                       self.font1_size,
                       self.font1_name,
                       self.label.value,
                       self.text]

        line_export = ':'.join([str(y) for y in line_export])
        return line_export

    def find_column_index(self, base_margins_left: List[int], base_margins_right: List[int],
                          eps_layout: int = 2) -> int:
        n_columns = len(base_margins_left)
        column_index = -1

        for i in range(n_columns):
            if base_margins_left[i] - eps_layout <= self.h_left <= self.h_right <= base_margins_right[i] + eps_layout:
                column_index = i

        return column_index

    @staticmethod
    def compare_size_with_reqular(size: int, regular_size: int, eps_size: float = 0.05) -> Sizes:
        if np.log(size / regular_size) > eps_size:
            return Sizes.LARGE
        if np.log(size / regular_size) < -eps_size:
            return Sizes.SMALL
        return Sizes.REGULAR

    def compare_font_sizes(self, regular_font_size: int, eps_size: float = 0.05) -> Sizes:
        size0 = self.compare_size_with_reqular(self.font0_size, regular_font_size, eps_size)
        size1 = self.compare_size_with_reqular(self.font1_size, regular_font_size, eps_size)
        if size0 != size1:
            return Sizes.NOT_EQUAL
        return size0

    def compare_vert_int(self, regular_vert_int: int, eps_size: float = 0.05) -> Sizes:
        if self.int_from_prev == 0:
            return Sizes.REGULAR
        return self.compare_size_with_reqular(self.int_from_prev, regular_vert_int, eps_size)

    def _do_preprocessing_1(self, regular_font_name: str, regular_font_size: int, regular_vert_int: int,
                            base_margins_left: List[int], base_margins_right: List[int],
                            eps_size: float = 0.05, eps_layout: int = 4):
        self.ind_block = self.find_column_index(base_margins_left, base_margins_right, eps_layout)

        self.is_aligned_left = abs(base_margins_left[self.ind_block] - self.h_left) <= eps_layout
        self.is_aligned_right = abs(base_margins_right[self.ind_block] - self.h_right) <= eps_layout

        self.vert_int_category = self.compare_vert_int(regular_vert_int, 1 * eps_size)

        self.font_size_category = self.compare_font_sizes(regular_font_size, eps_size)
        self.is_font_regular = (self.font0_name == regular_font_name) or (self.font1_name == regular_font_name)

    def do_processing_1(self, regular_font_name: str, regular_font_size: int, regular_vert_int: int,
                        base_margins_left: List[int], base_margins_right: List[int],
                        eps_size: float = 0.05, eps_layout: int = 4):
        self._do_preprocessing_1(regular_font_name, regular_font_size, regular_vert_int,
                                base_margins_left, base_margins_right,
                                eps_size, eps_layout)
        # ***D
        if self.font_size_category == Sizes.NOT_EQUAL:
            self.label = Label.OTHER
        # ***S
        elif self.font_size_category == Sizes.SMALL:
            self.label = Label.FOOTNOTE
        # ***L
        elif self.font_size_category == Sizes.LARGE:
            self.label = Label.TITLE
        elif self.is_after_empty_line:
            self.label = Label.NOT_SURE
        # ***R
        elif self.font_size_category == Sizes.REGULAR:
            # **SR
            if self.vert_int_category == Sizes.SMALL:
                self.label = Label.FOOTNOTE
            # **LR
            elif self.vert_int_category == Sizes.LARGE:
                if not self.is_font_regular:
                    self.label = Label.TITLE
                elif _is_valid_title(self.text):
                    self.label = Label.TITLE
                else:
                    # 11LR
                    if self.is_aligned_left and self.is_aligned_right:
                        self.label = Label.PAR_STARTS
                    # 10LR
                    elif self.is_aligned_left:
                        self.label = Label.NOT_SURE
                    # 01LR
                    elif self.is_aligned_right:
                        self.label = Label.NOT_SURE
                    # 00LR
                    else:
                        self.label = Label.TITLE
            # **RR
            elif self.vert_int_category == Sizes.REGULAR:
                if False and not self.is_font_regular:
                    self.label = Label.NOT_SURE
                else:
                    # 11RR
                    if self.is_aligned_left and self.is_aligned_right:
                        self.label = Label.PAR_CONTINUES
                    # 10RR
                    elif self.is_aligned_left:
                        self.label = Label.NOT_SURE
                    # 01RR
                    elif self.is_aligned_right:
                        self.label = Label.NOT_SURE
                    # 00RR
                    else:
                        self.label = Label.NOT_SURE
            else:
                raise ValueError
        else:
            # f'The size {self.font_size_category} is not valid!'
            raise ValueError

    def _do_preprocessing_2(self, regular_font_name: str, regular_font_size: int, regular_vert_int: int,
                            base_margins_left: List[int], base_margins_right: List[int], par_margins_left: List[int],
                            eps_size: float = 0.05, eps_layout: int = 2):
        self.is_aligned_par = abs(par_margins_left[self.ind_block] - self.h_left) <= eps_layout

    def do_processing_2(self, regular_font_name: str, regular_font_size: int, regular_vert_int: int,
                             base_margins_left: List[int], base_margins_right: List[int], par_margins_left: List[int],
                             eps_size: float = 0.05, eps_layout: int = 2):
        self._do_preprocessing_2(regular_font_name, regular_font_size, regular_vert_int,
                                base_margins_left, base_margins_right, par_margins_left,
                                eps_size, eps_layout)
        if _is_valid_title(self.text):
            self.label = Label.TITLE
        elif self.is_aligned_par:
            self.label = Label.PAR_STARTS
        elif self.vert_int_category == Sizes.LARGE:
            if self.text[0] == self.text.upper()[0]:
                if not self.is_font_regular:
                    self.label = Label.TITLE
                elif self.is_after_empty_line:
                    self.label = Label.TITLE
                else:
                    self.label = Label.PAR_STARTS
            else:
                self.label = Label.PAR_CONTINUES
        #elif self.text[0] == self.text.upper()[0]:
        #    self.label = Label.PAR_STARTS
        else:
            if self.is_font_regular:
                self.label = Label.PAR_CONTINUES  # OTHER
            else:
                self.label = Label.TITLE


def read_line(string_line: str) -> DataLine:
    line_attrs = string_line.replace('\n', '').split(':')
    len_line_attrs = len(line_attrs)

    assert len_line_attrs >= NUM_LINE_ATTRS, \
        f'must have at least {NUM_LINE_ATTRS - 1} elements, but has {len_line_attrs}'

    if len(line_attrs) > NUM_LINE_ATTRS:
        line_attrs[NUM_LINE_ATTRS - 1] = ':'.join(line_attrs[NUM_LINE_ATTRS - 1:])
        line_attrs = line_attrs[:NUM_LINE_ATTRS]

    return DataLine(*line_attrs)
