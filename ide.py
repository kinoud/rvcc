from PyQt5.QtCore import QDir
from PyQt5.QtGui import QIcon,QPixmap,QFont
from PyQt5.QtCore import  QDate
from PyQt5.QtWidgets import *
import PyQt5.QtWidgets as QtWidgets
import sys,os
from io import StringIO 
from multiprocessing import Process, Queue
import icg.gencode_test as codegen
sys.path.append(os.path.join(os.getcwd(), 'asm'))

import asm as asm

import signal



def sub_proc(fn, q, args):
    def myexit(signum, frame):
        print('terminated(sub)',file=sys.stderr)
        exit()
    signal.signal(signal.SIGINT, myexit)

    str_out = StringIO()
    _stdout = sys.stdout
    sys.stdout = str_out
    try:
      fn(*args)
    except Exception as ex:
      print(ex)
    sys.stdout = _stdout
    q.put(str_out.getvalue())
        
def myexit(signum, frame):
  print('teminated(main)')
  exit()
signal.signal(signal.SIGINT, myexit)

def get_output(fn,args):
    q = Queue()
    p = Process(target=sub_proc, args=(fn,q,args))
    p.daemon = True
    p.start()
    p.join()
    return q.get()
    


class AssemblePage(QWidget):
  def __init__(self,parent=None):
    super().__init__(parent)
    self.textOutput = QTextEdit()
    self.btnAddAsmFile = QPushButton('Add File')
    self.btnAsm = QPushButton('Assemble')
    self.btnSaveAll = QPushButton('Save All')
    self.btnSaveOutput = QPushButton('Save to File')

    self.cpCoe = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnAddAsmFile)
    layout.addWidget(self.btnSaveAll)
    layout.addWidget(self.btnAsm)
    self.cpCoe.setLayout(layout)


    self.cpOutput = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnSaveOutput)
    self.cpOutput.setLayout(layout)

    self.sliceOutput = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.textOutput)
    layout.addWidget(self.cpOutput)
    self.sliceOutput.setLayout(layout)

    self.panelAsm = AssemblePanel()
    self.sliceCoe = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.panelAsm)
    layout.addWidget(self.cpCoe)
    self.sliceCoe.setLayout(layout)
 
    layout=QHBoxLayout()
    layout.addWidget(self.sliceCoe)
    layout.addWidget(self.sliceOutput)
    self.setLayout(layout)
 
    self.btnAddAsmFile.clicked.connect(self.btnAddAsmFile_clicked)
    self.btnAsm.clicked.connect(self.btnAsm_clicked)
    self.btnSaveAll.clicked.connect(self.btnSaveAll_clicked)

  def btnAsm_clicked(self):
    self.btnSaveAll_clicked()
    output = get_output(asm.ide_main, args=(list(map(lambda x:x.file_path,self.panelAsm.tabs)),))
    self.textOutput.setPlainText(output)

  def btnSaveAll_clicked(self):
    # print(dir(self.panelAsm))
    print(len(self.panelAsm))
    for tab in self.panelAsm.tabs:
      tab.saveFile()


  def btnAddAsmFile_clicked(self):
    fileName,fileType = QtWidgets.QFileDialog.getOpenFileName(self, "选取文件", os.getcwd(), 
    "All Files(*);;Text Files(*.txt)")
    print(fileName)
    print(fileType)
    if fileName!='':
      self.panelAsm.addTabOfFile(fileName)
    # self.panelAsm.addTab(AssembleTab(fileName),os.path.basename(fileName))
class CompilerPage(QWidget):
  def __init__(self,parent=None):
    super(CompilerPage, self).__init__(parent)
    self.textSrc = QTextEdit()
    self.textAsm = QTextEdit()
    self.fileName = 'untitled.c'
    self.labelFile = QLabel(self.fileName)
    self.btnCompile=QPushButton('Complie')
    self.btnOpenFile=QPushButton('Open')
    self.btnSaveFile=QPushButton('Save')
    self.btnSaveOutput=QPushButton('Save Output')
    self.btnAsm=QPushButton('Assemble')

    self.cpSrc = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnCompile)
    layout.addWidget(self.btnOpenFile)
    layout.addWidget(self.btnSaveFile)
    self.cpSrc.setLayout(layout)

    self.cpAsm = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnSaveOutput)
    self.cpAsm.setLayout(layout)

    self.sliceSrc = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.labelFile)
    layout.addWidget(self.textSrc)
    layout.addWidget(self.cpSrc)
    self.sliceSrc.setLayout(layout)

    self.sliceAsm = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.textAsm)
    layout.addWidget(self.cpAsm)
    self.sliceAsm.setLayout(layout)
 
    layout=QHBoxLayout()
    layout.addWidget(self.sliceSrc)
    layout.addWidget(self.sliceAsm)
    self.setLayout(layout)
 
    self.btnCompile.clicked.connect(self.btnCompile_clicked)
    self.btnOpenFile.clicked.connect(self.btnOpenFile_clicked)
    self.btnSaveFile.clicked.connect(self.btnSaveFile_clicked)
    self.textSrc.textChanged.connect(self.textSrc_change)

  def textSrc_change(self):
    self.labelFile.setText(os.path.basename(self.fileName)+' *')

  def btnCompile_clicked(self):
    output = get_output(codegen.gen_code, args=(self.textSrc.toPlainText(),))
    self.textAsm.setPlainText(output)

  def btnOpenFile_clicked(self):
    fileName,fileType = QtWidgets.QFileDialog.getOpenFileName(self, "选取文件", os.getcwd(), 
    "C Source Files(*.c);;All Files(*)")
    print(fileName)
    print(fileType)
    if fileName=='':
      return
    
    with open(fileName,'r') as f:
      self.textSrc.setPlainText(f.read())
    self.fileName = fileName
    self.labelFile.setText(os.path.basename(fileName))

  def btnSaveFile_clicked(self):
    with open(self.fileName,'w') as f:
      f.write(self.textSrc.toPlainText())
    self.labelFile.setText(os.path.basename(self.fileName))




class AssembleTab(QWidget):
  def __init__(self, file_path ,parent=None):
    super().__init__(parent)
    self.te = QTextEdit()
    self.file_path = file_path
    with open(file_path,'r') as f:
      text = f.read()
    self.te.setPlainText(text)
    layout = QVBoxLayout()
    layout.addWidget(QLabel(file_path))
    layout.addWidget(self.te)
    self.setLayout(layout)
    self.changed = False
    self.te.textChanged.connect(self.te_changed)
    self.outter_hooks = []
  def te_changed(self):
    self.changed = True
    for hk in self.outter_hooks:
      hk()
  def getTitle(self):
    return os.path.basename(self.file_path)+ (' *'if self.changed else '')
  def saveFile(self):
    with open(self.file_path,'w') as f:
      f.write(self.te.toPlainText())
    self.changed = False
    for hk in self.outter_hooks:
      hk()


class AssemblePanel(QTabWidget):
  def __init__(self,parent=None):
    super().__init__(parent)
    self.file_name_list = []
    self.tabs = []
  
  def addTabOfFile(self,fileName):
    if fileName in self.file_name_list:
      QMessageBox.information(self,"Attention","File already opened!",QMessageBox.Yes)
      return
    new_tab = AssembleTab(fileName)
    idx = self.addTab(new_tab, os.path.basename(fileName))
    new_tab.outter_hooks.append(lambda:self.setTabText(self.indexOf(new_tab),new_tab.getTitle()))
    self.file_name_list.append(fileName)
    self.tabs.append(new_tab)

class MyWindow(QMainWindow):

  def __init__(self,parent=None):

    super().__init__(parent)
    self.setWindowTitle('SEU RISCV CC')
    self.resize(1200,600)
    tw = QTabWidget()
    tw.addTab(CompilerPage(),'Compiler')
    tw.addTab(AssemblePage(),'Assembler')
    self.setCentralWidget(tw)

if __name__=="__main__":
  # print(get_output(codegen.gen_code, args=('int a=1;',)))
  # quit()
  app=QApplication(sys.argv)
  font = QFont('consolas')
  pointsize = font.pointSize()
  font.setPixelSize(pointsize*1.5)
  app.setFont(font)
  win=MyWindow()
  win.show()
  sys.exit(app.exec_())