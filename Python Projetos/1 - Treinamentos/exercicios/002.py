#Ler o nome de uma pessoa e imprimir na tela com boas vindas por Diego Bonani

sexo = int(input("Digite 1- para masculino | 2- para feminino")) 
if(sexo == 1):
    pessoa = str(input("Digite o nome da pessoa")) #Comando de entrada para o usuário digitar
    print("Seja bem vindo" + pessoa)
elif(sexo == 2):
    pessoa = str(input("Digite o nome da pessoa")) #Comando de entrada para o usuário digitar
    print("Seja bem vinda" + pessoa)
else:
    print("Comando inválido")