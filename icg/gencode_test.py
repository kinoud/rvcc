from pycparser import c_ast
from pycparser import CParser
import argparse

from symtab import symtab_store
from symconst import LabelSymbol, GotoSymbol, genSimpleConst, genType, genConstant
from tac import TAC, TAC_block as Tblock
from taccpx import LocalVarTable, simple_opt

class LoopOpSet:
    def __init__(self):
        self.breaks = []
        self.continues = []

class LoopManager:
    def __init__(self):
        self.loops = []

    def curSet(self):
        if len(self.loops)==0:
            print("Warning: break/continue outside loops.")
            return None
        return self.loops[-1]

    def push(self):
        self.loops.append(LoopOpSet())

    def pop(self):
        self.loops.pop()

loopMgr = LoopManager()

def genTACs(ast:c_ast.Node, sts) -> Tblock:

    _dfs_function_pool={}

    # current_tvlist = None
    current_symtab = None
    
    def register(class_name):
        def _register(f):
            _dfs_function_pool[class_name] = f
        return _register

    def dfs(u:c_ast.Node):
        if u is None:
            return (None, Tblock())

        class_name = type(u).__name__
        if _dfs_function_pool.get(class_name) is None:
            raise NotImplementedError('对于'+class_name+'类型节点的dfs函数尚未实现!')
        dfs_fn = _dfs_function_pool[class_name]

        # nonlocal current_tvlist
        nonlocal current_symtab
        if class_name=='FileAST' or class_name=='For' or class_name=='Compound':
            # past_tvlist = current_tvlist
            # current_tvlist = Tvlist(current_tvlist)
            past_symtab = current_symtab
            current_symtab = sts.get_symtab_of(u)
            (endv, block) = dfs_fn(u)
            current_symtab = past_symtab
            # current_tvlist = past_tvlist
        else:
            (endv, block) = dfs_fn(u)

        return (endv, block)

    @register('FileAST')
    def FileAST(u):
        '''
        为每个子节点生成block并合并成1个block, 然后做简单的代码优化(simple_opt)
        '''
        block = Tblock()
        for v in u.ext:
            block = Tblock(block, dfs(v)[1])

        lt = LocalVarTable.genLocalVarTable(sts.get_symtab_of(u), block)
        block = simple_opt(block, lt)
        # TODO

        return (None, block)

    @register('Decl')
    def Decl(u:c_ast.Decl):
        block = Tblock()
        if u.init is not None:
            (rtmp, rblock) = dfs(u.init)
            u_sym = sts.get_symtab_of(u).get_symbol(u.name)
            newTAC = TAC("=", u_sym, rtmp)
            block = Tblock(block, rblock)
            block.appendTAC(newTAC)

        # print(block)
        return (None, block)

    @register('FuncDef')
    def FuncDef(u):
        # block = Tblock()
        # print(u)
        # TODO

        (res, block) = dfs(u.body)

        return (res, block)

    @register('Compound')
    def Compound(u):
        block = Tblock()
        nodes = u.block_items
        for node in nodes:
            (res, newBlock) = dfs(node)
            block = Tblock(block, newBlock)
        # TODO
        lt = LocalVarTable.genLocalVarTable(sts.get_symtab_of(u), block)
        block = simple_opt(block, lt)
        # TODO
        return (None, block)

    @register('Constant')
    def Constant(u):
        block = Tblock()
        endv = genSimpleConst(u.value, u.type)
        return (endv, block)

    @register('ID')
    def ID(u):
        block = Tblock()
        name = u.name
        sym = sts.get_symtab_of(u).get_symbol(name)
        return (sym, block)

    @register('UnaryOp')
    def UnaryOp(u):
        (res, block) = dfs(u.expr)
        endv = None
        if res.isConst:
            endv = genConstant(u.op, res)
        else:
            endvType = genType(u.op, res)
            newTmp = current_symtab.gen_tmp_symbol(endvType)
            newTAC = TAC(u.op, newTmp, res)
            block.appendTAC(newTAC)
            endv = newTmp
        return (endv, block)

    @register('BinaryOp')
    def BinaryOp(u):
        (leftRes, leftBlock) = dfs(u.left)
        (rightRes, rightBlock) = dfs(u.right)
        block = Tblock(leftBlock, rightBlock)
        endv = None
        if leftRes.isConst and rightRes.isConst:
            endv = genConstant(u.op, leftRes, rightRes)
            # print(endv)
        else:
            endvType = genType(u.op, leftRes, rightRes)
            # print(endvType)
            newTmp = current_symtab.gen_tmp_symbol(endvType)
            newTAC = TAC(u.op, newTmp, leftRes, rightRes)
            block.appendTAC(newTAC)
            endv = newTmp

        return (endv, block)

    @register('If')
    def If(u):
        (condRes, block) = dfs(u.cond)
        print((condRes, block))
        if condRes.isConst:
            if condRes.val!=0:
                (_, block) = dfs(u.iftrue)
            elif u.iffalse is None:
                block = Tblock()
            else:
                (_, block) = dfs(u.iffalse)
        elif u.iffalse is None:
            goto_endif = TAC('ifz', None, condRes)
            block.appendTAC(goto_endif)
            (true_res, true_part) = dfs(u.iftrue)
            endiftac = TAC('label', LabelSymbol())
            goto_endif.dest = GotoSymbol(endiftac)
            block = Tblock(block, true_part)
            block.appendTAC(endiftac)
        else:
            goto_false = TAC('ifz', None, condRes)
            (true_res, true_part) = dfs(u.iftrue)
            goto_endif = TAC('goto', None)
            (false_res, false_part) = dfs(u.iffalse)
            startfalsetac = TAC('label', LabelSymbol())
            goto_false.dest = GotoSymbol(startfalsetac)
            endiftac = TAC('label', LabelSymbol())
            goto_endif.dest = GotoSymbol(endiftac)
            block.appendTAC(goto_false)
            block = Tblock(block, true_part)
            block.appendTAC(goto_endif)
            block.appendTAC(startfalsetac)
            block = Tblock(block, false_part)
            block.appendTAC(endiftac)

        # print('IF:')
        # print(block)
        return (None, block)

    @register('While')
    def While(u):

        loopMgr.push()

        block = Tblock()
        (condRes, condBlock) = dfs(u.cond)
        if condRes.isConst:
            if condRes.val!=0:
                (_, while_body) = dfs(u.stmt)
                while_start = TAC('label', LabelSymbol())
                while_end = TAC('label', LabelSymbol())
                while_back = TAC('goto', GotoSymbol(while_start))
                block.appendTAC(while_start)
                block = Tblock(block, while_body)
                block.appendTAC(while_back)
                block.appendTAC(while_end)
        else:
            (_, while_body) = dfs(u.stmt)
            while_start = TAC('label', LabelSymbol())
            while_end = TAC('label', LabelSymbol())
            while_forward = TAC('ifz', GotoSymbol(while_end), condRes)
            while_back = TAC('goto', GotoSymbol(while_start))
            block.appendTAC(while_start)
            block = Tblock(block, condBlock)
            block.appendTAC(while_forward)
            block = Tblock(block, while_body)
            block.appendTAC(while_back)
            block.appendTAC(while_end)
        
        for break_tac in loopMgr.curSet().breaks:
            break_tac.dest = GotoSymbol(while_end)
        loopMgr.pop()

        return (None, block)

    @register('Break')
    def Break(u):
        tac = TAC('goto', None)
        block = Tblock()
        block.appendTAC(tac)
        loopMgr.curSet().breaks.append(tac)
        return (None, block)

    block = dfs(ast)[1]
    return block

if __name__=='__main__':
    
    argparser = argparse.ArgumentParser('Code gen test')
    argparser.add_argument('filename', help='name of file to parse')
    args = argparser.parse_args()

    parser = CParser()
    with open(args.filename,'r') as f:
        ast = parser.parse(f.read(), args.filename)
    sts = symtab_store(ast)
    
    sts.show(ast)
    ast.show()

    block = genTACs(ast, sts)
    print(block)