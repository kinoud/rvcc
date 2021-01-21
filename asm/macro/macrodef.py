
'''
    RISC-V 使用的symbol表示那个标号的地址，在出现在某一句代码中时，又要减去那里的PC
    （因为RISC-V的跳转基本都是PC相对寻址，而jalr一般也是伪指令展开后和auipc成对的）
    %hi取这个符号的相对地址的高20位作为立即数
    %lo是取低12位；这里，我们认为%lo符号作用时，上一句一定是%hi符号作用，因此%lo计算符号的相对地址时参照的不是本句代码地址，而是上一句。
    目前我们仅在auipc, jalr组合的情况下使用%hi和%lo，如果将来要拓展到其他情形，可能需要考虑这里的问题
'''

class DefaultMacros:
    @staticmethod
    def macro_nop(params):
        assert(len(params)==0)
        return [["addi", "$0", "$0", "0"]]
    @staticmethod
    def macro_neg(params):
        assert(len(params)==2)
        return [["sub", params[0], "$0", params[1]]]
    @staticmethod
    def macro_negw(params):
        assert(len(params)==2)
        return [["subw", params[0], "$0", params[1]]]
    @staticmethod
    def macro_snez(params):
        assert(len(params)==2)
        return [["sltu", params[0], "$0", params[1]]]
    @staticmethod
    def macro_sltz(params):
        assert(len(params)==2)
        return [["slt", params[0], params[1], "$0"]]
    @staticmethod
    def macro_sgtz(params):
        assert(len(params)==2)
        return [["slt", params[0], "$0", params[1]]]
    @staticmethod
    def macro_beqz(params):
        assert(len(params)==2)
        return [["beq", params[0], "$0", params[1]]]
    @staticmethod
    def macro_bnez(params):
        assert(len(params)==2)
        return [["bne", params[0], "$0", params[1]]]
    @staticmethod
    def macro_blez(params):
        assert(len(params)==2)
        return [["bge",  "$0", params[0], params[1]]]
    @staticmethod
    def macro_bgez(params):
        assert(len(params)==2)
        return [["bge", params[0], "$0", params[1]]]
    @staticmethod
    def macro_bltz(params):
        assert(len(params)==2)
        return [["blt", params[0], "$0", params[1]]]
    @staticmethod
    def macro_bgtz(params):
        assert(len(params)==2)
        return [["blt", "$0", params[0], params[1]]]
    @staticmethod
    def macro_j(params):
        assert(len(params)==1)
        return [["jal", "$0", params[0]]]
    @staticmethod
    def macro_jr(params):
        assert(len(params)==1)
        return [["jalr", "$0", params[0], "0"]]
    @staticmethod
    def macro_ret(params):
        assert(len(params)==0)
        return [["jalr", "$0", "$1", "0"]]
    '''
        以上是依赖于x0恒等于0的部分，基本都较简单，下面有一些指令是多展开的复杂
    '''
    @staticmethod
    def macro_la(params):
        assert(len(params)==2)
        return [
            ["auipc", params[0], "%hi("+params[1]+")"],
            ["addi", params[0], params[0], "%lo("+params[1]+")"]
        ]
    @staticmethod
    def macro_lw(params):
        # 这是个参数不足是才是伪指令的指令
        if len(params)==3:
            return [["lw", params[0], params[1], params[2]]]
        assert(len(params)==2)
        return [
            ["auipc", params[0], "%hi("+params[1]+")"],
            ["lw", params[0], params[0], "%lo("+params[1]+")"]
        ]
    @staticmethod
    def macro_sw(params):
        # 这是个第三个参数不是offset才是伪指令的指令
        assert(len(params)==3)
        try:
            _ = int(params[2])
            return [["sw", params[0], params[1], params[2]]]
        except:
            return [
            ["auipc", params[2], "%hi("+params[1]+")"],
            ["sw", params[0], params[2], "%lo("+params[1]+")"]
        ]
    @staticmethod
    def macro_li(params):
        assert(len(params)==2)
        x = int(params[1])                          # 暂不考虑在这里支持equ等符号带来变化
        if abs(x)>=(1<<11):
            hi = x>>12
            lo = x^hi
            return [
                ["lui", params[0], str(hi)],
                ["addi", params[0], params[0], str(lo)]
            ]
        # else:                                     # 暂时完全忽略位数不够的情况
        return [["addi", params[0], "$0", params[1]]]

    @staticmethod
    def macro_mv(params):
        assert(len(params)==2)
        return [["addi", params[0], params[1], "0"]]
    @staticmethod
    def macro_not(params):
        assert(len(params)==2)
        return [["xori", params[0], params[1], "-1"]]
    @staticmethod
    def macro_seqz(params):
        assert(len(params)==2)
        return [["sltiu", params[0], params[1], "1"]]
    @staticmethod
    def macro_bgt(params):
        assert(len(params)==3)
        return [["blt", params[1], params[0], params[2]]]
    @staticmethod
    def macro_ble(params):
        assert(len(params)==3)
        return [["bge", params[1], params[0], params[2]]]
    @staticmethod
    def macro_bgtu(params):
        assert(len(params)==3)
        return [["bltu", params[1], params[0], params[2]]]
    @staticmethod
    def macro_bleu(params):
        assert(len(params)==3)
        return [["bgeu", params[1], params[0], params[2]]]
    @staticmethod
    def macro_jal(params):
        # 这是个参数不足是才是伪指令的指令
        if len(params)==2:
            return [["jal", params[0], params[1]]]
        assert(len(params)==1)
        return [["jal", "$0", params[0]]]
    @staticmethod
    def macro_jalr(params):
        # 这是个参数不足是才是伪指令的指令
        if len(params)==3:
            return [["jalr", params[0], params[1], params[2]]]
        assert(len(params)==1)
        return [["jalr", "$1", params[0], "0"]]
    @staticmethod
    def macro_call(params):
        assert(len(params)==1)
        return [
            ["auipc", "$1", "%hi("+params[0]+")"],
            ["jalr", "$1", "$1", "%lo("+params[0]+")"]
        ]
    
    