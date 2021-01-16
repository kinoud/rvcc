#QMenuBar/QMenu/QAction的使用(菜单栏）
from PyQt5.QtWidgets import   QMenuBar,QMenu,QAction,QLineEdit,QStyle,QFormLayout,   QVBoxLayout,QWidget,QApplication ,QHBoxLayout, QPushButton,QMainWindow,QGridLayout,QLabel
from PyQt5.QtCore import QDir
from PyQt5.QtGui import QIcon,QPixmap,QFont
from PyQt5.QtCore import  QDate
from PyQt5.QtWidgets import QApplication,QWidget,QTextEdit,QVBoxLayout,QPushButton
import sys
from io import StringIO 
from multiprocessing import Process, Queue
import time
import icg.gencode_test as codegen

import signal
import traceback

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
    
class CompilerPage(QWidget):
  def __init__(self,parent=None):
    super(CompilerPage, self).__init__(parent)
    self.setWindowTitle('SEU RISCV CC')
 
    #定义窗口的初始大小
    self.resize(1200,600)
    #创建多行文本框
    self.textSrc = QTextEdit()
    self.textAsm = QTextEdit()
    self.textCoe = QTextEdit()
    self.btnGo=QPushButton('Go')
    self.btnAsm=QPushButton('Assemble')
    self.btnSaveAsm=QPushButton('Save ASM')
    self.btnSaveCoe=QPushButton('Save COE')


    self.cpSrc = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnGo)
    self.cpSrc.setLayout(layout)

    self.cpAsm = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnAsm)
    layout.addWidget(self.btnSaveAsm)
    self.cpAsm.setLayout(layout)

    self.cpCoe = QWidget()
    layout = QHBoxLayout()
    layout.addStretch(1)
    layout.addWidget(self.btnSaveCoe)
    self.cpCoe.setLayout(layout)


    self.sliceSrc = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.textSrc)
    layout.addWidget(self.cpSrc)
    self.sliceSrc.setLayout(layout)

    self.sliceAsm = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.textAsm)
    layout.addWidget(self.cpAsm)
    self.sliceAsm.setLayout(layout)

    self.sliceCoe = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.textCoe)
    layout.addWidget(self.cpCoe)
    self.sliceCoe.setLayout(layout)
 
    layout=QHBoxLayout()
    layout.addWidget(self.sliceSrc)
    layout.addWidget(self.sliceAsm)
    layout.addWidget(self.sliceCoe)
    self.setLayout(layout)
 
    self.btnGo.clicked.connect(self.btnGo_clicked)
 
  def btnGo_clicked(self):
    output = get_output(codegen.gen_code, args=(self.textSrc.toPlainText(),))
    self.textAsm.setPlainText(output)

class MyWindow(QMainWindow):

  def __init__(self,parent=None):

    super().__init__(parent)
    self.layout=QHBoxLayout()
    self.menubar=self.menuBar()#获取窗体的菜单栏

    self.file=self.menubar.addMenu("系统菜单")
    self.file.addAction("New File")

    self.save=QAction("Save",self)
    self.save.setShortcut("Ctrl+S")#设置快捷键
    self.file.addAction(self.save)

    self.edit=self.file.addMenu("Edit")
    self.edit.addAction("copy")#Edit下这是copy子项
    self.edit.addAction("paste")#Edit下设置paste子项

    self.quit=QAction("Quit",self)#注意如果改为：self.file.addMenu("Quit") 则表示该菜单下必须柚子菜单项；会有>箭头
    self.file.addAction(self.quit)
    self.file.triggered[QAction].connect(self.processtrigger)
    self.setLayout(self.layout)
    self.setWindowTitle("Menu Demo")
    self.setCentralWidget(CompilerPage())



if __name__=="__main__":
  # print(get_output(codegen.gen_code, args=('int a=1;',)))
  # quit()
  app=QApplication(sys.argv)
  font = QFont('consolas')
  pointsize = font.pointSize()
  font.setPixelSize(pointsize*1.5)
  app.setFont(font)
  win=CompilerPage()
  win.show()
  sys.exit(app.exec_())