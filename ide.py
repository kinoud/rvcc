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
    
class TextEditDemo(QWidget):
  def __init__(self,parent=None):
    super(TextEditDemo, self).__init__(parent)
    self.setWindowTitle('SEU RISCV CC')
 
    #定义窗口的初始大小
    self.resize(800,600)
    #创建多行文本框
    self.textEdit=QTextEdit()
    self.textEdit.textChanged.connect(self.on_text_change)
    self.textShow=QTextEdit()
    self.textShow.setFontFamily('consolas')
    self.textShow.setFontPointSize(13)



    #创建两个按钮
    self.btnPress1=QPushButton('生成汇编')
    self.btnPress2=QPushButton('显示HTML')

    self.controlPanel = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(self.btnPress1)
    layout.addWidget(self.btnPress2)
    self.controlPanel.setLayout(layout)
 
    layout=QHBoxLayout()
    layout.addWidget(self.textEdit)
    layout.addWidget(self.textShow)
    layout.addWidget(self.controlPanel)
    self.setLayout(layout)
 
    self.btnPress1.clicked.connect(self.btnPress1_clicked)
    self.btnPress2.clicked.connect(self.btnPress2_clicked)
 
  def btnPress1_clicked(self):
    #以文本的形式输出到多行文本框
    output = get_output(codegen.gen_code, args=(self.textEdit.toPlainText(),))
    self.textShow.setPlainText(output)
 
  def btnPress2_clicked(self):
    #以Html的格式输出多行文本框，字体红色，字号6号
    self.textEdit.setHtml("<font color='red' size='6'><red>Hello PyQt5!\n单击按钮。</font>")
  
  def on_text_change(self):
    self.textEdit.setFontFamily('consolas')
    self.textEdit.setFontPointSize(13)

if __name__=="__main__":
  # print(get_output(codegen.gen_code, args=('int a=1;',)))
  # quit()
  app=QApplication(sys.argv)
  win=TextEditDemo()
  win.show()
  sys.exit(app.exec_())