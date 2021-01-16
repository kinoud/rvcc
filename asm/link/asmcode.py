import re

class ASM_Line():
    def __init__(self, op, *args):
        self.op = op
        self.args = args
        self.pos = 0
        # self.marks = {}

    def __str__(self):
        if self.op=='label':
            return self.args[0]+':'
        content = self.op+'  \t'
        for arg in self.args:
            content += arg + ', '
        content = content[:-2]
        content = content.strip()
        if not self.op in [
            '.section', '.data', '.text', '.global', '.globl'
                ]:
            content = '\t' + content
        return content
    def __repr__(self):
        return str(self)

def gen_code_by_list(list):
    if list[0].strip()[-1]==':':
        return ASM_Line('label', list[0].strip()[:-1])
    return ASM_Line(*list)

def text_code_pass_one(code, pos, wait_dict, label_dict): # 返回值是下一句的pos
    code.pos = pos
    if code.op=='label':
        label_name = code.args[0]
        label_dict[label_name] = pos
        return pos
    #
    for arg in code.args:
        if re.match(r'%hi.*|%lo.*|[_a-zA-Z].*', arg):
            list = wait_dict.get(arg)
            if list is None:
                wait_dict[arg] = [code]
            else:
                wait_dict[arg].append(code)
    return pos + 4

def dict_in(label_dict, wait_dict):
    for k, v in label_dict.items():
        hk = '%hi('+k+')'
        lk = '%lo('+k+')'
        for _k, _s in [(k, 'm'), (hk, 'h'), (lk, 'l')]:
            item = wait_dict.get(_k)
            if not (item is None):
                for code in item:
                    text_code_pass_two(code, _k, v, _s)
            wait_dict.pop(_k, None)

def text_code_pass_two(code, k, v, vtype = 'm'):
    '''
    if code.op=='jal' or code.op.startswith('b'):      # PC相对跳转
        v -= code.pos
        #v //= 2               # 末位省略这个操作到转化为机器码时再做
    '''
    v -= code.pos
    if vtype=='h':
        v = v>>12
    elif vtype=='l':
        v+=4                   # %lo一般跟在%hi后面，要以后面的值为基准
        v = v^(v>>12<<12)
        while v>=1<<11:
            v-=1<<12
    arg_list = []
    for arg in code.args:
        t = arg if arg!=k else str(v)
        arg_list.append(t)
    code.args = tuple(arg_list)

def data_code_pass_one(code, pos, label_dict): # 返回值是下一句的pos
    code.pos = pos # 也许有用
    if code.op=='label':
        label_name = code.args[0]
        label_dict[label_name] = pos
        return pos
    if code.op=='.align':
        align_num = int(code.args[0])
        balign_num = 1<<align_num
    elif code.op=='.balign':
        balign_num = int(code.args[0])
    if code.op=='.align' or code.op=='.balign':
        while pos%balign_num!=0:
            pos += 1
        return pos
    if code.op=='.zero':
        cnt = int(code.args[0])
        pos += cnt
        return pos
    if code.op=='.word':              # 暂时只考虑支持一次定义一个，实际还没有初始化
        if len(code.args)!=1:
            print('Complex ".word" settings not implemented.')
        pos += 4
        return pos
    else:
        print('Data settings not implemented.')
    return pos

def write_bin_code(text, outfile):
    fout = None
    try:
        fout = open(outfile, 'w')
    except:
        print('Error: fail to open output file.')
        return
    for code in text:
        fout.write(str(code)+'\n')