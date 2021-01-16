import argparse

from macro.macro import gen_segments_from_infile
from link.link import link
from tobin.rvi import parse_input

def get_arguments():
    descr = '''
    - A simple assembler for RISC-V.
    '''

    ap = argparse.ArgumentParser(description=descr)
    ap.add_argument("INFILEs", nargs='+', help="Input files containing assembly code.")
    ap.add_argument('-o', "--outfile",
                    help="Output file name.", default = 'risv_default.coe')
    ap.add_argument('-t', "--text-start",
                    help="Address where code text segment start.", default = '0')
    ap.add_argument('-d', "--data-start",
                    help="Address where data segment start.", default = '4000')
    args = ap.parse_args()
    return args


def main():
    args = get_arguments()
    infiles = args.INFILEs
    files = []
    for infile in infiles:
        file_unit = gen_segments_from_infile(infile)
        files.append(file_unit)
    
    text_start = int(vars(args)['text_start'])
    data_start = int(vars(args)['data_start'])

    tmpFile_1 = 'riscv_link.tmp'

    text_size, data_size = link(files, data_start, text_start, tmpFile_1)

    print('Text Segment Size: '+str(text_size)+' byte(s)')
    print('Data Segment Size: '+str(data_size)+' byte(s)')

    outfile = args.outfile
    tmpFile_2 = 'riscv_asm.tmp'
    args.outfile = tmpFile_2
    parse_input(tmpFile_1, **vars(args))

    fin = None
    try:
        fin = open(tmpFile_2, 'r')
    except IOError:
        return None
    
    outstr = 'memory_initialization_radix=16;\nmemory_initialization_vector='
    for line in fin:
        x = int(line, 2)
        tot = hex(x)[2:].zfill(8)
        outstr += tot[0:4] + '\n' + tot[4:8] + '\n'

    fout = None
    try:
        fout = open(outfile, 'w')
    except:
        print('Error: fail to open output file.')
        return
    fout.write(outstr)

if __name__ == '__main__':
    main()
