import subprocess 
import os 
exe = os.path.abspath('./preproc/net5.0/test/a.c')
ins = os.path.abspath('./preproc/net5.0/CPreprocressor.exe') + ' ' + exe + ' -f -s error'
print(ins)
f = os.popen(ins)  
data = f.read()  
f.close()  
print (dir(data))