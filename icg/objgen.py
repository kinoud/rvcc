
ASM_AUTO_LABEL_CNT = 0

class ASM_Line():
    def __init__(self, op, *args):
        self.op = op
        self.args = args
        # self.marks = {}

    def __str__(self):
        if self.op=='label':
            return self.args[0]+':'
        content = self.op+'  \t'
        for arg in self.args:
            content += arg + ', '
        content = content[:-2]
        return '\t'+ content.strip()
    def __repr__(self):
        return str(self)

class ASM_VAR_MGR():
    def __init__(self, symbols):
        self.size = 4           # fp 一开始指向保存的上个帧指针
        self.symbols = symbols
        self.vars = {}
        self.waits = {}

    def __str__(self):
        return 'VAR total_size: '+str(self.size)+'\n'+str(self.vars)+'\nwaiting:'+str(self.waits)
    def __repr__(self):
        return str(self)

    def alloc_var(self, var):
        if var in self.symbols:
            self.vars[var.name] = (var, self.size)
            self.size += var.size
        else:
            self.waits[var.name] = (var, [])

    def get_var(self, var):
        v = self.vars.get(var.name)
        if v is None:
            v = self.waits.get(var.name)
        return v

    def make_address(self, var):        # 获得变量在fp下的偏移
        res = self.get_var(var)
        if res is None:
            self.alloc_var(var)
            res = self.get_var(var)
        _, offset = res
        return offset

    def lw(self, var, rt):       # 一般用t1/t2保存第1/2个参数的值
        offset = self.make_address(var)
        if isinstance(offset, int):
            code = ASM_Line('lw', rt, 'fp', str(-offset))
        else:
            code = ASM_Line('lw', rt, 'fp', '0')
            self.waits[var.name][1].append(code)
        return code

    def sw(self, var, rt):       # 一般用t3保存dest的值
        offset = self.make_address(var)
        if isinstance(offset, int):
            code = ASM_Line('sw', rt, 'fp', str(-offset))
        else:
            code = ASM_Line('lw', rt, 'fp', '0')
            self.waits[var.name][1].append(code)
        return code

class ASM_LABEL_MGR():
    def __init__(self):
        self.waitings = []
        self.labels = []

    def wait_ptr(self, asm_code, tgt_tac):
        self.waitings.append((
            asm_code, #'code': 
            tgt_tac   #'tac': 
        ))

    def alloc_ptr(self, tgt_tac):
        new_label_name = '__auto_'+str(ASM_AUTO_LABEL_CNT)
        self.labels.append((
            tgt_tac,       #     'tac': 
            new_label_name #    'label': 
        ))
        return new_label_name


class ASM_Module():
    def __init__(self, type, symbols):
        self.code = [] # list of ASM_line
        self.type = type
        self.local_val_mgr = ASM_VAR_MGR(symbols)
        self.local_label_mgr = ASM_LABEL_MGR()
        self.global_varlist = {}

    def add_code(self, *newlines):
        for line in newlines:
            self.code.append(line)

    def complete_labels(self):
        code_cnt = len(self.code)
        for i in range(code_cnt):
            for code_, tac in self.local_label_mgr.waitings:
                if not (self.code[i] is code_):
                    continue
                for tac_, label_name in self.local_label_mgr.labels:
                    if tac is tac_:
                        if code_.op=='j':
                            code_.args=(label_name,)
                        elif code_.op=='beqz':
                            code_.args=(code_.args[0], label_name)
                        else: # 可能包括函数调用等，还未考虑
                            pass

    def jump_tac_handler(self, tac): # tac.op=='goto' or tac.op=='ifz' or tac.op=='label'
        asm_lines = []
        if tac.op=='goto':
            next_code = ASM_Line('j', '')
            self.local_label_mgr.wait_ptr(next_code, tac.dest.tgt)
            asm_lines.append(next_code)
        elif tac.op=='ifz':
            arg = tac.args[0]
            next_code = self.local_val_mgr.lw(arg, 't1')
            asm_lines.append(next_code)
            next_code = ASM_Line('beqz', 't1', '')
            self.local_label_mgr.wait_ptr(next_code, tac.dest.tgt)
            asm_lines.append(next_code)
        elif tac.op=='label' or tac.op=='ret':                  # 会处理ret当作跳转目标的部分
            label_name = self.local_label_mgr.alloc_ptr(tac)
            next_code = ASM_Line('label', label_name)
            asm_lines.append(next_code)
        else:
            pass # 应该不会到这
        return asm_lines

    def normal_tac_handler(self, tac):
        asm_lines = []
        op = tac.op
        op_cast = { '=': 'mv',
            '+': 'add',
            '+i':'addi',
            '-': 'sub',
            '<': 'slt',
            '<u': 'sltu',
            '==0': 'seqz',
            '!=0': 'snez',
            '*': 'mul',            # 对乘除法还没仔细做，这里是暂时处理
            '/': 'div',
            '%': 'rem',
        }
        t_op = op_cast.get(op)
        if t_op is None:
            print('op not found')
        else:
            if op=='<' or op=='<u':    # 处理这里可能的有常数的情况——呃似乎处理不了
                print('unable')
            t_arg1 = tac.args[0]
            next_code = self.local_val_mgr.lw(t_arg1, 't1')
            asm_lines.append(next_code)
            if len(tac.args)==1:
                if op=='-':           # 处理单目-号
                    next_code = ASM_Line('neg', 't3', 't1')
                else:
                    next_code = ASM_Line(t_op, 't3', 't1')
                asm_lines.append(next_code)
            else:
                t_arg2 = tac.args[1]                
                if t_arg2.isConst:
                    next_code = ASM_Line(t_op, 't3', 't1', str(t_arg2.val))
                    asm_lines.append(next_code)
                else:
                    next_code = self.local_val_mgr.lw(t_arg2, 't2')
                    asm_lines.append(next_code)
                    next_code = ASM_Line(t_op, 't3', 't1', 't2')
                    asm_lines.append(next_code)
            t_dest = tac.dest
            next_code = self.local_val_mgr.sw(t_dest, 't3')
            asm_lines.append(next_code)
            
        return asm_lines

    @staticmethod
    def gen_decl(self, block):
        print('decl block')
        print(block)

    @staticmethod
    def gen_func(self, block, symbols):
        print('FUNC ASM MODULE')
        print(symbols)
        print(block)

    @staticmethod
    def gen_func_body(block, symbols):
        asm = ASM_Module('func_body', symbols)
        print('FUNC_BODY ASM MODULE')
        print(symbols)
        print(block)
        tac_list = block.TACs
        tac_list.reverse()
        first_tac = tac_list.pop()
        assert(first_tac.op=='label')
        # next_asm_line = ASM_Line('label', func_name)         没到生成标签的时候
        # asm.add_code(next_asm_line)
        for tac in reversed(tac_list):
            if tac.op=='ret':                   #  暂时先不考虑返回地址保存相关的问题
                asm.add_code(*asm.jump_tac_handler(tac))
                next_asm_line = ASM_Line('ret')
                asm.add_code(next_asm_line)
            elif tac.op=='goto' or tac.op=='ifz' or tac.op=='label':
                asm.add_code(*asm.jump_tac_handler(tac))
            else:
                asm.add_code(*asm.normal_tac_handler(tac))

        asm.complete_labels()
        print(asm.local_val_mgr)
        print(asm)
        return asm

    def  __str__(self):
        s = ''
        for line in self.code:
            s += str(line) + '\n'
        return s
    
    def __repr__(self):
        return str(self)

class ASM_CTRL():
    def __init__(self):
        self.location = 'global'
        self.funcDefs = []
        self.current_func_body = None

    def gen_func_body(self, block, symbols):
        self.current_func_body = ASM_Module.gen_func_body(block, symbols)

    def gen_func_def():
        pass

asm_ctrl = ASM_CTRL()