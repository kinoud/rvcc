from pycparser import c_ast
from pycparser import CParser

from symbol import *
from symbol import ArrayType
import argparse

class SymTab():
    def __init__(self, node:c_ast.Node, parent=None):
        self.node = node
        self.parent = parent
        if parent is not None:
            self.parent.children.append(self)
        self.children=[]
        self.syms = {}
        self.tmps = {}
        self.types = {}

    def get_symbol(self, name:str) -> Symbol:
        local_res = self.syms.get(name)
        if local_res is not None:
            return local_res
        if self.parent is None:
            return None
        return self.parent.get_symbol(name)
    
    def add_symbol(self, sym:Symbol):
        self.syms[sym.name] = sym

    def get_type(self, name:str) -> Type:
        x = self.types.get(name)
        if x is not None:
            return x
        if self.parent is None:
            return None
        return self.parent.get_type(name)

    def add_type(self, typ:Type, alias:str = None) -> Type:
        if alias is None:
            alias = typ.name
        self.types[alias] = typ

    def __repr__(self):
        ans = type(self.node).__name__ 
        once_flag = True
        len_name = len(ans)
        def prefix():
            nonlocal once_flag
            if once_flag:
                once_flag = False
                return ' '
            else:
                return '\n ' + ' '*len_name
    
        for k,v in self.types.items():
            ans += prefix()
            ans += '(type \033[1;33m%s\033[0m)['%k+repr(v)+']'
        for i,x in enumerate(self.syms.values()):
            ans += prefix()
            ans += '['+repr(x)+']'
        for x in self.tmps.values():
            ans += prefix()
            ans += '(tmp)['+repr(x)+']'
        
        return ans

    def __iter__(self):
        return iter(self.syms.values())

    '''
    侵入式修改，增加tmp_symbol功能
    '''
    def get_tmp_symbol(self, name):
        local_res = self.tmps.get(name)
        if local_res is not None:
            return local_res
        if self.parent is None:
            return None
        return self.parent.get_tmp_symbol(name)

    def gen_tmp_basic_symbol(self, varType):
        varName = "____"+str(len(self.tmps))
        newTmp = BasicSymbol(varName, varType)
        newTmp.isTmp = True
        self.tmps[varName] = newTmp
        return newTmp

    def gen_tmp_struct_symbol(self, structType):
        varName = "____"+str(len(self.tmps))
        newTmp = StructSymbol(varName, structType)
        newTmp.isTmp = True
        self.tmps[varName] = newTmp
        return newTmp        

    def gen_tmp_ptr_symbol(self, ptrType):
        varName = "____"+str(len(self.tmps))
        newTmp = PtrSymbol(varName, ptrType)
        newTmp.isTmp = True
        self.tmps[varName] = newTmp
        return newTmp
    


class SymTabStore():
    def __init__(self, ast:c_ast.Node):
        self._symtab={} # dict[c_ast.Node]->SymTab
        
        node_parent = {}
        def dfs(u:c_ast.Node):
            nonlocal node_parent
            for (v_name, v) in u.children():
                node_parent[v] = u
                dfs(v)
        dfs(ast)
        self._node_parent = node_parent

    def get_symtab_of(self, node:c_ast.Node) -> SymTab:
        t = self._symtab.get(node)
        if t is None:
            pnode = self._node_parent.get(node)
            if pnode is None:
                return None
            return self.get_symtab_of(pnode)
        return self._symtab.get(node)
    
    def add_symtab(self, node:c_ast.Node, symtab:SymTab):
        self._symtab[node]=symtab

    def show(self, root:c_ast.Node):
        def dfs(u:SymTab):
            ans = repr(u)
            for v in u.children:
                tmp = '  ' + dfs(v)
                tmp = '\n  '.join(tmp.split('\n'))
                ans += '\n' + tmp
            return ans
        root_t = self.get_symtab_of(root)
        print(dfs(root_t))

def symtab_store(ast:c_ast.Node) -> SymTabStore:
    '''
    给定一棵语法树,生成该语法树的所有符号表,存储在一个SymTabStore对象中,
    可以从中查询需要的符号表.
    实现方法是dfs遍历.
    '''

    # 符号表仓库 最后要返回的结果
    sts = SymTabStore(ast)

    '''
    辅助函数和变量
    '''

    _dfs_function_pool={}
    
    def register(class_name):
        def _register(f):
            _dfs_function_pool[class_name] = f
        return _register

    offset = 0
    in_func = False
    in_struct = False
    current_symtab = None
    
    def get_offset_type():
        if in_func:
            return OFFSET.LOCAL
        else:
            return OFFSET.GLOBAL
    # current_symtab是一个动态变化的变量,dfs下降或返回时它的内容发生改变,
    # 它的内容总是当前遍历过程中正在处理的节点的符号表


    def dfs(u:c_ast.Node, required = False, **kwargs):
        '''
        此函数将根据u的类型为它选择相应的具体的dfs函数去处理,
        与此同时维护符号表的建立与current_symtab的值
        params:
            u: 要深入遍历的节点
        '''
        nonlocal current_symtab

        if u is None:
            return {}

        t = SymTab(u, parent=current_symtab)
        sts.add_symtab(u, t)

        class_name = type(u).__name__
        if _dfs_function_pool.get(class_name) is None:
            if not required:
                return
            raise NotImplementedError('对于'+class_name+'类型节点的dfs函数尚未实现!')
        dfs_fn = _dfs_function_pool[class_name]

        saved_symtab = current_symtab
        current_symtab = t

        res = dfs_fn(u, **kwargs)

        current_symtab = saved_symtab

        return res

    
    '''
    以下是对应到每一种类型的节点的dfs处理函数(加了register注解的这些)
    '''

    @register('FileAST')
    def file_ast(u:c_ast.FileAST):
        nonlocal sts
        t = sts.get_symtab_of(u)
        for v in u.ext:
            res = dfs(v)
            if res.get('symbol') is not None:
                t.add_symbol(res['symbol'])
            if res.get('struct_type') is not None:
                t.add_type(res['struct_type'])
    
    @register('Decl')
    def decl(u:c_ast.Decl) -> dict:
        '''
        生成一个符号,并设置该符号的offset和size.
        如果它的type是FuncDecl,那么还设置该符号的参数个数.
        然后返回该符号给Decl的上级.注意,Decl并不修改自己的符号表.
        return:
            symbol: 生成的那个符号
            struct_symbol: symbol总是表示定义的变量符号,struct_symbol表示定义的
                           结构体符号(如果有的话).注意symbol和struct_symbol可能
                           同时存在,即在定义结构体的同时也定义了此类型的变量.
            (其他可能的返回值参见FuncDecl的dfs函数)
        '''
        nonlocal offset, get_offset_type

        if u.init is not None:
            dfs(u.init)

        type_name = type(u.type).__name__
        
        if type_name in ['FuncDecl','ArrayDecl','PtrDecl']:
            # FuncDecl ArrayDecl PtrDecl
            return {'symbol':dfs(u.type).gen_symbol(u.name)}

        t:Type = dfs(u.type) # u.type: Struct TypeDecl

        # 仅定义结构体而不声明变量则name=None
        if u.name is None:
            x = None
        else:
            x = t.gen_symbol(u.name)

        struct_type = None
        if isinstance(t, StructType):
            struct_type = t

        return {'symbol':x, 'struct_type':struct_type}

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

    @register('FuncDecl')
    def func_decl(u:c_ast.FuncDecl) -> FuncType:
        param_symbols = dfs(u.args) # to ParamList
        return_type = dfs(u.type) # to TypeDecl
        return FuncType(return_type, [p.type for p in param_symbols], [p.name for p in param_symbols])
        

    @register('ParamList')
    def paramlist(u:c_ast.ParamList):
        symbols = []
        for d in u.params: # d是Decl类型
            x = dfs(d)['symbol']
            symbols.append(x)
        return symbols
    
    # unsupported
    # @register('EllipsisParam')

    @register('Compound')
    def compound(u:c_ast.Compound):
        nonlocal sts
        t = sts.get_symtab_of(u)
        if u.block_items is not None:
            for v in u.block_items:
                res = dfs(v)
                if res is not None:
                    if res.get('symbol') is not None:
                        t.add_symbol(res['symbol'])
                    if res.get('struct_symbol') is not None:
                        t.add_symbol(res['struct_symbol'])


    @register('FuncDef')
    def func_def(u:c_ast.FuncDef):
        nonlocal sts
        t = sts.get_symtab_of(u)
        '''
        FuncDef的第一个孩子是Decl.
        在Decl的dfs处理函数中,我们生成一个符号,并设置该符号的offset和size.
        而现在我们令offset=0,那么Decl的dfs处理函数中将生成一个名为此函数名
        的符号,其size是返回值类型的size,offset是0.
        于是,我们约定在函数内部,返回值的offset为0.
        '''
        x = dfs(u.decl)['symbol'] # u.decl: Decl

        for sym in x.param_symbols:
            t.add_symbol(sym)
        t.add_symbol(x.return_symbol)

        dfs(u.body)

        return {'symbol':x}


    @register('If')
    def if_else(u:c_ast.If):
        dfs(u.cond)
        dfs(u.iftrue)
        dfs(u.iffalse)

    @register('PtrDecl')
    def ptr_decl(u:c_ast.PtrDecl) -> PtrType:
        target_type = dfs(u.type)
        return PtrType(target_type)
        
    @register('ArrayDecl')
    def array_decl(u:c_ast.ArrayDecl) -> ArrayType:
        dim = int(u.dim.value) # u.dim:Constant
        ele_type = dfs(u.type)
        return ArrayType(ele_type, dim)

    @register('DeclList') # 目前看来只有For用到
    def DeclList(u):
        symbols = []
        for decl in u.decls:
            res = dfs(decl)
            symbols.append(res['symbol'])
        return {'symbols':symbols}

    @register('For')
    def For(u):
        nonlocal sts
        res = dfs(u.init)
        t = sts.get_symtab_of(u)
        for syb in res['symbols']:
            t.add_symbol(syb)
        dfs(u.cond)
        dfs(u.next)
        dfs(u.stmt)

    @register('While')
    def While(u:c_ast.While):
        dfs(u.cond)
        dfs(u.stmt)

    @register('DoWhile')
    def DoWhile(u):
        dfs(u.cond)
        dfs(u.stmt)

    @register('TernaryOp')
    def TernaryOp(u: c_ast.TernaryOp):
        dfs(u.cond)
        dfs(u.iftrue)
        dfs(u.iffalse)

    dfs(ast)
    return sts


if __name__=='__main__':
    
    argparser = argparse.ArgumentParser('Dump AST with ...')
    argparser.add_argument('filename', help='name of file to parse')
    args = argparser.parse_args()

    parser = CParser()
    with open(args.filename,'r') as f:
        ast = parser.parse(f.read(), args.filename)
    print(ast)
    sts = symtab_store(ast)
    sts.show(ast)
