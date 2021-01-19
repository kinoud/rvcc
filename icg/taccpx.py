from .tac import TAC, TAC_block as Tblock
from .symbol import Type, BasicType, PtrType, ArrayType
from .symconst import genSimpleConst, genType, genConstant

from collections import deque

class LocalVarTable(object):
    '''
    中间代码生成过程中, 对于某个给定的block将它所涉及的所有Symbol, 拉到一个LocalVarTable中. 
        对用到的Symbol划分了3类:
        1. tmps 中间代码生成产生的临时变量
        2. lvars 本节点symtab里含有的Symbol
        3. gvars 本节点symtab里不含有的Symbol(在本节点的祖先节点里出现)
    '''
    def __init__(self):
        self.tmps = {}
        self.gvars = {}
        self.lvars = {}

    @staticmethod
    def genLocalVarTable(symtab, block):
        newT = LocalVarTable()
        def addArg(arg):
            nonlocal newT
            if arg.name in symtab.tmps:
                newT.tmps[arg] = arg
            elif arg.name in symtab.syms:
                newT.lvars[arg]=arg
            else:
                newT.gvars[arg]=arg

        for tac in block.TACs:
            if tac.isGoto():
                if tac.op=='if':
                    addArg(tac.args[0])
            else:
                addArg(tac.dest)
                for arg in tac.args:
                    addArg(arg)
        return newT

    def __str__(self):
        str_tmp = "tmp: {"
        for x in self.tmps:
            str_tmp += x.name + ", "
        str_tmp += "}"
        str_gvars = "\ngvar: {"
        for x in self.gvars:
            str_gvars += x.name + ", "
        str_gvars += "}"
        str_lvars = "\nlvar: {"
        for x in self.lvars:
            str_lvars += x.name + ", "
        str_lvars += "}"
        return str_tmp+str_gvars+str_lvars
    def __repr__(self):
        return str(self)

def simple_opt(tblock, ltable):

    #print(tblock)
    new_block = Tblock()

    src_tac_deque = deque(tblock.TACs)
    while len(src_tac_deque)>0:
        src_tac = src_tac_deque.popleft()
        if len(new_block.TACs)==0:
            new_block.appendTAC(src_tac)
        else:
            last_tac = new_block.TACs[-1]
            if src_tac.op=='=' and last_tac.dest.name==src_tac.args[0].name and (last_tac.dest in ltable.tmps):
                last_tac.dest = src_tac.dest
            else:
                new_block.appendTAC(src_tac)
    return new_block

    '''
    src_tacs = tblock.TACs
    length = len(src_tacs)
    for i in range(0,length):
        removed = False
        cur_tac = src_tacs[i]
        if cur_tac.op=='=':
            assign_arg = cur_tac.args[0]
            if assign_arg in ltable.tmps:
                cnt = 0
                loc = -1
                tgt_tac = None
                for j in range(0, i):
                    this_tac = src_tacs[j]
                    if this_tac.dest.name!=assign_arg.name:
                        continue
                    cnt += 1
                    loc = j
                    tgt_tac = this_tac
                if cnt==1:
                    newTAC = TAC(tgt_tac.op, cur_tac.dest, *tgt_tac.args)
                    new_block.TACs[j] = newTAC
                    removed = True
        if removed:
            new_block.appendTAC(TAC(None, None))
        else:
            new_block.appendTAC(cur_tac)
    res_block = Tblock()
    for tac in new_block.TACs:
        if not(tac.op is None):
            res_block.appendTAC(tac)
    return res_block
    '''

def label_adjdec(block):   # 去除跳转到自己下一句的情况，主要针对简单函数的return
    new_block = Tblock()
    next = None
    for tac in block.TACs:
        if next is tac and (tac.op=='label' or tac.op=='ret'):
            new_block.TACs.pop()                # 只删goto，标号可能还有其它地方来
            new_block.appendTAC(tac)
        elif tac.op=='goto' or tac.op=='ifz':
            next = tac.dest.tgt
            new_block.appendTAC(tac)
        else:
            next = None
            new_block.appendTAC(tac)
    return new_block

def label_clear_opt(block):
    new_block = Tblock()
    length = len(block.TACs)
    replace_dict = {}
    for i in range(length-1):
        if block.TACs[i].op=='label' and (block.TACs[i+1].op=='label' or block.TACs[i+1].op=='ret'):
            replace_dict[block.TACs[i]] = block.TACs[i+1]
    for tac in block.TACs:
        if tac.op=='goto' or tac.op=='ifz':
            tgt = tac.dest.tgt
            if tgt in replace_dict:
                tac.dest.tgt = replace_dict[tgt]
        if tac.op=='label' and tac in replace_dict:
            pass # delete this tac
        else:
            new_block.appendTAC(tac)
    return label_adjdec(new_block)

class SymbolTable(object):
    def __init__(self, syms:list):
        self.syms = syms
        self.tmps = dict()
    def get_tmp(self, typ:Type=BasicType('int'), force_new=False):
        '''
        获取一个typ类型的临时变量, force_new为真时强制创建一个临时变量,
        否则尽可能使用已创建过的临时变量
        '''
        if not force_new and self.tmps.get(typ) is not None:
            return self.tmps.get(typ)
        t = typ.gen_symbol('{tmp}')
        self.tmps[typ] = t
        self.syms.append(t)
        return t

stab = None

def to_taccpx(block:Tblock ,syms:list) -> Tblock:
    global stab
    stab = SymbolTable(syms)
    return sym_address_handler(block)

'''
    现状：由于我们全用int类型，因此几乎没什么要转化的，但是这点以后可能变更
'''

def dump_tac_detail(tac):
    line = tac.op + ' ' + str(tac.dest)
    for arg in tac.args:
        line += ' ' + str(arg)
    return line

def sym_address_handler(block):
    newBlock = Tblock()

    
    src_tac_deque = deque(block.TACs)
    while len(src_tac_deque)>0:         #  special: 至少在这一遍不对乘除法语句作处理（考虑到指针的offset）
        tac = src_tac_deque.popleft()
        # print(dump_tac_detail(tac))
        if tac.op=='=': # 单赋值语句，分析类型转换
            newBlock.appendTAC(*assign_cast_handler(tac))
        elif tac.op=='+':
            if (len(tac.args)==1):      # +单目，我们切换成=符号
                newBlock.appendTAC(*assign_cast_handler(TAC('=', tac.dest, *tac.args)))
            else:                       # 区分add和addi
                assert(not (tac.args[0].isConst and tac.args[1].isConst))
                new_tac = TAC('+', tac.dest, *tac.args)
                if new_tac.args[0].isConst:
                    new_tac.args = (new_tac.args[1], new_tac.args[0])
                if new_tac.args[1].isConst:
                    new_tac.op = '+i'
                newBlock.appendTAC(*add_cast_handler(new_tac))
        elif tac.op=='-':
            if (len(tac.args)==1):      # -单目
                newBlock.appendTAC(tac)
            else:                       # 只有sub
                assert(not (tac.args[0].isConst and tac.args[1].isConst))
                if tac.args[0].isConst:    #   暂未考虑不等宽情形 
                    tmp = stab.get_tmp()
                    tac_1 = TAC('-', tmp, tac.args[1])
                    tac_2 = TAC('+', tac.dest, tmp, tac.args[0])   # 还要塞回去
                    newBlock.appendTAC(tac_1)
                    src_tac_deque.appendleft(tac_2)
                elif tac.args[1].isConst:
                    neg_const = genSimpleConst(str(-tac.args[1].val), tac.args[1].type)
                    add_tac = TAC('+', tac.dest, tac.args[0], neg_const)
                    src_tac_deque.appendleft(add_tac)
                else:
                    newBlock.appendTAC(*sub_cast_handler(tac))
        elif tac.op=='<':               # <u 为无符号比较，  其他比较都转化为小于比较
            assert(len(tac.args)==2)
            if tac.args[0].isConst:       # 常数在左边的场合，两边移位到等号另一边
                tmp = stab.get_tmp(tac.args[1].type)
                tac_neg = TAC('-', tmp, tac.args[1])
                newBlock.appendTAC(*assign_cast_handler(tac_neg))
                tac = TAC('<', tac.dest, tmp, genSimpleConst(str(-tac.args[0].val), tac.args[0].type))
            if tac.args[1].isConst:
                tac.op += 'i'
            if (not tac.args[0].type.name.startswith('unsigned')) and (not tac.args[1].type.name.startswith('unsigned')):
                newBlock.appendTAC(TAC(tac.op, tac.dest, *tac.args))
            else:              #  指针比较也是无符号的
                newBlock.appendTAC(TAC(tac.op+'u', tac.dest, *tac.args))
        elif tac.op=='>':
            assert(len(tac.args)==2)
            new_tac = TAC('<', tac.dest, tac.args[1], tac.args[0])
            src_tac_deque.appendleft(new_tac)
        elif tac.op=='>=':
            tac_1 = TAC('<', tac.dest, *tac.args)
            tac_2 = TAC('==', tac.dest, tac.dest, genSimpleConst('0', BasicType('int')))
            src_tac_deque.extendleft([tac_2, tac_1])
        elif tac.op=='<=':
            tac_1 = TAC('>', tac.dest, *tac.args)
            tac_2 = TAC('==', tac.dest, tac.dest, genSimpleConst('0', BasicType('int')))
            src_tac_deque.extendleft([tac_2, tac_1])
        elif tac.op=='!':
            new_tac = TAC('==', tac.dest, tac.dest, genSimpleConst('0', BasicType('int')))
            src_tac_deque.appendleft(new_tac)
        elif tac.op=='==' or tac.op=='!=':
            assert(len(tac.args)==2)
            if tac.args[0].isConst:
                new_tac = TAC(tac.op, tac.dest, tac.args[1], tac.args[0])
            else:
                new_tac = TAC(tac.op, tac.dest, *tac.args)
            if tac.args[1].isConst and tac.args[1].val==0:
                new_tac = TAC(tac.op+'0', new_tac.dest, new_tac.args[0])
                newBlock.appendTAC(new_tac)
            else:
                tmp = stab.get_tmp()
                tac_1 = TAC('-', tmp, *new_tac.args)      # 符号暂设为默认
                tac_2 = TAC(tac.op, new_tac.dest, tmp, genSimpleConst('0', BasicType('int')))
                src_tac_deque.extendleft([tac_2, tac_1])
        elif tac.op=='/' or tac.op=='%':
            if tac.dest.type.name.startswith('unsigned'):
                tac.op += 'u'
            newBlock.appendTAC(tac)
        else: #default
            newBlock.appendTAC(tac)
    return newBlock

def assign_cast_handler(tac):  # 似乎不需要有操作
    # print(dump_tac_detail(tac))
    '''
    dest = tac.dest
    src = tac.args[0]
    if isinstance(dest.type, PtrType) and isinstance(src.type, PtrType): # 指针间直接赋值
        return tac
    elif isinstance(dest.type, PtrType) and isinstance(src.type, ArrayType): # 数组降级
        return tac
    elif isinstance(dest.type, PtrType) and src.isConst:       # 指针+常数
        print(src)
        return tac
    '''
    return (tac,)

def add_cast_handler(tac):
    # tac 的操作符和参数位置都已修正
    #print(dump_tac_detail(tac))
    # destType = tac.dest.type
    (arg1, arg2) = tac.args

    # 暂时忽略大小适配的变化，只考虑指针
    if isinstance(arg2.type, PtrType) or isinstance(arg2.type, ArrayType):
        arg1, arg2 = arg2, arg1
    
    targetType = None
    if isinstance(arg1.type, PtrType):
        targetType = arg1.type.target_type    
    elif isinstance(arg1.type, ArrayType):
        targetType = arg1.type.ele_type

    if not (targetType is None):
        tgt_size = targetType.size
        if arg2.isConst:
            new_val = arg2.val * tgt_size
            new_arg2 = genSimpleConst(str(new_val), arg2.type)
            new_tac = TAC(tac.op, tac.dest, arg1, new_arg2)
            return (new_tac,)
        else:
            tmp = stab.get_tmp()
            tac_a = TAC('*', tmp, arg2, genSimpleConst(str(tgt_size), arg2.type))
            tac_b = TAC('+', tac.dest, arg2, tmp)
            return (tac_a, tac_b)

    return Tblock.gen_tac_block(tac).TACs

def sub_cast_handler(tac):
    (arg1, arg2) = tac.args

    # 暂时忽略大小适配的变化，只考虑指针
    if isinstance(arg1.type, PtrType):
        # BasicType( int )的场合看作offset，否则直接把arg2强制转化为arg1类型指针
        tgt_size = arg1.type.target_type.size
        if isinstance(arg2.type, BasicType):
            tac_a = TAC('*', arg2, arg2, genSimpleConst(str(tgt_size), arg2.type))
            tac_b = TAC('/', arg2, arg2, genSimpleConst(str(tgt_size), arg2.type))
            return (tac_a, tac, tac_b)
        else:
            dest = tac.dest
            next_tac = TAC('/', dest, dest, genSimpleConst(str(tgt_size), BasicType('int')))
            return (tac, next_tac)

    return (tac,)