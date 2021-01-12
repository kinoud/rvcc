from tac import TAC, TAC_block as Tblock
from symconst import genSimpleConst, genType, genConstant

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
    new_block = Tblock()

    for src_tac in tblock.TACs:
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

def func_handler(block):
    print('FUNC(before)')
    print(block)

    block = sym_address_handler(block)

    return block

def sym_address_handler(block):
    newBlock = Tblock()
    for tac in block.TACs:
        print(tac.op + ' ' + str(tac.dest) + ' ' + str(tac.args))
        if tac.op=='=': # 单赋值语句，分析类型转换
            #基本上都是直接过去了？
            newBlock.appendTAC(tac)
        else: #default
            newBlock.appendTAC(tac)
    return newBlock
