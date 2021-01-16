
from macro.macrodef import DefaultMacros

from macro.register import register_replace

import re


macro_list_tmp = dir(DefaultMacros)
macro_list = []
for attr in macro_list_tmp:
    if re.match(r'macro_.*', attr):
        macro_list.append(attr)
rvi_macro = {
}
for macro in macro_list:
    rvi_macro[macro[6:]] = getattr(DefaultMacros, macro, None)

def macro_handler(words):
    new_words_list = [words]
    try:
        new_words_list = rvi_macro[words[0]](words[1:])
    except KeyError:
        pass
    return new_words_list

def register_handler(words_list):
    for words in words_list:
        for i in range(len(words)):
            words[i] = register_replace(words[i])
    return words_list

def split_segment(asm_list):
    def_list = []
    text_list = []
    data_list = []
    asm_list.reverse()
    cur_words = asm_list.pop()
    while cur_words[0]!='.section' and cur_words[0]!='.text':
        def_list.append(cur_words)
        cur_words = asm_list.pop()
    assert(cur_words[0]=='.section' or cur_words[0]=='.text')
    cur_words = asm_list.pop()
    while cur_words[0]!='.section' and cur_words[0]!='.data':
        text_list.append(cur_words)
        cur_words = asm_list.pop()
    assert(cur_words[0]=='.section' or cur_words[0]=='.data')
    asm_list.reverse()
    data_list = asm_list

    return [def_list, text_list, data_list]

def main_by_list(list):
    first_parsed_lines = []
    for line in list:
        sls = [x for x in re.split(r',|\s', re.sub(r'#.*', "", line).strip()) if x]
        if len(sls)==0 or len(sls[0])==0:
            continue
        new_words_list = macro_handler(sls)
        new_words_list = register_handler(new_words_list)
        for new_words in new_words_list:
            first_parsed_lines.append(new_words)

    return first_parsed_lines

def file_in_process(infile):
    fin = None
    try:
        fin = open(infile, 'r')
    except IOError:
        print("Error: File does not seem to exist or" +
                       " you do not have the required permissions.")
        return None
    ret_val = main_by_list(fin)
    fin.close()
    return ret_val

def gen_segments_from_infile(infile):
    asm_list = file_in_process(infile)
    if asm_list is None:
        splited = None
    else:
        splited = split_segment(asm_list)
    return splited
