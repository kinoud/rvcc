from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
import PyQt5.QtWidgets as QtWidgets
import sys,os, subprocess
from io import StringIO 
from PyQt5 import QtCore
from multiprocessing import Process, Queue
import icg.gencode_test as codegen
sys.path.append(os.path.join(os.getcwd(), 'asm'))
import asm as asm
import json
from PyQt5.QtCore import QTimer

from PyQt5.QtWebEngineWidgets import *

import signal

from pycparser.c_lexer import CLexer

def _lex_error_func(msg, line, column):
  return
  raise ParseError("%s:%s: %s" % (msg, line, column))

clex = CLexer(_lex_error_func, lambda:None, lambda:None, lambda _:False)
clex.build(optimize=True)

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
    self.btnClose = QPushButton('Close')

    self.cpCoe = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnAddAsmFile)
    layout.addWidget(self.btnSaveAll)
    layout.addWidget(self.btnAsm)
    layout.addWidget(self.btnClose)
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
    self.btnSaveOutput.clicked.connect(self.btnSaveOutput_clicked)
    self.btnClose.clicked.connect(self.btnClose_clicked)
  
  def btnSaveOutput_clicked(self):
    fileName,fileType = QtWidgets.QFileDialog.getSaveFileName(self, "保存文件", os.getcwd(), 
    "Text Files(*.coe);;All Files(*)")
    if fileName == '':
      return 
    with open(fileName, 'w') as f:
      f.write(self.textOutput.toPlainText())
  
  def btnClose_clicked(self):
    self.panelAsm.removeCurrent()


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
    "Text Files(*.asm);;All Files(*)")
    print(fileName)
    print(fileType)
    if fileName!='':
      self.panelAsm.addTabOfFile(fileName)
    # self.panelAsm.addTab(AssembleTab(fileName),os.path.basename(fileName))

COLOR_TYPE = '#FF9999'
COLOR_KEYWORD = '#996699'
COLOR_ID = '#0099CC'
COLOR_NUMBER = '#FF6666'
COLOR_COMMENT = '#99CC66'

color_dict = {
  'BREAK':COLOR_KEYWORD,
  'CHAR':COLOR_TYPE, 
  'CONST':COLOR_KEYWORD,
  'CONTINUE':COLOR_KEYWORD, 
  'DO':COLOR_KEYWORD, 
  'ELSE':COLOR_KEYWORD, 
  'FOR':COLOR_KEYWORD, 
  'IF':COLOR_KEYWORD, 
  'INT':COLOR_TYPE, 
  'LONG':COLOR_TYPE,
  'RETURN':COLOR_KEYWORD, 
  'SHORT':COLOR_TYPE, 
  'SIGNED':COLOR_TYPE, 
  'STRUCT':COLOR_TYPE,
  'UNSIGNED':COLOR_TYPE, 
  'VOID':COLOR_TYPE,
  'WHILE':COLOR_KEYWORD, 
  'ASM':COLOR_KEYWORD,
  'COMMENT':COLOR_COMMENT,
  'INT_CONST_DEC':COLOR_NUMBER,
  'ID':COLOR_ID
}

def colored(plain:str, ttype:str) -> str:
  if color_dict.get(ttype) is None:
    print(ttype)
    return plain
  return '<font color="%s">%s</font>'%(color_dict[ttype],plain)

def colored_html_from_plain(plain:str) -> str:
  ans = ''
  lineno = 1
  pos = 0
  clex.input(plain)
  def to_html(s):
    d = {
      '\n':'<br>',
      '\t':'&nbsp;'*8,
      ' ':'&nbsp;',
      '<':'&lt;',
      '>':'&gt;'
    }
    ans = ''
    for x in s:
      ans += d.get(x,x)
    return ans
  for token in iter(clex.token, None):
    # print(token.lineno,token.lexpos,token.type,token.value)
    # print(token)
    dans = ''
    while pos < token.lexpos:
      dans += plain[pos]
      pos += 1
    ans += colored(to_html(dans), 'COMMENT')
    ans += colored(to_html(token.value), token.type)
    pos += len(token.value)
  return ans
    
# colored_html_from_plain('int{a=123;\n}')

class CompilerPage(QWidget):
  def __init__(self,parent=None):
    super(CompilerPage, self).__init__(parent)
    self.textSrc = QTextEdit()
    self.textColored = QTextEdit()
    self.textAsm = QTextEdit()
    self.fileName = 'untitled.c'
    self.isNew = True
    self.labelFile = QLabel(self.fileName)
    self.btnCompile=QPushButton('Complie')
    self.btnOpenFile=QPushButton('Open')
    self.btnSaveFile=QPushButton('Save')
    self.btnSaveOutput=QPushButton('Save Output')
    self.btnAsm=QPushButton('Assemble')
    self.browser = QWebEngineView()
    self.browser.setUrl(QtCore.QUrl('file:///' + os.path.abspath('./monaco/monaco.html').replace('\\','/')))

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

    self.naiveEditor = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.textSrc)
    layout.addWidget(self.textColored)
    self.naiveEditor.setLayout(layout)

    self.editPanel = QTabWidget()
    self.editPanel.addTab(self.naiveEditor,'naive')
    self.editPanel.addTab(self.browser,'senior')

    self.sliceSrc = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.labelFile)
    # layout.addWidget(self.browser)
    # layout.addWidget(self.textSrc)
    # layout.addWidget(self.textColored)
    layout.addWidget(self.editPanel)
    layout.addWidget(self.cpSrc)
    self.layoutSimple = layout
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
    self.textSrc.keyPressEvent
    self.btnSaveOutput.clicked.connect(self.btnSaveOutput_clicked)
    self.editPanel.currentChanged['int'].connect(self.tabfun)
    self.isBrowser = False
    self.timer = QTimer(self) #初始化一个定时器
    self.timer.timeout.connect(self.operate) #计时结束调用operate()方法
    self.timer.start(500) #设置计时间隔并启动
    self.last = self.textSrc.toPlainText()
  
  def operate(self):
    if self.isBrowser:
      self.browser.page().runJavaScript('''getValue()''', lambda x: self.textSrc.setPlainText(x))
      
  def tabfun(self, index):
    if self.isBrowser:
      self.browser.page().runJavaScript('''getValue()''', lambda x: self.textSrc.setPlainText(x))
      self.isBrowser = False
    else:
      self.isBrowser = True
      self.browser.page().runJavaScript('setValue('+ json.dumps( self.textSrc.toPlainText() ) +')')

  
  def btnSaveOutput_clicked(self):
    fileName,fileType = QtWidgets.QFileDialog.getSaveFileName(self, "保存文件", os.getcwd(), 
    "Text Files(*.asm);;All Files(*)")
    if fileName == '':
      return 
    with open(fileName, 'w') as f:
      f.write(self.textAsm.toPlainText())

  def textSrc_change(self):
    curr = self.textSrc.toPlainText()
    if (curr == self.last):
      return
    self.labelFile.setText(os.path.basename(self.fileName)+' *')
    self.textColored.setHtml(colored_html_from_plain(curr))
    self.last = curr

  def btnCompile_clicked(self):
    # print(self.textSrc.toPlainText())
    # print(colored_html_from_plain(self.textSrc.toPlainText()))
    # print(self.textColored.toPlainText())
    exe = os.path.abspath('./preproc/net5.0/test/a.c')
    with open(exe, 'w') as f:
      f.write(self.textSrc.toPlainText())
    ins = os.path.abspath('./preproc/net5.0/CPreprocressor.exe') + ' ' + exe + ' -f -s error'
    print(ins)
    f = os.popen(ins)  
    data = f.read()  
    f.close()
    print (data)
    if(data.find(':')>0):
      self.textAsm.setPlainText(data)
      return
    exe = os.path.abspath('./preproc/net5.0/test/a.p.cpp')
    with open(exe, 'r') as f:
      pp = f.read()
    output = get_output(codegen.gen_code, args=(pp,))
    self.textAsm.setPlainText(output)

  def btnOpenFile_clicked(self):
    fileName,fileType = QtWidgets.QFileDialog.getOpenFileName(self, "选取文件", os.getcwd(), 
    "C Source Files(*.c);;All Files(*)")
    print(fileName)
    print(fileType)
    self.isNew = False
    if fileName=='':
      return
    
    with open(fileName,'r') as f:
      self.textSrc.setPlainText(f.read())
    self.fileName = fileName
    self.labelFile.setText(os.path.basename(fileName))

  def btnSaveFile_clicked(self):
    if self.isNew:
      fileName,_ = QtWidgets.QFileDialog.getSaveFileName(self, "保存文件", os.getcwd(), 
    "C Source Files(*.c);;All Files(*)")
      if fileName == '':
        return
      self.fileName = fileName
    with open(self.fileName,'w') as f:
      f.write(self.textSrc.toPlainText())
    self.isNew = False
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
  
  def removeCurrent(self):
    if self.currentIndex() == -1:
      return
    self.file_name_list.pop(self.currentIndex())
    self.tabs.pop(self.currentIndex())
    self.removeTab(self.currentIndex())
    print(self.file_name_list)

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
  
  # quit()
  app=QApplication(sys.argv)
  font = QFont('consolas')
  pointsize = font.pointSize()
  font.setPixelSize(pointsize*1.5)
  app.setFont(font)
  win=MyWindow()
  win.show()
  sys.exit(app.exec_())