from tac import TAC, TAC_block
from symconst import genSimpleConst, genType, genConstant

class LocalVarTable(object):
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
    new_block = TAC_block()
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
    print('new_block')
    print(new_block)
    res_block = TAC_block()
    for tac in new_block.TACs:
        if not(tac.op is None):
            res_block.appendTAC(tac)
    print(res_block)
    return res_block
                
