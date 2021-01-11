from pycparser import c_ast
from pycparser import CParser
import argparse

from symbol import BasicType, PtrType, StructType, BasicSymbol, PtrSymbol, StructSymbol
from symtab import symtab_store
from symconst import LabelSymbol, GotoSymbol, FakeSymbol, genSimpleConst, genType, genConstant
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

    def enter_loop(self):
        '''
        新push,功能相同
        '''
        self.loops.append(LoopOpSet())
    
    def quit_loop(self, start_tac, end_tac):
        '''
        新pop,功能相同
        '''
        for break_tac in self.curSet().breaks:
            break_tac.dest = GotoSymbol(end_tac)
        for continue_tac in loopMgr.curSet().continues:
            continue_tac.dest = GotoSymbol(start_tac)
        
        self.loops.pop()
    
        
class FuncRetMgr():
    def __init__(self):
        self.inFunc = False
        self.retSet = []
        self.retVar = None

    def curSet(self):
        if not self.inFunc:
            print("Warning: return outside functions.")
            return None
        return self.retSet

    def curRet(self):
        if not self.inFunc:
            print("Warning: return outside functions.")
            return None
        return self.retVar
    
    def enterFunc(self, retVar):
        self.inFunc = True
        self.retSet = []
        self.retVar = retVar

    def exitFunc(self):
        self.inFunc = False
        self.retSet = []
        self.retVar = None


loopMgr = LoopManager()
funcRetMgr = FuncRetMgr()


def genTACs(ast:c_ast.Node, sts) -> Tblock:

    _dfs_function_pool={}

    # current_tvlist = None
    current_symtab = None
    
    def register(class_name):
        def _register(f):
            _dfs_function_pool[class_name] = f
        return _register

    def dfs(u:c_ast.Node):
        if u is None:                       # deliver empty node
            return (Tblock(), None, None)

        class_name = type(u).__name__
        if _dfs_function_pool.get(class_name) is None:
            raise NotImplementedError('对于'+class_name+'类型节点的dfs函数尚未实现!')
        dfs_fn = _dfs_function_pool[class_name]

        # nonlocal current_tvlist
        nonlocal current_symtab
        if class_name=='FileAST' or class_name=='FuncDef' or class_name=='For' or class_name=='Compound':
            # past_tvlist = current_tvlist
            # current_tvlist = Tvlist(current_tvlist)
            past_symtab = current_symtab
            current_symtab = sts.get_symtab_of(u)
            (block, endv, endtype) = dfs_fn(u)
            current_symtab = past_symtab
            # current_tvlist = past_tvlist
        else:
            (block, endv, endtype) = dfs_fn(u)

        return (block, endv, endtype)

    def lval_to_rval(block, res, resType):
        nonlocal current_symtab
        if resType=='pvar':
            targetType = res.type.target_type

            if isinstance(targetType, BasicType):
                newTmp = current_symtab.gen_tmp_basic_symbol(targetType)
            elif isinstance(targetType, PtrType): # 目前似乎还用不到
                newtgt = targetType.target_type
                newTmp = current_symtab.gen_tmp_ptr_symbol(newtgt)
            elif isinstance(targetType, StructType):
                newTmp = current_symtab.gen_tmp_struct_symbol(targetType)
            else: # TODO
                # 暂时这么做，应该会有bug
                newTmp = current_symtab.gen_tmp_basic_symbol(targetType)
            
            newTAC = TAC('get', newTmp, res)
            block.appendTAC(newTAC)
            res = newTmp
            resType = 'var'
        return (block, res, resType)

    @register('FileAST')
    def FileAST(u):
        '''
        为每个子节点生成block并合并成1个block, 然后做简单的代码优化(simple_opt)
        '''
        block = Tblock()
        for v in u.ext:
            (newBlock, _, _) = dfs(v)
            block = Tblock(block, newBlock)

        lt = LocalVarTable.genLocalVarTable(sts.get_symtab_of(u), block)
        block = simple_opt(block, lt)
        # TODO

        return (block, None, None)

    @register('Decl')
    def Decl(u:c_ast.Decl):
        block = Tblock()
        if u.init is not None:
            # 目前只考虑了简单变量
            (rblock, rtmp, _) = dfs(u.init)
            u_sym = sts.get_symtab_of(u).get_symbol(u.name)
            newTAC = TAC("=", u_sym, rtmp)
            block = Tblock(block, rblock)
            block.appendTAC(newTAC)

        # print(block)
        return (block, None, None)

    @register('FuncDef')
    def FuncDef(u):
        retVar = sts.get_symtab_of(u).get_symbol('__ret__')
        funcRetMgr.enterFunc(retVar)

        (funcBlock, _, _) = dfs(u.body)
        func_start = TAC('label', LabelSymbol())
        func_end = TAC('ret', LabelSymbol())
        block = Tblock()
        block.appendTAC(func_start)
        block = Tblock(block, funcBlock)
        block.appendTAC(func_end)

        for tac in funcRetMgr.retSet:
            tac.dest = GotoSymbol(func_end)
        funcRetMgr.exitFunc()

        return (block, None, None)

    @register('Return')
    def Return(u):
        (block, res, _) = dfs(u.expr)

        goto_ret = TAC('goto', None)

        if not (res is None):
            return_assign = TAC('=', funcRetMgr.curRet(), res)
            block.appendTAC(return_assign)
        
        block.appendTAC(goto_ret)
        
        funcRetMgr.retSet.append(goto_ret)
        return (block, None, None)

    @register('Compound')
    def Compound(u):
        block = Tblock()
        nodes = u.block_items
        for node in nodes:
            (newBlock, _, _) = dfs(node)
            block = Tblock(block, newBlock)
        # TODO
        lt = LocalVarTable.genLocalVarTable(sts.get_symtab_of(u), block)
        block = simple_opt(block, lt)
        # TODO
        return (block, None, None)

    @register('Constant')
    def Constant(u):
        block = Tblock()
        endv = genSimpleConst(u.value, BasicType(u.type))
        return (block, endv, 'const')

    @register('ID')
    def ID(u):
        block = Tblock()
        name = u.name
        sym = sts.get_symtab_of(u).get_symbol(name)

        if isinstance(sym, StructSymbol):
            newTmp = current_symtab.gen_tmp_ptr_symbol(sym.type)
            newTAC = TAC('&', newTmp, sym)
            block.appendTAC(newTAC)
            return (block, newTmp, 'pvar')

        return (block, sym, 'var')

    @register('StructRef')
    def StructRef(u):
        if u.type=='.':
            (nameBlock, nameVal, nameType) = dfs(u.name)
            #(fieldBlock, fieldVal, fieldType) = dfs(u.field)
            
            print((nameBlock, nameVal, nameType))
            '''
            print(nameVal)
            print(isinstance(nameVal, StructSymbol))
            print(nameVal.type)
            print(isinstance(nameVal.type, StructType))
            '''
            '''
            if not (isinstance(nameVal, StructSymbol) and isinstance(nameVal.type, StructType)):
                print('Error: illeagal element before \'.\' ')     # .前面的应该只能是结构体变量吧
                return (Tblock(), None, None)

            member_types = nameVal.type.member_types
            '''
            if not (nameType=='pvar' and isinstance(nameVal, PtrSymbol)):
                if not isinstance(nameVal.type.target_type, StructType):
                    print('Error: illeagal element before \'.\' ')     # .前面的应该只能是结构体变量吧
                    return (Tblock(), None, None)
            
            member_types = nameVal.type.target_type.member_types

            if type(u.field).__name__!='ID':        # 访问结构体成员应该是只能用名字吧
                print('Error: illeagal element after \'.\' ')
                return (Tblock(), None, None)

            field_type = member_types.get(u.field.name)
            if field_type is None:
                print('Error: this struct not has this member. ')
                return (Tblock(), None, None)

            endvType = PtrType(field_type)
            newTmp = current_symtab.gen_tmp_basic_symbol(endvType)
            newTAC = TAC('offset', newTmp, nameVal, FakeSymbol(u.field.name))
            block = Tblock(nameBlock)
            block.appendTAC(newTAC)

            print(block)
            print(newTmp)

            return (block, newTmp, 'pvar')

        elif u.type=='->':
            pass # 先不考虑
        else:
            # 应该不会有其他情况吧
            return None
        return (Tblock(), None, None)

    @register('Assignment')
    def Assignment(u:c_ast.Assignment):
        (lblock, lval, ltype) = dfs(u.lvalue)
        (rblock, rval, rtype) = lval_to_rval(*dfs(u.rvalue))

        if u.op=='=':
            newTAC = TAC(u.op, lval, rval)
        else:
            newOp = u.op[:-1]
            newTAC = TAC(newOp, lval, lval, rval)

        if ltype=='pvar':
            newTAC.op='set'
        elif ltype!='var':
            print('Error: lvalue cannot be assigned.')
            return (Tblock(), None, None)

        block = Tblock(lblock, rblock)
        block.appendTAC(newTAC)
            
        # TODO
        #block = left_val_handler(block)
        return (block, lval, ltype)

    @register('UnaryOp')
    def UnaryOp(u):
        # TODO                   // for ptr
        (block, res, resType) = dfs(u.expr)

        if u.op=='&':
            if resType == 'pvar':
                return (block, res, 'tmp')
            elif resType!='var':
                print('Not lvalue!')
                return (block, None, None)
        else:
            (block, res, resType) = lval_to_rval(block, res, resType)
            
        if u.op=='*':
            return (block, res, 'pvar')

        endv = None
        if res.isConst:
            endv = genConstant(u.op, res)
        else:
            endvType = genType(u.op, res)
            newTmp = current_symtab.gen_tmp_basic_symbol(endvType)
            newTAC = TAC(u.op, newTmp, res)
            block.appendTAC(newTAC)
            endv = newTmp
        '''  废弃
        if u.op=='&':
            # lt = LocalVarTable.genLocalVarTable(sts.get_symtab_of(u), block)
            # TODO
            block = left_val_handler(block)
        '''
        return (block, endv, 'tmp')

    @register('BinaryOp')
    def BinaryOp(u):
        (leftBlock, leftRes, _) = lval_to_rval(*dfs(u.left))
        (rightBlock, rightRes, _) = lval_to_rval(*dfs(u.right))
        block = Tblock(leftBlock, rightBlock)
        endv = None
        if leftRes.isConst and rightRes.isConst:
            endv = genConstant(u.op, leftRes, rightRes)
            # print(endv)
        else:
            endvType = genType(u.op, leftRes, rightRes)
            newTmp = current_symtab.gen_tmp_basic_symbol(endvType)
            # special
            if u.op=="&&":
                tac_1 = TAC('ifz', None, leftRes)
                tac_2 = TAC('!=', newTmp, rightRes, genSimpleConst('0', BasicType('int')))
                tac_3 = TAC('goto', None)
                tac_4 = TAC('label', LabelSymbol())
                tac_5 = TAC('=', newTmp, genSimpleConst('0', BasicType('int')))
                tac_6 = TAC('label', LabelSymbol())
                tac_1.dest = GotoSymbol(tac_4)
                tac_3.dest = GotoSymbol(tac_6)
                block.appendTAC(tac_1)
                block.appendTAC(tac_2)
                block.appendTAC(tac_3)
                block.appendTAC(tac_4)
                block.appendTAC(tac_5)
                block.appendTAC(tac_6)
            elif u.op=="||":
                tac_1 = TAC('ifz', None, leftRes)
                tac_2 = TAC('=', newTmp, genSimpleConst('1', BasicType('int')))
                tac_3 = TAC('goto', None)
                tac_4 = TAC('label', LabelSymbol())
                tac_5 = TAC('!=', newTmp, rightRes, genSimpleConst('0', BasicType('int')))
                tac_6 = TAC('label', LabelSymbol())
                tac_1.dest = GotoSymbol(tac_4)
                tac_3.dest = GotoSymbol(tac_6)
                block.appendTAC(tac_1)
                block.appendTAC(tac_2)
                block.appendTAC(tac_3)
                block.appendTAC(tac_4)
                block.appendTAC(tac_5)
                block.appendTAC(tac_6)
            else:
                newTAC = TAC(u.op, newTmp, leftRes, rightRes)
                block.appendTAC(newTAC)
            endv = newTmp

        return (block, endv, 'tmp')

    @register('If')
    def If(u):
        (block, condRes, _) = dfs(u.cond)
        if condRes.isConst:
            if condRes.val!=0:
                (block, _, _) = dfs(u.iftrue)
            elif u.iffalse is None:
                block = Tblock()
            else:
                (block, _, _) = dfs(u.iffalse)
        elif u.iffalse is None:
            goto_endif = TAC('ifz', None, condRes)
            block.appendTAC(goto_endif)
            (true_part, _, _) = dfs(u.iftrue)
            endiftac = TAC('label', LabelSymbol())
            goto_endif.dest = GotoSymbol(endiftac)
            block = Tblock(block, true_part)
            block.appendTAC(endiftac)
        else:
            goto_false = TAC('ifz', None, condRes)
            (true_part, _, _) = dfs(u.iftrue)
            goto_endif = TAC('goto', None)
            (false_part, _, _) = dfs(u.iffalse)
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

        return (block, None, None)

    @register('While')
    def While(u):

        loopMgr.push()

        block = Tblock()
        (condBlock, condRes, _) = dfs(u.cond)
        if condRes.isConst:
            if condRes.val!=0:
                (while_body, _, _) = dfs(u.stmt)
                while_start = TAC('label', LabelSymbol())
                while_end = TAC('label', LabelSymbol())
                while_back = TAC('goto', GotoSymbol(while_start))
                block.appendTAC(while_start)
                block = Tblock(block, while_body)
                block.appendTAC(while_back)
                block.appendTAC(while_end)
        else:
            (while_body, _, _) = dfs(u.stmt)
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
        
        for continue_tac in loopMgr.curSet().continues:
            continue_tac.dest = GotoSymbol(while_start)
        for break_tac in loopMgr.curSet().breaks:
            break_tac.dest = GotoSymbol(while_end)
        loopMgr.pop()

        return (block, None, None)

    @register('For')
    def For(u:c_ast.For):
        block = Tblock()
        loopMgr.enter_loop()
        
        (init_block, _, _) = dfs(u.init)
        for_start = TAC('label', LabelSymbol())
        cond_res,cond_block = dfs(u.cond)
        for_end = TAC('label', LabelSymbol())
        for_forward = TAC('ifz', GotoSymbol(for_end), cond_res)
        (body_block, _, _) = dfs(u.stmt)
        (next_block, _, _) = dfs(u.next)
        for_back = TAC('goto', GotoSymbol(for_start))
        
        
        block = Tblock(block, init_block)
        block.appendTAC(for_start)
        block = Tblock(block, cond_block)
        block.appendTAC(for_forward)
        block = Tblock(block, body_block)
        block = Tblock(block, next_block)
        block.appendTAC(for_back)
        block.appendTAC(for_end)
        
        loopMgr.quit_loop(for_start, for_end)
        
        return (block, None, None)


    @register('DeclList')
    def DeclList(u:c_ast.DeclList):
        block = Tblock()
        for d in u.decls:
            (b, _, _) = dfs(d)
            block = Tblock(block, b)
        return (block, None, None)

    @register('Break')
    def Break(u):
        tac = TAC('goto', None)
        block = Tblock()
        block.appendTAC(tac)
        loopMgr.curSet().breaks.append(tac)
        return (block, None, None)

    @register('Continue')
    def Continue(u):
        tac = TAC('goto', None)
        block = Tblock()
        block.appendTAC(tac)
        loopMgr.curSet().continues.append(tac)
        return (block, None, None)

    block, _, _ = dfs(ast)
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