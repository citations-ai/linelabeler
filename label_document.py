import sys

from utils import *


def pipeline(journal_handler):
    file_path = get_file_path(journal_handler)

    # Открытие и чтение исходного txt
    data = read_lines_from_txt(file_path)

    # Фильтруем страницы для разметки --- откидываем первые две страницы и всё, что идет после REFERENCES
    page_first, page_last = calc_page_numbers_interval(data, page_start=2)
    data, filtered_inds = filter_data(data, page_first, page_last)

    # Получаем основные общие характеристики документа
    regular_font_name, regular_font_size = find_regular_font(data, filtered_inds)
    regular_vert_int = find_regular_vert_int(data, filtered_inds)
    base_margins_left = find_base_magrins(data, filtered_inds, left=True)
    base_margins_right = find_base_magrins(data, filtered_inds, left=False)

    # Делаем первичный препроцессинг
    for line in data:
        if line.label == Label.SKIP:
            continue
        line.do_processing_1(regular_font_name, regular_font_size, regular_vert_int,
                             base_margins_left, base_margins_right)

    # Считаем статистику для лучшего распознавания начал абзацев
    paragraph_indents = find_paragraph_indents(data, filtered_inds)
    par_margins_left = find_par_magrins(paragraph_indents, base_margins_left, base_margins_right)
    for line in data:
        if line.label == Label.SKIP:
            continue
        if line.label == Label.NOT_SURE:
            line.do_processing_2(regular_font_name, regular_font_size, regular_vert_int,
                                 base_margins_left, base_margins_right, par_margins_left)

    # Сохраняем разметку
    write_lines_to_txt(data, file_path)
    write_lines_to_pdf(data, file_path)


if __name__ == "__main__":
    journal_handler = sys.argv[1]
    pipeline(journal_handler)
