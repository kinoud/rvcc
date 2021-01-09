from pycparser import c_ast
from pycparser import CParser
import argparse

from symtab import symtab_store
from symconst import genSimpleConst, genType, genConstant
from tac import TAC, TAC_block as Tblock
from taccpx import LocalVarTable, simple_opt

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
        block = Tblock()
        # print(u)
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
    def unaryOp(u):
        (res, block) = dfs(u.expr)
        print((res, block))
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
        # print(u)
        (leftRes, leftBlock) = dfs(u.left)
        (rightRes, rightBlock) = dfs(u.right)
        # print(leftRes)
        # print(rightRes)
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