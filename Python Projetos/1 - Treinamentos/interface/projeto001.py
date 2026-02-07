from tkinter import *
import pymysql
import hashlib
import json
from urllib import request


class Administrador():
    def getConexao(self):
        try:
            con = pymysql.connect(host='localhost',
                                  user='root',password='',
                                  db='db_patricia',
                                  charset='utf8mb4'
                                  )
        except:
            print("Erro ao conectar ao banco de dados")

    def getIp():
        try:
            url = request.urlopen('http://ip-api.com/json').read()
            jsn = json.loads(url.decode('UTF-8'))
            ip = jsn['query']
            print(ip)
        except:
            print("Ip não encontrado")

    def getMd5():
        senha = str(input("Digite uma senha"))
        cripto = hashlib.md5(senha.encode())
        print(cripto.hexdigest())
    '''
    def verificaLogin(self):
        login = login.self.root()
        senha = senha.self.root()

    def criarProduto(self):

    def lerProduto(self):

    def atualizarProduto(self):

    def deletarProduto(self):
    '''
    def __init__(self):
        try:
            self.root = Tk()
            self.root.title('Administrador')
            self.root.mainloop()
        except:
            if(self.root == quit(self.root)):
                print("Programa foi finalizado")

class telaInicial():
    def __init__(self):
        try:
            self.root = Tk()
            self.root.title('Loginn')
            self.root.resizable(False,False)
            Label(self.root, text='Digite seu usuário').grid()
            Label(self.root, text='Digite sua senha').grid()
            Entry(self.root, text='Digite aqui o seu login').grid(row=1,column=1)
            Entry(self.root, text='Digite a sua senha', show='*').grid(row=1,column=1)
            Button(self.root, text='Clique aqui para acessar o Administrador', bg='black', command=Administrador).grid(row=3,column=6)
            self.root.mainloop()
        except:
            print("Deu erro")

telaInicial()
