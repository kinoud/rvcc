from pycparser import c_ast
from pycparser import CParser
import argparse

from symbol import Type, Symbol, BasicType, PtrType, StructType, ArrayType, FuncType, BasicSymbol, PtrSymbol, StructSymbol, ArraySymbol
from symtab import symtab_store, SymTab
from symconst import LabelSymbol, GotoSymbol, FakeSymbol, genSimpleConst, genType, genConstant
from tac import TAC, TAC_block as Tblock
from taccpx import LocalVarTable, simple_opt, func_handler

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
            res = (block, endv, endtype) = dfs_fn(u)
            
            # rename begin
            
            if class_name in ['FuncDef','For','Compound']:
                config = rename_init(current_symtab)
                rename_block_symbols(block, config)
                rename_symbol(endv, config)
            
            # rename end

            current_symtab = past_symtab
            # current_tvlist = past_tvlist
        else:
            res = dfs_fn(u)

        return res

    _rename_block_id = 0
    def rename_init(t:SymTab) -> dict:
        nonlocal _rename_block_id
        config = {}
        config['prefix'] = '{b%d}' %_rename_block_id
        _rename_block_id += 1
        config['symtab'] = t
        config['renamed'] = set()
        return config

    def rename_symbol(x:Symbol, config:dict):
        if x is None or x in config['renamed']:
            return
        t = config['symtab']
        if t.tmps.get(x.name) is not None:
            d = t.tmps
        elif t.syms.get(x.name) is not None:
            d = t.syms
        else:
            d = None
        if d is not None:
            d[x.name] = None
            x.name = config['prefix'] + x.name
            d[x.name] = x
            config['renamed'].add(x)

    def rename_block_symbols(block:Tblock, config:dict):
        for tac in block.TACs:
            rename_symbol(tac.dest, config)
            for x in tac.args:
                rename_symbol(x, config)

    def lval_to_rval(block, res, resType):
        nonlocal current_symtab
        if resType=='pvar':
            targetType = res.type.target_type

            if isinstance(targetType, BasicType):
                newTmp = current_symtab.gen_tmp_basic_symbol(targetType)
            elif isinstance(targetType, PtrType): # 目前似乎还用不到
                # newtgt = targetType.target_type
                newTmp = current_symtab.gen_tmp_ptr_symbol(targetType)
            elif isinstance(targetType, StructType):
                newTmp = current_symtab.gen_tmp_struct_symbol(targetType)
            elif isinstance(targetType, ArrayType):
                newTmp = current_symtab.gen_tmp_basic_symbol(targetType)
                newTAC = TAC('=', newTmp, res)
                block.appendTAC(newTAC)
                res = newTmp
                resType = 'var'
                return (block, res, resType)

            else: # TODO
                # 暂时这么做，应该会有bug
                newTmp = current_symtab.gen_tmp_basic_symbol(targetType)
            
            newTAC = TAC('get', newTmp, res)
            block.appendTAC(newTAC)
            res = newTmp
            resType = 'var'
        return (block, res, resType)

    def struct_copy(struct_ptr):

        member_types = struct_ptr.type.target_type.member_types

        endv = current_symtab.gen_tmp_struct_symbol(struct_ptr.type.target_type)

        block = Tblock()
        for vName, vType in member_types.items():
            field_sym = FakeSymbol(vName)
            ptrType = PtrType(vType)
            tmp_1 = current_symtab.gen_tmp_ptr_symbol(ptrType)
            tac_1 = TAC('offset', tmp_1, struct_ptr, field_sym)
            tmp_2 = current_symtab.gen_tmp_ptr_symbol(ptrType)
            tac_2 = TAC('offset', tmp_2, endv, field_sym)
            tmp_3 = current_symtab.gen_tmp_ptr_symbol(vType)
            tac_3 = TAC('get', tmp_3, tmp_1)
            tac_4 = TAC('set', tmp_2, tmp_3)
            block.appendTAC(tac_1)
            block.appendTAC(tac_2)
            block.appendTAC(tac_3)
            block.appendTAC(tac_4)

        return (endv, block)

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

        # 接下来对这个整体的FuncDef的TAC作地址化
        block = func_handler(block)

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

    @register('ExprList')
    def ExprList(u):
        block = Tblock()
        for expr in u.exprs:
            (thisBlock, endv, endType) = dfs(expr)
            block = Tblock(block, thisBlock)
        
        return (block, endv, endType)

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
            newTmp = current_symtab.gen_tmp_ptr_symbol(PtrType(sym.type))
            newTAC = TAC('&', newTmp, sym)
            block.appendTAC(newTAC)
            return (block, newTmp, 'pvar')
        elif isinstance(sym, ArraySymbol):  # 数组其实也是指针
            castedType = PtrType(sym.type.ele_type)
            newTmp = current_symtab.gen_tmp_ptr_symbol(castedType)
            newTAC = TAC('=', newTmp, sym)
            block.appendTAC(newTAC)
            return (block, newTmp, 'var')
        elif sym is None:
            print('Error: Id name not found here.')

        return (block, sym, 'var')
    
    @register('Cast')
    def Cast(u):
        to_type = dfs(u.to_type)
        (exprBlock, exprVal, _) = lval_to_rval(*dfs(u.expr))
        newTmp = current_symtab.gen_tmp_ptr_symbol(to_type)
        newTAC = TAC('=', newTmp, exprVal)
        block = Tblock(exprBlock)
        block.appendTAC(newTAC)
        return (block, newTmp, 'tmp')
    
    #BEGIN ----以下都是给cast用的，decl不会深入进来
    @register('Typename')
    def Typename(u) -> Type:
        return dfs(u.type)

    @register('PtrDecl')
    def ptr_decl(u:c_ast.PtrDecl) -> PtrType:
        target_type = dfs(u.type)
        return PtrType(target_type)
    
    @register('Struct')
    def struct(u:c_ast.Struct)->StructType:
        '''
        语法树中出现Struct有两种情况(暂时发现两种),
        一是定义一个struct,二是使用一个struct.
        使用struct时,decls=None.
        '''
        nonlocal sts
        # 使用一个struct,而不是定义它
        t = sts.get_symtab_of(u)
        if u.decls is None:
            return t.get_type(u.name) # u.name 是struct的名字(不含'struct')
        # 定义一个struct
        member_types = {}
        for d in u.decls:
            sym = dfs(d)['symbol'] # 不允许Struct内嵌套定义Struct
            if sym is not None:
                member_types[sym.name] = sym.type
        return StructType(u.name, member_types)

    @register('TypeDecl')
    def type_decl(u:c_ast.TypeDecl) -> Type:
        return dfs(u.type) # IdentifierType Struct

    @register('IdentifierType')
    def identifier_type(u:c_ast.IdentifierType) -> Type:
        # 暂时认为identifier_type都是BasicType
        type_str = ' '.join(u.names)
        return BasicType(type_str)
    # END

    @register('FuncCall')
    def FuncCall(u):
        '''
        调用约定：从后往前显式指出每个参数
        basic类型和ptr类型变量直接使用
        struct类型变量原地拷贝，然后传指针
        '''
        (funcNameBlock, funcNameVal, funcNameType) = dfs(u.name)
        argList = u.args.exprs # u.args是ExprList, 但是要用特殊办法展开
        # print((funcNameBlock, funcNameVal, funcNameType))
        paramList = []
        argBlock = Tblock()
        for arg in reversed(argList):
            (thisBlock, thisEndv, thisType) = dfs(arg)

            if thisType!='pvar':
                argBlock = Tblock(argBlock, thisBlock)
                paramList.append(thisEndv)
            else:
                assert(isinstance(thisEndv, PtrSymbol))
                if isinstance(thisEndv.type.target_type, BasicType):
                    (thisBlock, thisEndv, _) = lval_to_rval(thisBlock, thisEndv, thisType)
                    argBlock = Tblock(argBlock, thisBlock)
                    paramList.append(thisEndv)
                elif isinstance(thisEndv.type.target_type, ArrayType):
                    ''' 这里还是暂时考虑隐含类型转换
                    castedType = PtrType(thisEndv.type.target_type.ele_type)
                    newTmp = current_symtab.gen_tmp_ptr_symbol(castedType)
                    newTAC = TAC('=', newTmp, thisEndv)
                    argBlock = Tblock(argBlock, thisBlock)
                    argBlock.appendTAC(newTAC)
                    paramList.append(newTmp)
                    ''' 
                    argBlock = Tblock(argBlock, thisBlock)
                    paramList.append(thisEndv)
                elif isinstance(thisEndv.type.target_type, StructType):
                    (thisEndv, copyBlock) = struct_copy(thisEndv)
                    thisBlock = Tblock(thisBlock, copyBlock)
                    argBlock = Tblock(argBlock, thisBlock)
                    paramList.append(thisEndv)
                else: # 暂时没想到其他允许的参数形式
                    print("Error: Illegal param.")
                    return (Tblock(), None, None)

        block = Tblock(funcNameBlock, argBlock)

        for param in paramList:
            newTAC = TAC('param', param)
            block.appendTAC(newTAC)
        
        funcType = funcNameVal.type
        if isinstance(funcType, FuncType):
            retType = funcType.return_type
            if isinstance(retType, BasicType):
                newTmp = current_symtab.gen_tmp_basic_symbol(retType)
                newTAC = TAC('call', newTmp, funcNameVal)
                block.appendTAC(newTAC)
                return (block, newTmp, 'tmp')
            else:
                print('Error: Complex return value not supported now.')
                return (Tblock(), None, None)
        else: # 先不考虑函数指针等情况
            print('Error: Not supported now.')
            return (Tblock(), None, None)
        return (Tblock(), None, None)

    @register('ArrayRef')
    def ArrayRef(u):
        (nameBlock, nameVal, nameType) = dfs(u.name)
        (subsBlock, subsVal, subsType) = lval_to_rval(*dfs(u.subscript))

        if not isinstance(nameVal.type, PtrType):
            print('Error: only pointer/array can be indexed.')
            newType = None
        
        if nameType=='var':
            newType = nameVal.type
        elif nameType=='pvar':
            newType = PtrType(nameVal.type.target_type.ele_type)
        else:
            print('Error: temp/const values cannot be indexed.')
            newType = None
        '''
        if isinstance(nameVal.type, ArrayType):
            print('Maybe impossible.')          # 按理说已经在ID模块直接转化掉
            newType = PtrType(nameVal.type.ele_type)
        elif isinstance(nameVal.type, PtrType):
            newType = nameVal.type
        else: # 应该是这样吧
            print('Error: only pointer/array can be indexed.')
            newType = None
        '''

        if not isinstance(subsVal, BasicSymbol):
            print('Error: subscript must be integer.')
        
        newTmp = current_symtab.gen_tmp_ptr_symbol(newType)
        newTAC = TAC('+', newTmp, nameVal, subsVal)
        block = Tblock(nameBlock, subsBlock)
        block.appendTAC(newTAC)

        return (block, newTmp, 'pvar')

    @register('StructRef')
    def StructRef(u):
        (nameBlock, nameVal, nameType) = dfs(u.name)
        
        if u.type=='.':
            if not (nameType=='pvar' and isinstance(nameVal, PtrSymbol)):
                if not isinstance(nameVal.type.target_type, StructType):
                    print('Error: illeagal element before \'.\' ')     # .前面的应该只能是结构体变量吧
                    return (Tblock(), None, None)
        elif u.type=='->':
            if not (nameType=='var' and isinstance(nameVal, PtrSymbol)):
                if not isinstance(nameVal.type.target_type, StructType):
                    print('Error: illeagal element before \'.\' ')     # .前面的应该只能是结构体变量吧
                    return (Tblock(), None, None)
        else:
            # 应该不会有其他情况吧
            print('Error: quirk struct ref?')
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
        newTmp = current_symtab.gen_tmp_ptr_symbol(endvType)

        newTAC = TAC('offset', newTmp, nameVal, FakeSymbol(u.field.name))
        block = Tblock(nameBlock)
        block.appendTAC(newTAC)

        return (block, newTmp, 'pvar')

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
        elif u.op=='++' or u.op=='p++' or u.op=='--' or u.op=='p--':
            if resType!='var':
                print('Not lvalue!')
                return (block, None, None)
            if isinstance(res.type, BasicType):
                newTmp = current_symtab.gen_tmp_basic_symbol(res.type)
            elif isinstance(res.type, PtrType):
                newTmp = current_symtab.gen_tmp_ptr_symbol(res.type)
            else:
                print('Error: this type of symbol cannot apply ++/--.')
                return (block, None, None)
            newOp = ''+u.op[1]
            if u.op[0]=='p':
                tac_1 = TAC('=', newTmp, res)
                tac_2 = TAC(newOp, res, res, genSimpleConst('1', res.type))
                block.appendTAC(tac_1)
                block.appendTAC(tac_2)
                return (block, newTmp, 'tmp')
            else:             # C标准中即使前置++/--返回的也是右值
                tac_1 = TAC(newOp, res, res, genSimpleConst('1', res.type))
                tac_2 = TAC('=', newTmp, res)
                block.appendTAC(tac_1)
                block.appendTAC(tac_2)
                return (block, newTmp, 'tmp')
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
        (cond_block, cond_res, _) = dfs(u.cond)
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