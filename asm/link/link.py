from link.asmcode import gen_code_by_list, text_code_pass_one, dict_in, data_code_pass_one, write_bin_code

def link(total, data_start = 4000, text_start = 0, outfile = 'riscv_link.tmp'):

    text_pos = text_start
    total_text = []
    data_pos = data_start
    # total_data = []             # 目前不能实现数据段初始化
    total_wait = {}
    total_dict = {}
    for file_code in total:
        glbl_raw_code = file_code[0]
        export_dict = {}
        for code in glbl_raw_code:
            # 省略其他情况考虑
            symbol = code[1]
            export_dict[symbol] = None

        text_raw_code = file_code[1]
        # print(text_raw_code)
        text_code = []
        for code in text_raw_code:
            text_code.append(gen_code_by_list(code))
        wait_dict = {}
        label_dict = {}
        for code in text_code:
            text_pos = text_code_pass_one(code, text_pos, wait_dict, label_dict)

        data_raw_code = file_code[2]
        # print(data_raw_code)
        data_code = []
        for code in data_raw_code:
            data_code.append(gen_code_by_list(code))
        for code in data_code:
            data_pos = data_code_pass_one(code, data_pos, label_dict)

        dict_in(label_dict, wait_dict)
        total_wait.update(wait_dict)

        for k, v in label_dict.items():
            if k in export_dict:
                export_dict[k] = v

        total_text += text_code
        # total_data += data_code

        # print(export_dict)
        for k, v in export_dict.items():
            if v is None:
                print('Error: an undefined global symbol.')
                continue
            if k in total_dict:
                print('Error: duplicate global symbol.')
                continue
            total_dict[k] = v
    
    dict_in(total_dict, total_wait)
    
    if len(total_wait)>0:
        print('Error: unresolved symbol(s).')

    write_bin_code(total_text, outfile)

    return (text_pos-text_start, data_pos-data_start)
