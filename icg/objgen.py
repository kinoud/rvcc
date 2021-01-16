from collections import deque

from .symbol import PtrType, ArrayType, StructType, FuncSymbol

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
        content = content.strip()
        if not self.op in [
            '.section', '.data', '.text', '.global', '.globl'
                ]:
            content = '\t' + content
        return content
    def __repr__(self):
        return str(self)

class ASM_VAR_MGR():
    def __init__(self, symbols):
        self.size = 8           # 目前只保存两个寄存器量 fp(帧指针), ra(返回地址)
        self.symbols = symbols
        self.vars = {}
        self.waits = {}
        self.offset_info = {}

    def __str__(self):
        return 'VAR total_size: '+str(self.size)+'\n'+str(self.vars)+'\nwaiting:'+str(self.waits)+'\nsolved:'+str(self.offset_info)
    def __repr__(self):
        return str(self)

    def solve_func_var(self):

        start_ptr = -self.size + 4

        for var in self.vars.values():
            res = self.waits.get(var.name)
            if res is None:
                print('Warning: unnecessary local variable.<'+str(var)+'>')
                continue
            self.offset_info[var.name] = (var, start_ptr)
            _, code_list = res
            for code in code_list:
                code.args = (code.args[0], code.args[1], str(start_ptr))
            start_ptr += var.size

        for var_name in self.vars:
            self.waits.pop(var_name, None)
        self.vars = {}


    def fill_in_param(self, var): #, offset):
        res = self.waits.get(var.name)
        if not (res is None):
            # _, code_list = res
            #for code in code_list:
            #    code.args = (code.args[0], code.args[1], str(-offset))
            #self.waits.pop(var.name)
            self.vars[var.name] = var
            self.size += var.size

    def alloc_var(self, var):
        #if var in self.symbols:
        #    self.vars[var.name] = (var, [])     # self.size)
        #    self.size += var.size               # 现在，所有offset都等到函数确定时再填入
        #else:
        #    self.waits[var.name] = (var, [])
        self.waits[var.name] = (var, [])
        if var in self.symbols:
            self.vars[var.name] = var
            self.size += var.size


    def get_var(self, var):
        #v = self.vars.get(var.name)
        #if v is None:
        #    v = self.waits.get(var.name)
        #return v
        return self.waits.get(var.name)

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
        if isinstance(var.type, ArrayType) or isinstance(var.type, StructType):   # 转而取指针
            code.op = 'addi'
        return code

    def sw(self, var, rt):       # 一般用t3保存dest的值
        offset = self.make_address(var)
        if isinstance(offset, int):
            code = ASM_Line('sw', rt, 'fp', str(-offset))
        else:
            code = ASM_Line('sw', rt, 'fp', '0')
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
        global ASM_AUTO_LABEL_CNT
        new_label_name = '__auto_'+str(ASM_AUTO_LABEL_CNT)
        ASM_AUTO_LABEL_CNT += 1
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

    def add_code(self, *newlines):
        for line in newlines:
            self.code.append(line)

    def export_as_func(self):
        for var, wait_list in self.local_val_mgr.waits.values():
            for code in wait_list:
                if code.op=='addi':
                    code.op = 'la'
                    code.args = (code.args[0], var.name)
                elif code.op=='lw':
                    code.args = (code.args[0], var.name)
                elif code.op=='sw':
                    code.args = (code.args[0], var.name, 't4')
                else:
                    print('ASM Error: illegal ref of global symbol.')

        return self.code
        '''
        for _, waiting_codes in self.local_val_mgr.waits.values():
            for code in waiting_codes:
                code.marks['g'] = True
        ex_code = []
        for code in self.code:
            if code.marks.get('g'):
                ex_code.append(ASM_Line('la', '', ''))
            ex_code.append(code)
        return (ex_code, self.local_val_mgr.waits)
        '''

    def complete_labels(self):
        for code_, tac in self.local_label_mgr.waitings:
            for tac_, label_name in self.local_label_mgr.labels:
                if tac is tac_:
                    if code_.op=='j':
                        code_.args=(label_name,)
                    elif code_.op=='beqz':
                        code_.args=(code_.args[0], label_name)
                    else: # 可能包括函数调用等，还未考虑
                        pass
        '''
        x = {}
        for code_, tac in self.local_label_mgr.waitings:
            id = tac.id
            if id not in x:
                x[id]=[]
            x[id].append(code_)
        for tac_, label_name in self.local_label_mgr.labels:
            for code_ in x[tac_.id]:
                if tac is tac_:
                    if code_.op=='j':
                        code_.args=(label_name,)
                    elif code_.op=='beqz':
                        code_.args=(code_.args[0], label_name)
                    else: # 可能包括函数调用等，还未考虑
                        pass
        '''

    def func_call_handler(self, tac, param_list):

        asm_lines = []
        param_cnt = len(param_list)
        if param_cnt>=8:
            print('Waring: too much params, throw the extra params.')
        for param in param_list:
            if param_cnt<8:
                if param.isConst:
                    next_code = ASM_Line('li', 'a'+str(param_cnt), str(param.val))
                else:
                    next_code = self.local_val_mgr.sw(param, 'a'+str(param_cnt))
                asm_lines.append(next_code)
            param_cnt -= 1
        
        next_code = ASM_Line('call', tac.args[0].name)
        asm_lines.append(next_code)
        next_code = self.local_val_mgr.sw(tac.dest, 'a0')
        asm_lines.append(next_code)
        return asm_lines

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
        elif tac.op=='label' or tac.op=='ret':                  # 会处理ret当作跳转目标的部分，ret指令在更外层做
            label_name = self.local_label_mgr.alloc_ptr(tac)
            next_code = ASM_Line('label', label_name)
            asm_lines.append(next_code)
        else:
            pass # 应该不会到这
        return asm_lines

    def normal_tac_handler(self, tac):
        asm_lines = []
        op = tac.op
        if op=='=':       # '='号单独考虑
            dest = tac.dest
            arg = tac.args[0]
            if arg.isConst:
                next_code = ASM_Line('li', 't1', str(arg.val))
                asm_lines.append(next_code)
            else:
                next_code = self.local_val_mgr.lw(arg, 't1')
                asm_lines.append(next_code)
            next_code = ASM_Line('mv', 't3', 't1')
            asm_lines.append(next_code)
            next_code = self.local_val_mgr.sw(dest, 't3')
            asm_lines.append(next_code)
            return asm_lines
        elif op=='&':     # 目前看来只有取结构体变量的地址会用到
            dest = tac.dest
            arg = tac.args[0]
            assert(not arg.isConst)
            next_code = self.local_val_mgr.lw(arg, 't1')
            asm_lines.append(next_code)
            next_code = ASM_Line('mv', 't3', 't1')
            asm_lines.append(next_code)
            next_code = self.local_val_mgr.sw(dest, 't3')
            asm_lines.append(next_code)
            return asm_lines
        elif op=='offset':
            field_name = tac.args[1].name
            if not isinstance(tac.args[0].type, PtrType):
                print('TAC code Error')
            elif not isinstance(tac.args[0].type.target_type, StructType):
                print('TAC code Error')
            else:
                offset_dict = tac.args[0].type.target_type.member_offsets
                field_offset = offset_dict.get(field_name)
                if field_offset is None:
                    print('Error: illegal struct field.')
                else:
                    dest = tac.dest
                    arg = tac.args[0]
                    next_code = self.local_val_mgr.lw(arg, 't1')
                    asm_lines.append(next_code)
                    next_code = ASM_Line('addi', 't3', 't1', str(field_offset))
                    asm_lines.append(next_code)
                    next_code = self.local_val_mgr.sw(dest, 't3')
                    asm_lines.append(next_code)
            return asm_lines

        op_cast = {
            '+': 'add',
            '+i':'addi',
            '-': 'sub',
            '<': 'slt',
            '<u': 'sltu',
            '<i': 'slti',
            '<iu': 'sltiu',
            '==0': 'seqz',
            '!=0': 'snez',
            '*': 'mul',            # 对乘除法还没仔细做，这里是暂时处理
            '/': 'div',
            '/u': 'divu',
            '%': 'rem',
            '%u': 'remu',
        }
        t_op = op_cast.get(op)
        if t_op is None:
            if op=='set':
                dest = tac.dest
                arg = tac.args[0]
                if arg.isConst:
                    next_code = ASM_Line('li', 't3', str(arg.val))
                    asm_lines.append(next_code)
                else:
                    next_code = self.local_val_mgr.lw(arg, 't3')
                    asm_lines.append(next_code)
                next_code = self.local_val_mgr.lw(dest, 't1')
                asm_lines.append(next_code)
                next_code = ASM_Line('sw', 't3', 't1', '0')
                asm_lines.append(next_code)
            elif op=='get':
                dest = tac.dest
                arg = tac.args[0]
                if arg.isConst:
                    next_code = ASM_Line('li', 't1', str(arg.val))
                    asm_lines.append(next_code)
                else:
                    next_code = self.local_val_mgr.lw(arg, 't1')
                    asm_lines.append(next_code)
                next_code = ASM_Line('lw', 't3', 't1', '0')
                asm_lines.append(next_code)
                next_code = self.local_val_mgr.sw(dest, 't3')
                asm_lines.append(next_code)
            else:
                print('op not found')
        else:                                 # 进入这个分支前提是有参数1，并且不是立即数
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
                    if op in ['*', '/', '/u', '%', '%u']:
                        next_code = ASM_Line('li', 't2', str(t_arg2.val))
                        asm_lines.append(next_code)
                        next_code = ASM_Line(t_op, 't3', 't1', 't2')
                        asm_lines.append(next_code)
                    else:
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

    def func_extend_with(self, func_decl):
        params = func_decl.param_symbols
        ret_val = func_decl.return_symbol
        param_list = [ret_val]+params
        for param in param_list:
            self.local_val_mgr.fill_in_param(param)
        frame_size = self.local_val_mgr.size
        
        enter_code = []
        enter_code.append(ASM_Line('label', func_decl.name))
        enter_code.append(ASM_Line('sw', 'fp', 'sp', '-4'))
        enter_code.append(ASM_Line('sw', 'ra', 'sp', '-8'))
        enter_code.append(ASM_Line('addi', 'fp', 'sp', '-4'))
        if len(param_list)>=8:
            print('Error: 暂不支持过多参数！会忽略靠后的参数')
        for i in range(8):
            if i>=len(param_list):
                break
            if i==0:  # 暂时假设一定有有返回值（尚不支持void）
                continue
            enter_code.append(self.local_val_mgr.sw(param_list[i], 'a'+str(i)))
        enter_code.append(ASM_Line('addi', 'sp', 'sp', str(-frame_size)))
        
        # 暂时假设有返回值（尚不支持void）
        exit_code = []
        exit_code.append(self.local_val_mgr.lw(param_list[0], 'a0')) # ('lw', 'a0', 'fp', str(-offset_list[0])))
        exit_code.append(ASM_Line('addi', 'sp', 'sp', str(frame_size)))
        exit_code.append(ASM_Line('lw', 'fp', 'sp', '-4'))
        exit_code.append(ASM_Line('lw', 'ra', 'sp', '-8'))
        exit_code.append(ASM_Line('ret'))
        self.code = enter_code + self.code + exit_code

        self.local_val_mgr.solve_func_var()

    def del_mv(self):
        new_code = []
        for this_code in self.code:
            if len(new_code)>0:
                last_code = new_code[-1]
                if last_code.op=='mv' and this_code.op=='mv' and (last_code.args==this_code.args or
                        (last_code.args[0], last_code.args[1])==(this_code.args[1], this_code.args[0])):
                    pass # 已经mv a,b 那么mv a,b 和mv b,a可删去
                elif last_code.op=='mv' and this_code.op=='mv' and last_code.args[0]==this_code.args[1]:
                    new_code.append(ASM_Line('mv', this_code.args[0], last_code.args[1]))
                    # 已经mv a,b 那么mv c,a 可化为mv c,b
                elif last_code.op=='mv' and (this_code.op in [
                            'lw', 'add', 'addi', 'sub', 'slt', 'sltu',
                            'slti', 'sltiu', 'seqz', 'snez'
                        ]) and last_code.args[0]==this_code.args[0]: 
                    new_code.pop()     # mv到的这个寄存器又立刻成为修改寄存器操作的目标寄存器，删去上个mv
                    new_code.append(this_code)
                else:
                    new_code.append(this_code)
            else:
                new_code.append(this_code)
        self.code = new_code

    def clear_sw(self):
        # 没有被lw过的位置自然不需要去sw    
        mem_list = {'0':'0', '-4': '-4'}               # 不能清除未决变量和保存变量
        for code in self.code:
            if code.op=='lw' and code.args[1]=='fp':
                mem_list[code.args[2]] = code.args[2]
        new_code = []
        for code in self.code:
            if code.op=='sw' and code.args[0].startswith('t') and code.args[1]=='fp' and not (code.args[2] in mem_list):
                pass
            else:
                new_code.append(code)
        self.code = new_code

    def pick_up_lw(self):
        old_code = deque()
        for code in self.code:
            old_code.append((True, code))
        new_code = deque()
        while len(old_code)>0:
            (toDo, this_code)  = old_code.popleft()
            if toDo and this_code.op=='lw' and this_code.args[1]=='fp':
                to_continue = True
                while to_continue and len(new_code)>0:
                    (_, last_code) = new_code[-1]
                    # print(last_code)
                    # print(this_code)
                    # print(this_code.args[0] in last_code.args)
                    if last_code.op in [                             # 是跳转相关语句时截止
                            'label', 'ret', 'call'                   # TODO: 这个列表可能还需要补充
                            ] or last_code.op.startswith('j') or last_code.op.startswith('b'):
                        to_continue = False
                        new_code.append((False, this_code))
                    elif len(last_code.args)>0 and last_code.args[0]=='fp': # 上一句目标数是fp时截止
                        to_continue = False
                        new_code.append((False, this_code))                        
                    elif last_code.op=='sw' and last_code.args[1]=='fp' and last_code.args[2]==this_code.args[2]:
                        if last_code.args[0]==this_code.args[0]:   # rd先sw到变量，再取出到rd，故删去lw
                            to_continue = False
                        else:                                      # rt先sw到变量，再取出到rd，故化简为mv
                            to_continue = False
                            new_code.append((False, ASM_Line('mv', this_code.args[0], last_code.args[0])))
                    elif last_code.op=='lw' and last_code.args[1]=='fp' and last_code.args[2]==this_code.args[2]:
                        if last_code.args[0]==this_code.args[0]:   # 重复lw，删除后一个
                            to_continue = False
                        else:                                      # 重复lw到不同寄存器，这一条改为mv
                            to_continue = False
                            new_code.append((False, ASM_Line('mv', this_code.args[0], last_code.args[0])))
                    elif this_code.args[0] in last_code.args:                  # lw, sw以外的操作涉及该寄存器
                        to_continue = False
                        new_code.append((False, this_code))
                    else:                                          # 能安全地把lw指令前移
                        new_code.pop()
                        old_code.appendleft((False, last_code))

            else:
                new_code.append((False, this_code))
        code_set = []
        for _, code in new_code:
            code_set.append(code)
        self.code = code_set

    '''
    @staticmethod
    def gen_decl(self, block):
        print('decl block')
        print(block)
    '''

    @staticmethod
    def gen_func_body(block, symbols):
        asm = ASM_Module('func_body', symbols)
        tac_list = block.TACs
        tac_list.reverse()
        first_tac = tac_list.pop()
        assert(first_tac.op=='label')
        # next_asm_line = ASM_Line('label', func_name)         没到生成标签的时候
        # asm.add_code(next_asm_line)
        preparing_func_call = False
        func_param_list = []
        for tac in reversed(tac_list):
            if tac.op=='param' or tac.op=='call':
                preparing_func_call = True
            if preparing_func_call:
                if tac.op=='call':
                    asm.add_code(*asm.func_call_handler(tac, func_param_list))
                    func_param_list = []
                    preparing_func_call = False
                elif tac.op=='param':
                    func_param_list.append(tac.dest)
                else:     # Illegal: param call 必须连成一个序列
                    print('TAC code Error: illegal func call sequence.')
                    break
            elif tac.op=='ret':                   #  暂时先不考虑返回地址保存相关的问题
                asm.add_code(*asm.jump_tac_handler(tac))
            elif tac.op=='goto' or tac.op=='ifz' or tac.op=='label':
                asm.add_code(*asm.jump_tac_handler(tac))
            else:
                asm.add_code(*asm.normal_tac_handler(tac))

        asm.complete_labels()
        return asm

    def  __str__(self):
        s = str(self.local_val_mgr) + '\n'
        for line in self.code:
            s += str(line) + '\n'
        return s
    
    def __repr__(self):
        return str(self)

class ASM_CTRL():
    def __init__(self):
        self.funcDefs = []
        self.hasDef = {}
        self.gvars = {}
        self.result = []

    def gen_func(self, block, symbols, func_decl):
        func_asm = ASM_Module.gen_func_body(block, symbols)
        func_asm.func_extend_with(func_decl)
        func_asm.pick_up_lw()
        func_asm.clear_sw()
        func_asm.del_mv()
        # print(func_asm)
        self.funcDefs.append(func_asm.export_as_func())
        self.hasDef[func_decl.name] = True

    def gen_gvar_init(self, block):
        if len(block.TACs)==0:
            return
        if len(block.TACs)>1:
            print('Error: complicit global variable init not supported now.')
            return
        ginit_tac = block.TACs[0]
        if ginit_tac.op!='=':
            print('Error: complicit global variable init not supported now.')
            return
        if not ginit_tac.args[0].isConst:
            print('Error: global variable can only be inited as a constant.')
            return
        self.gvars[ginit_tac.dest.name] = ginit_tac.args[0].val

    def gen_total(self, all_symbols):
        global_symbols = {}
        for symbol in all_symbols:
            if not symbol.name.startswith('{'):
                if not(isinstance(symbol, FuncSymbol)) or symbol.name in self.hasDef:
                    global_symbols[symbol.name] = symbol

        code_text = []
        for symbol_name in global_symbols:
            code_text.append(ASM_Line('.global', symbol_name))
        code_text.append(ASM_Line('.section', '.text'))

        code_data = []
        code_data.append(ASM_Line('.section', '.data'))
        code_data.append(ASM_Line('.align', '2'))
        for symbol_name in global_symbols:
            if isinstance(global_symbols[symbol_name], FuncSymbol):
                continue
            code_data.append(ASM_Line('label', symbol_name))
            value = self.gvars.get(symbol_name)
            if value is None:
                code_data.append(ASM_Line('.zero', str(global_symbols[symbol_name].size))) # 分配若干字节空间（初始化为0未必已实现）
            else:
                code_data.append(ASM_Line('.word', str(value)))

        total_code = code_text
        for codes in self.funcDefs:
            total_code += codes
        total_code += code_data
        self.result = total_code

    def gen_code_text(self):
        text = ''
        for code in self.result:
            text += str(code) + '\n'
        return text

asm_ctrl = ASM_CTRL()